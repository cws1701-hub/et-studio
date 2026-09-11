#!/usr/bin/env python3
"""자체 제작 그래픽 카드 + 나레이션 음성 + 자막을 합성해 최종 영상(mp4)을 만듭니다.

방송 영상은 전혀 쓰지 않고, build_graphics.py가 만든 카드 이미지만 사용합니다
(CLAUDE.md 저작권 원칙 준수).

입력 (모두 관례적인 경로에서 자동으로 찾음):
    output/graphics/<matchId>/*.png                        — build_graphics.py 결과물
    output/<platform>/<날짜>/<matchId>_subtitles.srt         — 나레이션 기준 SRT
    output/<platform>/<날짜>/<matchId>_narration.mp3         — generate_tts.py 결과물

출력:
    output/<platform>/<날짜>/<matchId>_video.mp4

나레이션 음성의 실제 길이에 맞춰 SRT의 원래 타임코드 비율을 그대로 유지하며
전체 길이를 재조정합니다 (TTS 결과물이 항상 대본 상의 초 단위와 정확히
일치하지는 않기 때문).

사용법:
    python scripts/assemble_video.py --match-id 575335 --platform instagram
"""
import argparse
import glob
import re
import subprocess
import sys
from pathlib import Path

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
GRAPHICS_DIR = OUTPUT_DIR / "graphics"

PLATFORM_DIRS = {"instagram": "instagram", "youtube": "youtube"}

FONT_NAME = "NanumGothic"

SRT_TIME_RE = re.compile(r"(\d{2}):(\d{2}):(\d{2}),(\d{3})")


def srt_time_to_seconds(h, m, s, ms) -> float:
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000


def parse_srt(path: Path) -> list[dict]:
    blocks = path.read_text(encoding="utf-8").strip().split("\n\n")
    cues = []
    for block in blocks:
        lines = [l for l in block.splitlines() if l.strip()]
        if len(lines) < 2:
            continue
        time_line = next((l for l in lines if "-->" in l), None)
        if not time_line:
            continue
        start_str, end_str = [t.strip() for t in time_line.split("-->")]
        start = srt_time_to_seconds(*SRT_TIME_RE.match(start_str).groups())
        end = srt_time_to_seconds(*SRT_TIME_RE.match(end_str).groups())
        text_lines = [l for l in lines if l is not time_line and not l.strip().isdigit()]
        cues.append({"start": start, "end": end, "text": " ".join(text_lines)})
    return cues


def rescale_cues(cues: list[dict], target_duration: float) -> list[dict]:
    original_duration = cues[-1]["end"] if cues else 1
    if original_duration <= 0:
        return cues
    scale = target_duration / original_duration
    return [{"start": c["start"] * scale, "end": c["end"] * scale, "text": c["text"]} for c in cues]


def pick_image(cue_index: int, total_cues: int, text: str, graphics: dict, previous: str) -> str:
    if cue_index == 0 and "hook" in graphics:
        return graphics["hook"]
    if cue_index == total_cues - 1 and "outro" in graphics:
        return graphics["outro"]
    if re.search(r"\d+\s*[-:]\s*\d+", text) and "summary" in graphics:
        return graphics["summary"]
    if ("MOM" in text or "평점" in text) and "mom" in graphics:
        return graphics["mom"]
    if "순위" in text and "standings" in graphics:
        return graphics["standings"]
    return previous or graphics.get("hook") or next(iter(graphics.values()))


def find_one(pattern: str, description: str) -> Path:
    matches = sorted(glob.glob(pattern))
    if not matches:
        sys.exit(f"{description}를 찾을 수 없습니다: {pattern}")
    return Path(matches[-1])


def ffprobe_duration(path: Path) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        capture_output=True,
        text=True,
        check=True,
    )
    return float(result.stdout.strip())


def seconds_to_ass_time(t: float) -> str:
    t = max(t, 0)
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = int(t % 60)
    cs = int(round((t - int(t)) * 100))
    return f"{h:d}:{m:02d}:{s:02d}.{cs:02d}"


ASS_HEADER = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font},46,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,3,0,2,80,80,110,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def write_rescaled_ass(cues: list[dict], path: Path):
    # 자막을 SRT 대신 ASS로 직접 만드는 이유: ffmpeg의 subtitles 필터가 plain SRT를
    # 내부적으로 ASS로 변환할 때 PlayResX/Y를 정하지 못해서, 자막 한 줄이 길어
    # 줄바꿈이 일어나는 경우 폰트가 몇 배로 커지는 버그성 동작이 있었다. PlayResX/Y를
    # 프레임 실제 해상도로 명시한 ASS 파일을 직접 쓰면 이 문제가 사라진다.
    lines = [ASS_HEADER.format(font=FONT_NAME)]
    for cue in cues:
        text = cue["text"].replace("\n", "\\N")
        lines.append(
            f"Dialogue: 0,{seconds_to_ass_time(cue['start'])},{seconds_to_ass_time(cue['end'])},"
            f"Default,,0,0,0,,{text}"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_concat_list(entries: list[tuple[str, float]], path: Path):
    lines = []
    for image_path, duration in entries:
        lines.append(f"file '{image_path}'")
        lines.append(f"duration {duration:.3f}")
    # ffmpeg concat demuxer 특성상 마지막 파일은 duration 없이 한 번 더 반복해야 한다.
    lines.append(f"file '{entries[-1][0]}'")
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--match-id", required=True)
    parser.add_argument("--platform", required=True, choices=list(PLATFORM_DIRS.keys()))
    args = parser.parse_args()

    match_id = args.match_id
    platform_dir = PLATFORM_DIRS[args.platform]

    graphics_dir = GRAPHICS_DIR / match_id
    if not graphics_dir.exists():
        sys.exit(f"그래픽이 없습니다: {graphics_dir} — 먼저 scripts/build_graphics.py를 실행해주세요.")
    graphics = {
        "hook": str(graphics_dir / "01_hook.png"),
        "summary": str(graphics_dir / "02_summary.png"),
        "mom": str(graphics_dir / "03_mom.png"),
        "standings": str(graphics_dir / "04_standings.png"),
        "outro": str(graphics_dir / "05_outro.png"),
    }
    for label, path in graphics.items():
        if not Path(path).exists():
            sys.exit(f"그래픽 파일이 없습니다: {path}")

    srt_path = find_one(
        str(OUTPUT_DIR / platform_dir / "*" / f"{match_id}_*_subtitles.srt"), "SRT 자막 파일"
    )
    audio_path = find_one(
        str(OUTPUT_DIR / platform_dir / "*" / f"{match_id}_*_narration.mp3"), "나레이션 음성 파일"
    )
    out_dir = srt_path.parent
    base_name = srt_path.name.removesuffix("_subtitles.srt")
    out_video = out_dir / f"{base_name}_video.mp4"

    print(f"[{match_id}/{args.platform}] SRT: {srt_path}")
    print(f"[{match_id}/{args.platform}] 나레이션: {audio_path}")

    cues = parse_srt(srt_path)
    if not cues:
        sys.exit(f"SRT에서 자막 구간을 읽지 못했습니다: {srt_path}")

    audio_duration = ffprobe_duration(audio_path)
    rescaled = rescale_cues(cues, audio_duration)
    print(f"  나레이션 길이 {audio_duration:.2f}s에 맞춰 자막/그래픽 타이밍 재조정")

    previous_image = None
    entries = []
    for i, cue in enumerate(rescaled):
        image = pick_image(i, len(rescaled), cues[i]["text"], graphics, previous_image)
        previous_image = image
        duration = max(cue["end"] - cue["start"], 0.1)
        entries.append((image, duration))

    concat_list_path = out_dir / f"{match_id}_concat.txt"
    write_concat_list(entries, concat_list_path)

    rescaled_ass_path = out_dir / f"{match_id}_subtitles_rescaled.ass"
    write_rescaled_ass(rescaled, rescaled_ass_path)

    vf = (
        "scale=1080:1920:force_original_aspect_ratio=decrease,"
        "pad=1080:1920:(ow-iw)/2:(oh-ih)/2,setsar=1,"
        f"subtitles={rescaled_ass_path}"
    )

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", str(concat_list_path),
        "-i", str(audio_path),
        "-vf", vf,
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "30",
        "-c:a", "aac", "-b:a", "128k",
        "-shortest",
        str(out_video),
    ]
    print("  ffmpeg 렌더링 중...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        sys.exit(f"ffmpeg 렌더링 실패:\n{result.stderr[-3000:]}")

    concat_list_path.unlink(missing_ok=True)
    print(f"완료: {out_video}")


if __name__ == "__main__":
    main()
