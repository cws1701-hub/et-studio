#!/usr/bin/env python3
"""API-SPORTS(api-football, https://v3.football.api-sports.io/)에서
득점자·시간·카드 이벤트를 가져와 data/matches/ 안의 기존 경기 JSON 파일에 병합합니다.

football-data.org(fetch_matches.py)와 API-SPORTS는 서로 다른 경기 ID 체계를 쓰기
때문에, 각 JSON 파일의 홈팀/원정팀 이름과 날짜로 API-SPORTS의 해당 fixture를
찾아 매칭합니다.

주의: RapidAPI 경유가 아니라 API-SPORTS 직접 구독이므로 x-rapidapi-key가 아니라
x-apisports-key 헤더를 사용합니다.

사용법:
    python scripts/fetch_match_events.py
    python scripts/fetch_match_events.py --force
    python scripts/fetch_match_events.py --match-file 497582_manchester_city_arsenal.json

.env 파일에 APIFOOTBALL_KEY를 설정해야 합니다 (API-SPORTS 직접 구독 키).
"""
import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import requests
from dotenv import load_dotenv

API_BASE = "https://v3.football.api-sports.io"

MATCHES_DIR = Path(__file__).resolve().parent.parent / "data" / "matches"

# API-SPORTS 무료 티어 레이트리밋(분당 10회) 여유를 두기 위한 호출 간 대기 시간(초)
REQUEST_INTERVAL_SEC = 6

GOAL_TYPES = {"Goal"}
CARD_TYPES = {"Card"}


def normalize_team_name(name: str) -> str:
    name = re.sub(r"\b(FC|CF|AFC|SC|CD|AC)\b", "", name, flags=re.IGNORECASE)
    name = name.lower()
    name = re.sub(r"[^a-z0-9]+", "", name)
    return name


def teams_match(a: str, b: str) -> bool:
    na, nb = normalize_team_name(a), normalize_team_name(b)
    if not na or not nb:
        return False
    return na == nb or na in nb or nb in na


def find_fixture(session: requests.Session, home_team: str, away_team: str, utc_date: str) -> dict | None:
    match_dt = datetime.fromisoformat(utc_date.replace("Z", "+00:00"))
    for offset in (0, -1, 1):
        date_str = (match_dt.date() + timedelta(days=offset)).isoformat()
        resp = session.get(f"{API_BASE}/fixtures", params={"date": date_str}, timeout=15)
        if resp.status_code != 200:
            print(f"    fixtures 조회 오류 {resp.status_code} ({date_str}): {resp.text[:200]}", file=sys.stderr)
            continue

        for item in resp.json().get("response", []):
            fixture_home = item["teams"]["home"]["name"]
            fixture_away = item["teams"]["away"]["name"]
            if teams_match(home_team, fixture_home) and teams_match(away_team, fixture_away):
                return item["fixture"]

        time.sleep(REQUEST_INTERVAL_SEC)

    return None


def fetch_events(session: requests.Session, fixture_id: int) -> list:
    resp = session.get(f"{API_BASE}/fixtures/events", params={"fixture": fixture_id}, timeout=15)
    if resp.status_code != 200:
        print(f"    events 조회 오류 {resp.status_code}: {resp.text[:200]}", file=sys.stderr)
        return []
    return resp.json().get("response", [])


def build_goal_events(raw_events: list) -> list:
    return [
        {
            "minute": e["time"]["elapsed"],
            "extraMinute": e["time"]["extra"],
            "team": e["team"]["name"],
            "scorer": e["player"]["name"],
            "assist": e.get("assist", {}).get("name"),
            "detail": e["detail"],
        }
        for e in raw_events
        if e["type"] in GOAL_TYPES
    ]


def build_card_events(raw_events: list) -> list:
    return [
        {
            "minute": e["time"]["elapsed"],
            "extraMinute": e["time"]["extra"],
            "team": e["team"]["name"],
            "player": e["player"]["name"],
            "cardType": e["detail"],
        }
        for e in raw_events
        if e["type"] in CARD_TYPES
    ]


def process_match_file(session: requests.Session, path: Path, force: bool) -> bool:
    match = json.loads(path.read_text(encoding="utf-8"))

    if not force and "apiFootballFixtureId" in match:
        print(f"  [{path.name}] 이미 이벤트가 병합되어 있어 건너뜁니다 (--force로 재수집 가능).")
        return False

    home_team = match["homeTeam"]["name"]
    away_team = match["awayTeam"]["name"]
    print(f"  [{path.name}] {home_team} vs {away_team} fixture 검색 중...")

    fixture = find_fixture(session, home_team, away_team, match["utcDate"])
    if fixture is None:
        print(f"    매칭되는 API-SPORTS fixture를 찾지 못했습니다. 건너뜁니다.", file=sys.stderr)
        return False

    time.sleep(REQUEST_INTERVAL_SEC)
    raw_events = fetch_events(session, fixture["id"])

    match["apiFootballFixtureId"] = fixture["id"]
    match["goalEvents"] = build_goal_events(raw_events)
    match["cardEvents"] = build_card_events(raw_events)

    path.write_text(json.dumps(match, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"    저장 완료: 득점 {len(match['goalEvents'])}건, 카드 {len(match['cardEvents'])}건")
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--match-file", help="data/matches/ 안의 특정 파일 하나만 처리 (파일명만 입력)")
    parser.add_argument("--force", action="store_true", help="이미 이벤트가 병합된 파일도 다시 수집")
    args = parser.parse_args()

    load_dotenv()
    api_key = os.environ.get("APIFOOTBALL_KEY")
    if not api_key:
        sys.exit(
            "APIFOOTBALL_KEY가 설정되지 않았습니다. "
            ".env 파일에 API-SPORTS(api-football) 직접 구독 키를 추가해주세요."
        )

    if not MATCHES_DIR.exists():
        sys.exit(f"{MATCHES_DIR} 폴더가 없습니다. 먼저 scripts/fetch_matches.py를 실행해주세요.")

    if args.match_file:
        files = [MATCHES_DIR / args.match_file]
        if not files[0].exists():
            sys.exit(f"파일을 찾을 수 없습니다: {files[0]}")
    else:
        files = sorted(MATCHES_DIR.glob("*.json"))

    if not files:
        sys.exit(f"{MATCHES_DIR}에 처리할 경기 JSON 파일이 없습니다.")

    session = requests.Session()
    session.headers.update({"x-apisports-key": api_key})

    updated = 0
    for path in files:
        if process_match_file(session, path, args.force):
            updated += 1
        time.sleep(REQUEST_INTERVAL_SEC)

    print(f"\n완료: 총 {updated}개 경기 파일에 이벤트 병합")


if __name__ == "__main__":
    main()
