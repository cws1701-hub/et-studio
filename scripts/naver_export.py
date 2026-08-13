#!/usr/bin/env python3
"""블로그 Markdown 초안을 네이버 블로그 스마트에디터에 붙여넣기 좋은
HTML 미리보기로 변환합니다 (반자동 발행용). docs/NAVER_SEMI_AUTO.md 참고.

사용법:
    python scripts/naver_export.py --club cerezo-osaka-jy --topic intro
"""
import argparse
import re
import html
from pathlib import Path


def markdown_to_naver_html(md_text: str) -> str:
    lines = md_text.splitlines()
    out = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            out.append("<p><br></p>")
            continue
        if stripped.startswith("# "):
            out.append(f"<h1>{html.escape(stripped[2:])}</h1>")
        elif stripped.startswith("## "):
            out.append(f"<h2>{html.escape(stripped[3:])}</h2>")
        elif stripped.startswith("> "):
            out.append(f"<blockquote>{html.escape(stripped[2:])}</blockquote>")
        elif stripped.startswith("[이미지:"):
            inner = stripped.strip("[]")
            out.append(
                f'<div style="border:2px dashed #ccc;padding:16px;margin:8px 0;'
                f'color:#888;">🖼 {html.escape(inner)} — 이 위치에 원본 이미지를 '
                f'드래그 앤 드롭하세요</div>'
            )
        elif stripped.startswith("- "):
            out.append(f"<p>&nbsp;&nbsp;• {html.escape(stripped[2:])}</p>")
        elif stripped == "---":
            out.append("<hr>")
        else:
            text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", stripped)
            out.append(f"<p>{text}</p>")
    return "\n".join(out)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--club", required=True)
    parser.add_argument("--topic", default="intro")
    args = parser.parse_args()

    base = Path(__file__).resolve().parent.parent / "content" / args.club / "blog"
    md_path = base / f"{args.topic}.md"
    if not md_path.exists():
        raise FileNotFoundError(
            f"{md_path} 가 없습니다. 먼저 generate_blog_post.py로 초안을 만드세요."
        )

    md_text = md_path.read_text(encoding="utf-8")
    body_html = markdown_to_naver_html(md_text)

    page = f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<title>네이버 블로그 붙여넣기 미리보기 — {args.club}/{args.topic}</title>
<style>
  body {{ font-family: -apple-system, "Malgun Gothic", sans-serif; max-width: 720px;
         margin: 40px auto; line-height: 1.7; color: #222; }}
  .howto {{ background:#fff8db; border:1px solid #e5d98a; padding:12px 16px;
            border-radius:8px; margin-bottom:24px; font-size:14px; }}
</style>
</head>
<body>
<div class="howto">
  <b>사용법</b>: 아래 본문 전체를 선택(Ctrl+A) → 복사(Ctrl+C) 후, 네이버 블로그
  스마트에디터 새 글쓰기 화면에 붙여넣기(Ctrl+V) 하세요. 점선 박스로 표시된
  이미지 위치에는 <code>content/{args.club}/images/</code> 안의 원본 이미지를
  직접 드래그 앤 드롭해서 채워 넣으세요. 발행 버튼은 최종 검수 후 직접 클릭합니다.
</div>
<div id="content">
{body_html}
</div>
</body>
</html>
"""

    out_path = base / f"{args.topic}_naver_preview.html"
    out_path.write_text(page, encoding="utf-8")
    print(f"네이버 발행용 미리보기 생성 완료: {out_path}")
    print("브라우저로 열어 전체 복사 후 네이버 블로그 에디터에 붙여넣으세요.")


if __name__ == "__main__":
    main()
