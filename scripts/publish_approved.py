#!/usr/bin/env python3
"""사람이 `/approve`로 승인한(`status: approved`) 인스타그램/유튜브 콘텐츠를
찾아서 그래픽 생성 -> TTS -> 영상 합성 -> 실제 게시까지 자동으로 처리합니다.

최종 SNS 업로드는 사람이 `/approve`를 실행해야 시작되므로, "최종 업로드 승인은
사람"이라는 원칙(CLAUDE.md)을 지킨다. 네이버 블로그는 공식 글쓰기 API가 없어서
이 스크립트가 자동 게시하지 않는다 — 승인된 글은 사람이 직접 스마트에디터에
붙여넣어야 한다 (docs/NAVER_SEMI_AUTO.md).

각 단계는 필요한 산출물이 이미 있으면 다시 만들지 않는다(멱등). 자격 증명이
없거나 네트워크가 막혀서 실패하면 해당 항목은 `approved` 상태로 남겨두고
다음 실행 때 다시 시도한다 — 추측으로 채우거나 임의로 상태를 바꾸지 않는다.

사용법:
    python scripts/publish_approved.py
    python scripts/publish_approved.py --dry-run
"""
import argparse
import datetime
import glob
import re
import subprocess
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = REPO_ROOT / "output"
DATA_MATCHES_DIR = REPO_ROOT / "data" / "matches"
SCRIPTS_DIR = Path(__file__).resolve().parent

FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n", re.S)


def read_frontmatter(path: Path) -> dict | None:
    m = FRONTMATTER_RE.match(path.read_text(encoding="utf-8"))
    if not m:
        return None
    return yaml.safe_load(m.group(1)) or {}


def update_frontmatter_status(path: Path, new_status: str, extra: dict | None = None):
    content = path.read_text(encoding="utf-8")
    m = FRONTMATTER_RE.match(content)
    if not m:
        return
    fm = yaml.safe_load(m.group(1)) or {}
    fm["status"] = new_status
    if extra:
        fm.update(extra)
    new_block = "---\n" + yaml.safe_dump(fm, allow_unicode=True, sort_keys=False).strip() + "\n---\n"
    path.write_text(new_block + content[m.end():], encoding="utf-8")


def find_match_json(match_id: str) -> Path | None:
    matches = glob.glob(str(DATA_MATCHES_DIR / f"{match_id}_*.json"))
    return Path(matches[0]) if matches else None


def run_script(args: list[str], dry_run: bool) -> bool:
    print(f"    $ {' '.join(args)}")
    if dry_run:
        return True
    result = subprocess.run(args, cwd=REPO_ROOT, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"    실패:\n{result.stderr[-2000:]}", file=sys.stderr)
        return False
    if result.stdout.strip():
        print("    " + result.stdout.strip().replace("\n", "\n    "))
    return True


def extract_instagram_caption(script_path: Path) -> str:
    content = script_path.read_text(encoding="utf-8")
    caption_match = re.search(r"## 게시용 캡션\n\n(.*?)\n\n## 해시태그\n\n(.*?)(?:\n\n|\Z)", content, re.S)
    if not caption_match:
        return ""
    caption, hashtags = caption_match.groups()
    return f"{caption.strip()}\n\n{hashtags.strip()}"


def find_video(platform_dir: str, match_id: str) -> Path | None:
    matches = glob.glob(str(OUTPUT_DIR / platform_dir / "*" / f"{match_id}_*_video.mp4"))
    return Path(matches[0]) if matches else None


def ensure_graphics(match_id: str, dry_run: bool) -> bool:
    if (OUTPUT_DIR / "graphics" / match_id).exists():
        return True
    match_json = find_match_json(match_id)
    if not match_json:
        print(f"    data/matches/에서 {match_id} 경기 JSON을 찾을 수 없어 그래픽을 만들 수 없습니다.")
        return False
    return run_script(
        ["python3", str(SCRIPTS_DIR / "build_graphics.py"), "--match-file", match_json.name], dry_run
    )


def ensure_narration(match_id: str, platform: str, dry_run: bool) -> bool:
    platform_dir = "instagram" if platform == "instagram" else "youtube"
    if glob.glob(str(OUTPUT_DIR / platform_dir / "*" / f"{match_id}_*_narration.mp3")):
        return True
    return run_script(
        ["python3", str(SCRIPTS_DIR / "generate_tts.py"), "--match-id", match_id, "--platform", platform],
        dry_run,
    )


def ensure_video(match_id: str, platform: str, dry_run: bool) -> Path | None:
    existing = find_video("instagram" if platform == "instagram" else "youtube", match_id)
    if existing:
        return existing
    ok = run_script(
        ["python3", str(SCRIPTS_DIR / "assemble_video.py"), "--match-id", match_id, "--platform", platform],
        dry_run,
    )
    if not ok:
        return None
    return find_video("instagram" if platform == "instagram" else "youtube", match_id)


def publish_instagram(match_id: str, script_path: Path, video_path: Path, dry_run: bool) -> bool:
    result = subprocess.run(
        ["python3", str(SCRIPTS_DIR / "publish_video.py"), "--file", str(video_path)],
        cwd=REPO_ROOT, capture_output=True, text=True,
    )
    if dry_run:
        print(f"    $ publish_video.py --file {video_path}")
        return True
    if result.returncode != 0:
        print(f"    영상 공개 호스팅 실패:\n{result.stderr[-2000:]}", file=sys.stderr)
        return False
    public_url = result.stdout.strip().splitlines()[-1]

    caption = extract_instagram_caption(script_path)
    caption_file = video_path.parent / f"{match_id}_caption.txt"
    caption_file.write_text(caption, encoding="utf-8")

    return run_script(
        [
            "python3", str(SCRIPTS_DIR / "post_instagram.py"),
            "--video-url", public_url,
            "--caption", str(caption_file),
        ],
        dry_run,
    )


def publish_youtube(script_path: Path, video_path: Path, frontmatter: dict, dry_run: bool) -> bool:
    title = frontmatter.get("title") or f"경기 리뷰 {frontmatter.get('matchId')}"
    description = frontmatter.get("description") or ""
    tags = frontmatter.get("tags") or []
    tags_str = ",".join(tags) if isinstance(tags, list) else str(tags)

    return run_script(
        [
            "python3", str(SCRIPTS_DIR / "upload_youtube.py"),
            "--file", str(video_path),
            "--title", title,
            "--description", description,
            "--tags", tags_str,
        ],
        dry_run,
    )


def process_entry(script_path: Path, platform: str, dry_run: bool):
    frontmatter = read_frontmatter(script_path)
    if not frontmatter or frontmatter.get("status") != "approved":
        return
    match_id = str(frontmatter.get("matchId"))
    print(f"[{match_id}/{platform}] 승인됨 — 게시 파이프라인 진행")

    if not ensure_graphics(match_id, dry_run):
        return
    if not ensure_narration(match_id, platform, dry_run):
        print(f"    나레이션 음성이 없어 건너뜁니다 (ELEVENLABS_API_KEY 확인). approved 상태 유지.")
        return
    video_path = ensure_video(match_id, platform, dry_run)
    if not video_path:
        print("    영상 합성 실패. approved 상태 유지.")
        return

    if platform == "instagram":
        ok = publish_instagram(match_id, script_path, video_path, dry_run)
    else:
        ok = publish_youtube(script_path, video_path, frontmatter, dry_run)

    if ok and not dry_run:
        update_frontmatter_status(
            script_path, "posted", {"postedAt": datetime.datetime.utcnow().isoformat() + "Z"}
        )
        print(f"    게시 완료 → status: posted")
    elif not ok:
        print(f"    게시 실패. approved 상태 유지 (다음 체크 때 재시도).")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="실제로 실행하지 않고 수행할 명령만 출력")
    args = parser.parse_args()

    for path in sorted(glob.glob(str(OUTPUT_DIR / "instagram" / "*" / "*_script.md"))):
        process_entry(Path(path), "instagram", args.dry_run)

    for path in sorted(glob.glob(str(OUTPUT_DIR / "youtube" / "*" / "*_script.md"))):
        process_entry(Path(path), "youtube", args.dry_run)

    naver_pending = [
        p for p in glob.glob(str(OUTPUT_DIR / "naverblog" / "*" / "*_post.md"))
        if (read_frontmatter(Path(p)) or {}).get("status") == "approved"
    ]
    if naver_pending:
        print("\n네이버 블로그는 공식 API가 없어 자동 게시되지 않습니다. "
              "아래 글을 스마트에디터에 직접 붙여넣어 발행해주세요:")
        for p in naver_pending:
            print(f"  - {p}")


if __name__ == "__main__":
    main()
