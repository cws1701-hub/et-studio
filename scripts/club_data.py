"""구단 YAML DB 로더 (data/clubs/*.yaml)"""
from pathlib import Path
import yaml

CLUBS_DIR = Path(__file__).resolve().parent.parent / "data" / "clubs"


def list_club_ids():
    return sorted(
        p.stem for p in CLUBS_DIR.glob("*.yaml") if not p.stem.startswith("_")
    )


def load_club(club_id: str) -> dict:
    path = CLUBS_DIR / f"{club_id}.yaml"
    if not path.exists():
        available = ", ".join(list_club_ids()) or "(없음)"
        raise FileNotFoundError(
            f"구단 '{club_id}'을(를) 찾을 수 없습니다. 사용 가능한 구단: {available}"
        )
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def unverified_notice(club: dict) -> str:
    status = club.get("verification", {}).get("status", "draft")
    if status != "verified":
        return (
            "\n> ⚠️ [확인 필요] 이 구단 정보는 아직 공식 검증되지 않았습니다 "
            f"(verification.status = {status}). 학비·기숙사·유학생 수용 여부 등은 "
            "구단 공식 채널로 반드시 재확인 후 게시하세요.\n"
        )
    return ""
