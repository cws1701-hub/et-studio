#!/usr/bin/env python3
"""경기 JSON으로부터 영상에 쓸 자체 제작 그래픽 카드(PNG)를 생성합니다.

방송 화면 캡처나 중계 영상은 전혀 사용하지 않고, Pillow로 직접 그린 카드만
사용합니다 (CLAUDE.md 저작권 원칙 준수).

생성되는 5장의 카드 (1080x1920, 9:16):
    01_hook.png       — 훅 구간용 (스코어 미공개, 궁금증 유발)
    02_summary.png    — 경기요약/스코어 공개 구간용
    03_mom.png        — MOM/평점 구간용
    04_standings.png  — 순위 변동 구간용
    05_outro.png      — 마무리/구독·팔로우 유도 구간용

사용법:
    python scripts/build_graphics.py --match-file 575335_fenerbah_e_sk_as_roma.json
"""
import argparse
import json
import sys
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

MATCHES_DIR = Path(__file__).resolve().parent.parent / "data" / "matches"
GRAPHICS_DIR = Path(__file__).resolve().parent.parent / "output" / "graphics"

WIDTH, HEIGHT = 1080, 1920

FONT_DIR = Path("/usr/share/fonts/truetype/nanum")
FONT_BOLD = FONT_DIR / "NanumGothicBold.ttf"
FONT_REGULAR = FONT_DIR / "NanumGothic.ttf"

BG_TOP = (14, 22, 40)
BG_BOTTOM = (28, 42, 74)
ACCENT = (255, 199, 44)
WHITE = (245, 246, 250)
MUTED = (170, 180, 200)


def font(path: Path, size: int) -> ImageFont.FreeTypeFont:
    if not path.exists():
        sys.exit(f"폰트를 찾을 수 없습니다: {path} (fonts-nanum 패키지가 설치되어 있어야 합니다)")
    return ImageFont.truetype(str(path), size)


def vertical_gradient(size, top, bottom) -> Image.Image:
    w, h = size
    base = Image.new("RGB", (1, h))
    draw = ImageDraw.Draw(base)
    for y in range(h):
        t = y / max(h - 1, 1)
        color = tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3))
        draw.point((0, y), fill=color)
    return base.resize((w, h))


def wrapped_text(draw, text, f, max_width):
    avg_char_w = f.getbbox("가")[2] or 1
    wrap_width = max(1, max_width // avg_char_w)
    return "\n".join(textwrap.wrap(text, width=wrap_width, break_long_words=True))


def draw_centered_multiline(draw, text, f, center_x, top_y, fill, max_width, line_spacing=12):
    wrapped = wrapped_text(draw, text, f, max_width)
    bbox = draw.multiline_textbbox((0, 0), wrapped, font=f, spacing=line_spacing, align="center")
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.multiline_text(
        (center_x - w / 2, top_y), wrapped, font=f, fill=fill, spacing=line_spacing, align="center"
    )
    return top_y + h


def base_card(competition_label: str) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    img = vertical_gradient((WIDTH, HEIGHT), BG_TOP, BG_BOTTOM)
    draw = ImageDraw.Draw(img)
    f_label = font(FONT_BOLD, 40)
    draw.rectangle([(0, 0), (WIDTH, 130)], fill=(10, 14, 26))
    draw.text((60, 45), competition_label, font=f_label, fill=ACCENT)
    return img, draw


def save(img: Image.Image, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, "PNG")
    print(f"  저장: {path}")


def card_hook(match: dict, out_path: Path):
    competition = match["competition"]["name"]
    home = match["homeTeam"]["name"]
    away = match["awayTeam"]["name"]

    img, draw = base_card(competition)
    f_teams = font(FONT_BOLD, 72)
    f_vs = font(FONT_REGULAR, 48)
    f_hint = font(FONT_REGULAR, 40)

    y = 640
    y = draw_centered_multiline(draw, home, f_teams, WIDTH / 2, y, WHITE, WIDTH - 160) + 30
    y = draw_centered_multiline(draw, "VS", f_vs, WIDTH / 2, y, ACCENT, WIDTH - 160) + 30
    y = draw_centered_multiline(draw, away, f_teams, WIDTH / 2, y, WHITE, WIDTH - 160) + 80
    draw_centered_multiline(draw, "결과는 과연...?", f_hint, WIDTH / 2, y, MUTED, WIDTH - 200)

    save(img, out_path)


def card_summary(match: dict, out_path: Path):
    competition = match["competition"]["name"]
    home = match["homeTeam"]["name"]
    away = match["awayTeam"]["name"]
    score = match["score"]["fullTime"]
    half = match["score"].get("halfTime", {})

    img, draw = base_card(competition)
    f_team = font(FONT_BOLD, 56)
    f_score = font(FONT_BOLD, 160)
    f_half = font(FONT_REGULAR, 36)

    y = 560
    y = draw_centered_multiline(draw, home, f_team, WIDTH / 2, y, WHITE, WIDTH - 160) + 40
    score_text = f"{score['home']} - {score['away']}"
    y = draw_centered_multiline(draw, score_text, f_score, WIDTH / 2, y, ACCENT, WIDTH - 160) + 40
    y = draw_centered_multiline(draw, away, f_team, WIDTH / 2, y, WHITE, WIDTH - 160) + 60
    if half:
        half_text = f"(전반 {half.get('home', '-')} - {half.get('away', '-')})"
        draw_centered_multiline(draw, half_text, f_half, WIDTH / 2, y, MUTED, WIDTH - 200)

    save(img, out_path)


def card_mom(match: dict, out_path: Path):
    competition = match["competition"]["name"]
    mom = match.get("mom") or "확인 필요"
    reason = match.get("momReason") or "세부 기록 확인 후 업데이트 예정"
    rating = match.get("rating")
    rating_text = f"{rating} / 10" if rating else "확인 필요"

    img, draw = base_card(competition)
    f_label = font(FONT_BOLD, 44)
    f_name = font(FONT_BOLD, 88)
    f_rating = font(FONT_BOLD, 64)
    f_reason = font(FONT_REGULAR, 38)

    y = 500
    y = draw_centered_multiline(draw, "MAN OF THE MATCH", f_label, WIDTH / 2, y, MUTED, WIDTH - 160) + 50
    y = draw_centered_multiline(draw, mom, f_name, WIDTH / 2, y, WHITE, WIDTH - 160) + 40
    y = draw_centered_multiline(draw, f"평점 {rating_text}", f_rating, WIDTH / 2, y, ACCENT, WIDTH - 160) + 60
    draw_centered_multiline(draw, reason, f_reason, WIDTH / 2, y, MUTED, WIDTH - 200)

    save(img, out_path)


def card_standings(match: dict, out_path: Path):
    competition = match["competition"]["name"]
    note = match.get("standingsNote") or "이번 라운드 순위 변동 — 확인 필요"

    img, draw = base_card(competition)
    f_label = font(FONT_BOLD, 44)
    f_note = font(FONT_REGULAR, 46)

    y = 700
    y = draw_centered_multiline(draw, "순위 변동", f_label, WIDTH / 2, y, MUTED, WIDTH - 160) + 60
    draw_centered_multiline(draw, note, f_note, WIDTH / 2, y, WHITE, WIDTH - 200)

    save(img, out_path)


def card_outro(match: dict, out_path: Path):
    competition = match["competition"]["name"]

    img, draw = base_card(competition)
    f_main = font(FONT_BOLD, 64)
    f_sub = font(FONT_REGULAR, 40)

    y = 800
    y = draw_centered_multiline(draw, "저장 & 팔로우", f_main, WIDTH / 2, y, ACCENT, WIDTH - 160) + 50
    draw_centered_multiline(draw, "다음 경기도 놓치지 마세요!", f_sub, WIDTH / 2, y, WHITE, WIDTH - 200)

    save(img, out_path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--match-file", required=True, help="data/matches/ 안의 파일명 (경로 포함해도 됨)")
    args = parser.parse_args()

    match_path = MATCHES_DIR / Path(args.match_file).name
    if not match_path.exists():
        sys.exit(f"파일을 찾을 수 없습니다: {match_path}")

    match = json.loads(match_path.read_text(encoding="utf-8"))
    out_dir = GRAPHICS_DIR / str(match["id"])

    print(f"[{match['id']}] {match['homeTeam']['name']} vs {match['awayTeam']['name']} 그래픽 생성 중...")
    card_hook(match, out_dir / "01_hook.png")
    card_summary(match, out_dir / "02_summary.png")
    card_mom(match, out_dir / "03_mom.png")
    card_standings(match, out_dir / "04_standings.png")
    card_outro(match, out_dir / "05_outro.png")
    print(f"완료: {out_dir}")


if __name__ == "__main__":
    main()
