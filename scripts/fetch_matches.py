#!/usr/bin/env python3
"""football-data.org API로 최근 종료된 유럽축구 경기를 수집합니다.

프리미어리그(PL), 라리가(PD), 분데스리가(BL1), 세리에A(SA), 리그1(FL1),
챔피언스리그(CL) 6개 대회의 최근 종료된 경기를 가져와서
data/matches/ 폴더에 경기별 JSON 파일로 저장합니다.

사용법:
    python scripts/fetch_matches.py
    python scripts/fetch_matches.py --days 3
    python scripts/fetch_matches.py --competitions PL,CL

.env 파일에 FOOTBALL_DATA_API_KEY를 설정해야 합니다 (football-data.org 무료 API 키).
"""
import argparse
import json
import os
import re
import sys
import time
from datetime import date, timedelta
from pathlib import Path

import requests
from dotenv import load_dotenv

API_BASE = "https://api.football-data.org/v4"

COMPETITIONS = {
    "PL": "프리미어리그",
    "PD": "라리가",
    "BL1": "분데스리가",
    "SA": "세리에A",
    "FL1": "리그1",
    "CL": "챔피언스리그",
}

MATCHES_DIR = Path(__file__).resolve().parent.parent / "data" / "matches"

# football-data.org 무료 티어 레이트리밋(분당 10회) 여유를 두기 위한 호출 간 대기 시간(초)
REQUEST_INTERVAL_SEC = 6


def slugify(name: str) -> str:
    name = re.sub(r"\s+FC$|^FC\s+", "", name, flags=re.IGNORECASE)
    name = name.lower()
    name = re.sub(r"[^a-z0-9]+", "_", name)
    return name.strip("_")


def fetch_finished_matches(session: requests.Session, competition_code: str, date_from: str, date_to: str) -> list:
    url = f"{API_BASE}/competitions/{competition_code}/matches"
    params = {"status": "FINISHED", "dateFrom": date_from, "dateTo": date_to}
    resp = session.get(url, params=params, timeout=15)

    if resp.status_code == 429:
        print(f"  [{competition_code}] 레이트리밋 초과. 잠시 후 다시 시도해주세요.", file=sys.stderr)
        return []
    if resp.status_code != 200:
        print(f"  [{competition_code}] API 오류 {resp.status_code}: {resp.text[:200]}", file=sys.stderr)
        return []

    return resp.json().get("matches", [])


def build_match_record(match: dict) -> dict:
    return {
        "id": match["id"],
        "competition": {
            "code": match["competition"]["code"],
            "name": COMPETITIONS.get(match["competition"]["code"], match["competition"]["name"]),
        },
        "season": match.get("season", {}).get("id"),
        "matchday": match.get("matchday"),
        "utcDate": match["utcDate"],
        "status": match["status"],
        "homeTeam": {
            "id": match["homeTeam"]["id"],
            "name": match["homeTeam"]["name"],
        },
        "awayTeam": {
            "id": match["awayTeam"]["id"],
            "name": match["awayTeam"]["name"],
        },
        "score": match["score"],
    }


def save_match(match: dict) -> Path:
    home_slug = slugify(match["homeTeam"]["name"])
    away_slug = slugify(match["awayTeam"]["name"])
    filename = f"{match['id']}_{home_slug}_{away_slug}.json"

    MATCHES_DIR.mkdir(parents=True, exist_ok=True)
    path = MATCHES_DIR / filename
    path.write_text(json.dumps(match, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=2, help="최근 며칠간 종료된 경기를 가져올지 (기본값: 2)")
    parser.add_argument(
        "--competitions",
        default=",".join(COMPETITIONS.keys()),
        help="쉼표로 구분한 대회 코드 목록 (기본값: PL,PD,BL1,SA,FL1,CL)",
    )
    args = parser.parse_args()

    load_dotenv()
    api_key = os.environ.get("FOOTBALL_DATA_API_KEY")
    if not api_key:
        sys.exit(
            "FOOTBALL_DATA_API_KEY가 설정되지 않았습니다. "
            ".env 파일에 football-data.org API 키를 추가해주세요."
        )

    competition_codes = [c.strip().upper() for c in args.competitions.split(",") if c.strip()]

    date_to = date.today()
    date_from = date_to - timedelta(days=args.days)

    session = requests.Session()
    session.headers.update({"X-Auth-Token": api_key})

    total_saved = 0
    for i, code in enumerate(competition_codes):
        label = COMPETITIONS.get(code, code)
        print(f"[{code}] {label} 경기 조회 중 ({date_from} ~ {date_to})...")

        matches = fetch_finished_matches(session, code, date_from.isoformat(), date_to.isoformat())
        if not matches:
            print(f"  [{code}] 종료된 경기가 없습니다.")
        else:
            for match in matches:
                record = build_match_record(match)
                path = save_match(record)
                print(f"  저장: {path.relative_to(MATCHES_DIR.parent.parent)}")
                total_saved += 1

        if i < len(competition_codes) - 1:
            time.sleep(REQUEST_INTERVAL_SEC)

    print(f"\n완료: 총 {total_saved}개 경기 저장 ({MATCHES_DIR})")


if __name__ == "__main__":
    main()
