#!/usr/bin/env python3
"""인스타그램 릴스/쇼츠용 대본(스토리보드)을 생성합니다.

사용법:
    python scripts/generate_reels_script.py --club cerezo-osaka-jy --topic intro
"""
import argparse
from pathlib import Path

from club_data import load_club, unverified_notice

TOPICS = {
    "intro": "구단 소개",
    "training": "훈련 시스템",
    "life": "기숙사/생활",
    "alumni": "졸업생/진로",
}


def build_script(club: dict, topic: str) -> str:
    name = club["name"]["kr"]
    notice = unverified_notice(club)

    scenes = [
        ("0-3초", f"훅: '{name}를 아시나요?' 자막 + 구단 엠블럼/훈련장 클립", "임팩트 있는 오프닝 컷, 텍스트는 크고 굵게"),
        ("3-10초", "구단 위치/소속 소개 (도도부현, J리그 산하 클럽유스)", "지도 그래픽 또는 전경샷"),
        ("10-20초", f"{TOPICS.get(topic, topic)} 관련 핵심 포인트 2~3개", "훈련/시설 클립, 자막으로 핵심 포인트 나열"),
        ("20-27초", "다음 편 예고 또는 팔로우 유도", "'다음 편에서는 기숙사 생활을 소개합니다' 등"),
        ("27-30초", "채널 아웃트로 (로고/팔로우 CTA)", "고정 아웃트로 템플릿 사용"),
    ]

    scene_lines = "\n".join(
        f"### {t} — {desc}\n연출 메모: {note}\n" for t, desc, note in scenes
    )

    caption = f"""{name} 소개 🇯🇵⚽
일본 U15 축구 구단을 소개하는 시리즈, 오늘은 {name}입니다.
※ 유학/입단 관련 세부 정보는 구단 공식 확인 후 별도로 안내드릴 예정이에요.

#일본축구유학 #일본U15 #{club['club_id'].replace('-', '')} #축구유학 #클럽유스 #JFA
"""

    return f"""# {name} 릴스/쇼츠 대본 — {TOPICS.get(topic, topic)}
{notice}
형식: 세로 9:16, 30초 내외, 자막 필수

{scene_lines}
## 캡션 초안

{caption}
"""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--club", required=True)
    parser.add_argument("--topic", default="intro", choices=list(TOPICS.keys()))
    args = parser.parse_args()

    club = load_club(args.club)
    script = build_script(club, args.topic)

    base = Path(__file__).resolve().parent.parent / "content" / args.club
    reels_dir = base / "reels"
    captions_dir = base / "captions"
    reels_dir.mkdir(parents=True, exist_ok=True)
    captions_dir.mkdir(parents=True, exist_ok=True)

    script_path = reels_dir / f"{args.topic}.md"
    script_path.write_text(script, encoding="utf-8")

    caption_only = script.split("## 캡션 초안\n\n", 1)[-1]
    caption_path = captions_dir / f"{args.topic}.txt"
    caption_path.write_text(caption_only.strip() + "\n", encoding="utf-8")

    print(f"릴스 대본 생성 완료: {script_path}")
    print(f"캡션 파일 생성 완료: {caption_path}")


if __name__ == "__main__":
    main()
