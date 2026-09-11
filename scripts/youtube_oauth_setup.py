#!/usr/bin/env python3
"""YouTube 업로드용 리프레시 토큰을 최초 1회 발급받습니다 (사람이 브라우저로 동의).

Google Cloud Console에서 다운로드한 OAuth 클라이언트 secret json 파일이 필요합니다
(docs/YOUTUBE_SETUP.md 참고). 이 스크립트는 로컬 브라우저를 띄워 동의를 받은 뒤,
YOUTUBE_CLIENT_ID / YOUTUBE_CLIENT_SECRET / YOUTUBE_REFRESH_TOKEN 값을 출력합니다.
이 값들을 .env에 붙여넣으면 이후 scripts/upload_youtube.py는 브라우저 없이
자동으로 인증됩니다.

브라우저가 없는 원격/헤드리스 환경에서는 실행할 수 없습니다 — 로컬 PC에서
실행해주세요.

사용법:
    python scripts/youtube_oauth_setup.py --client-secrets client_secret.json
"""
import argparse
import sys

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--client-secrets", required=True, help="Google Cloud Console에서 받은 OAuth 클라이언트 secret json 경로"
    )
    args = parser.parse_args()

    try:
        flow = InstalledAppFlow.from_client_secrets_file(args.client_secrets, SCOPES)
        creds = flow.run_local_server(port=0)
    except Exception as e:
        sys.exit(
            f"OAuth 인증 실패: {e}\n"
            "브라우저를 열 수 없는 환경이면 로컬 PC에서 이 스크립트를 실행해주세요."
        )

    print("\n아래 값을 .env에 추가하세요:\n")
    print(f"YOUTUBE_CLIENT_ID={creds.client_id}")
    print(f"YOUTUBE_CLIENT_SECRET={creds.client_secret}")
    print(f"YOUTUBE_REFRESH_TOKEN={creds.refresh_token}")


if __name__ == "__main__":
    main()
