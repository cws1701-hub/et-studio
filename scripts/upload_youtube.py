#!/usr/bin/env python3
"""렌더링된 영상(mp4)을 YouTube Data API v3로 업로드합니다.

인스타그램과 달리 공개 URL 호스팅이 필요 없고, 로컬 mp4 파일을 그대로
업로드합니다. 최초 1회는 브라우저 OAuth 동의가 필요하고, 이후에는
저장된 리프레시 토큰으로 자동 인증됩니다 (docs/YOUTUBE_SETUP.md 참고).

.env에 YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET, YOUTUBE_REFRESH_TOKEN을
설정해야 합니다.

사용법:
    python scripts/upload_youtube.py --file output/youtube/2026-09-11/575335_xxx_video.mp4 \\
        --title "..." --description "..." --tags "축구,챔피언스리그"
"""
import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
TOKEN_URI = "https://oauth2.googleapis.com/token"


def get_credentials() -> Credentials:
    client_id = os.environ.get("YOUTUBE_CLIENT_ID")
    client_secret = os.environ.get("YOUTUBE_CLIENT_SECRET")
    refresh_token = os.environ.get("YOUTUBE_REFRESH_TOKEN")
    if not all([client_id, client_secret, refresh_token]):
        sys.exit(
            "YOUTUBE_CLIENT_ID / YOUTUBE_CLIENT_SECRET / YOUTUBE_REFRESH_TOKEN이 "
            ".env에 설정되어 있지 않습니다. docs/YOUTUBE_SETUP.md를 참고해 최초 1회 "
            "OAuth 인증을 진행해주세요."
        )
    creds = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri=TOKEN_URI,
        client_id=client_id,
        client_secret=client_secret,
        scopes=SCOPES,
    )
    creds.refresh(Request())
    return creds


def upload(creds: Credentials, file_path: Path, title: str, description: str, tags: list[str], privacy: str) -> dict:
    youtube = build("youtube", "v3", credentials=creds)
    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags,
            "categoryId": "17",  # Sports
        },
        "status": {"privacyStatus": privacy, "selfDeclaredMadeForKids": False},
    }
    media = MediaFileUpload(str(file_path), chunksize=-1, resumable=True, mimetype="video/mp4")
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"  업로드 중... {int(status.progress() * 100)}%")
    return response


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True, help="업로드할 로컬 mp4 파일 경로")
    parser.add_argument("--title", required=True)
    parser.add_argument("--description", default="")
    parser.add_argument("--tags", default="", help="쉼표로 구분한 태그 목록")
    parser.add_argument(
        "--privacy", default="public", choices=["public", "unlisted", "private"],
        help="공개 범위 (기본값: public)",
    )
    args = parser.parse_args()

    load_dotenv()

    file_path = Path(args.file)
    if not file_path.exists():
        sys.exit(f"파일을 찾을 수 없습니다: {file_path}")

    tags = [t.strip() for t in args.tags.split(",") if t.strip()]

    print(f"[upload_youtube] {file_path.name} 업로드 중...")
    creds = get_credentials()
    result = upload(creds, file_path, args.title, args.description, tags, args.privacy)

    video_id = result["id"]
    print(f"업로드 완료: https://youtu.be/{video_id}")


if __name__ == "__main__":
    main()
