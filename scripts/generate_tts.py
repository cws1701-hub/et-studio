#!/usr/bin/env python3
"""ElevenLabs API로 나레이션 SRT의 텍스트를 음성(mp3)으로 합성합니다.

입력: output/<platform>/<날짜>/<matchId>_*_subtitles.srt (write-instagram/write-youtube
     커맨드가 만든 나레이션 기준 SRT)
출력: 같은 폴더에 <matchId>_*_narration.mp3

.env 파일에 ELEVENLABS_API_KEY, ELEVENLABS_VOICE_ID를 설정해야 합니다.

사용법:
    python scripts/generate_tts.py --match-id 575335 --platform instagram
"""
import argparse
import glob
import os
import re
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"

PLATFORM_DIRS = {"instagram": "instagram", "youtube": "youtube"}

API_BASE = "https://api.elevenlabs.io/v1"

SRT_BLOCK_RE = re.compile(r"\d+\n\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3}\n(.+?)(?:\n\n|\Z)", re.S)


def extract_narration_text(srt_path: Path) -> str:
    content = srt_path.read_text(encoding="utf-8")
    texts = [m.group(1).strip().replace("\n", " ") for m in SRT_BLOCK_RE.finditer(content)]
    if not texts:
        sys.exit(f"SRT에서 나레이션 텍스트를 읽지 못했습니다: {srt_path}")
    return " ".join(texts)


def find_srt(platform_dir: str, match_id: str) -> Path:
    pattern = str(OUTPUT_DIR / platform_dir / "*" / f"{match_id}_*_subtitles.srt")
    matches = sorted(glob.glob(pattern))
    if not matches:
        sys.exit(f"SRT 자막 파일을 찾을 수 없습니다: {pattern}")
    return Path(matches[-1])


def synthesize(api_key: str, voice_id: str, text: str) -> bytes:
    resp = requests.post(
        f"{API_BASE}/text-to-speech/{voice_id}",
        headers={"xi-api-key": api_key, "Content-Type": "application/json"},
        json={
            "text": text,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
        },
        timeout=60,
    )
    if resp.status_code != 200:
        sys.exit(f"ElevenLabs API 오류 {resp.status_code}: {resp.text[:300]}")
    return resp.content


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--match-id", required=True)
    parser.add_argument("--platform", required=True, choices=list(PLATFORM_DIRS.keys()))
    args = parser.parse_args()

    load_dotenv()
    api_key = os.environ.get("ELEVENLABS_API_KEY")
    voice_id = os.environ.get("ELEVENLABS_VOICE_ID")
    if not api_key or not voice_id:
        sys.exit(
            "ELEVENLABS_API_KEY / ELEVENLABS_VOICE_ID가 .env에 설정되어 있지 않습니다. "
            ".env.example을 참고해주세요."
        )

    platform_dir = PLATFORM_DIRS[args.platform]
    srt_path = find_srt(platform_dir, args.match_id)
    narration_path = srt_path.parent / srt_path.name.replace("_subtitles.srt", "_narration.mp3")

    text = extract_narration_text(srt_path)
    print(f"[{args.match_id}/{args.platform}] 나레이션 합성 중 ({len(text)}자)...")

    audio_bytes = synthesize(api_key, voice_id, text)
    narration_path.write_bytes(audio_bytes)
    print(f"완료: {narration_path}")


if __name__ == "__main__":
    main()
