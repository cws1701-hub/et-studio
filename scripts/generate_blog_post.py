#!/usr/bin/env python3
"""네이버 블로그용 구단 소개 초안(Markdown)을 생성합니다.

사용법:
    python scripts/generate_blog_post.py --club cerezo-osaka-jy --topic intro
"""
import argparse
from pathlib import Path
from datetime import date

from club_data import load_club, unverified_notice

TOPICS = {
    "intro": "구단 소개",
    "training": "훈련 시스템",
    "life": "기숙사/생활",
    "alumni": "졸업생/진로",
}


def studio_abroad_line(club):
    sa = club.get("study_abroad", {})
    accepts = sa.get("accepts_international_students", "unknown")
    if accepts == "unknown":
        return "유학생(외국인 선수) 정식 수용 여부는 아직 공식 확인되지 않았습니다. 관심 있으신 분들은 구단 공식 채널로 직접 문의하시길 권장드립니다."
    return str(sa)


def build_markdown(club: dict, topic: str) -> str:
    name = club["name"]
    loc = club.get("location", {})
    notice = unverified_notice(club)
    title = f"{name['kr']} 소개 — {TOPICS.get(topic, topic)}"

    alumni_lines = []
    for a in club.get("notable_alumni", []):
        tag = "" if a.get("verified") else " (확인 필요)"
        alumni_lines.append(f"- {a['name']}{tag}")
    alumni_block = "\n".join(alumni_lines) or "- 확인된 자료 없음"

    body = f"""# {title}
{notice}
## 한눈에 보기

- **구단명**: {name['kr']} ({name.get('jp', '')})
- **소속**: {club.get('affiliation', '확인 필요')}
- **카테고리**: {club.get('category', 'U-15')}
- **소재지**: {loc.get('prefecture', '확인 필요')} {loc.get('city', '')}

[이미지: {club['club_id']}_hero.jpg — 구단 엠블럼 또는 훈련장 전경]

## 구단 소개

{name['kr']}는(은) {club.get('affiliation', '(소속 확인 필요)')}로, 일본 U-15
클럽유스 무대에서 활동하고 있습니다. (※ 본 문단은 초안입니다. 연혁·철학 등
세부 서술은 공식 자료 확인 후 보강하세요.)

## 훈련 시설

{club.get('facilities', {}).get('training_ground', '확인 필요')}

[이미지: {club['club_id']}_training.jpg — 훈련 장면]

## 기숙사/생활 여건

기숙사 운영 여부: {club.get('facilities', {}).get('dormitory', {}).get('available', 'unknown')}
{club.get('facilities', {}).get('dormitory', {}).get('details', '') or '(세부 정보 확인 필요)'}

## 졸업생/진로

{alumni_block}

## 한국 학생 관점에서 참고할 점

{studio_abroad_line(club)}

---
*이 글은 공개된 자료를 바탕으로 작성된 초안이며, 입단·유학 관련 세부 조건은
구단 공식 채널을 통해 반드시 재확인하시기 바랍니다.*

작성일: {date.today().isoformat()}
"""
    return body


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--club", required=True)
    parser.add_argument("--topic", default="intro", choices=list(TOPICS.keys()))
    args = parser.parse_args()

    club = load_club(args.club)
    md = build_markdown(club, args.topic)

    out_dir = Path(__file__).resolve().parent.parent / "content" / args.club / "blog"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{args.topic}.md"
    out_path.write_text(md, encoding="utf-8")
    print(f"블로그 초안 생성 완료: {out_path}")


if __name__ == "__main__":
    main()
