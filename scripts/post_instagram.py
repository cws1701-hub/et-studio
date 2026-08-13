#!/usr/bin/env python3
"""인스타그램 이미지 자동 게시 (Meta Graph API). docs/INSTAGRAM_SETUP.md 참고.

주의: Graph API는 공개적으로 접근 가능한 이미지 URL이 필요합니다. 로컬 파일
경로가 아니라 이미 호스팅된 이미지의 URL을 --image-url로 전달하세요.

사용법:
    python scripts/post_instagram.py \\
        --image-url https://example.com/intro_1.jpg \\
        --caption content/cerezo-osaka-jy/captions/intro.txt
"""
import argparse
import os
import sys
import time
import requests
from dotenv import load_dotenv

load_dotenv()

GRAPH_API_BASE = "https://graph.facebook.com/v21.0"


def get_credentials():
    ig_user_id = os.environ.get("IG_BUSINESS_ACCOUNT_ID")
    access_token = os.environ.get("IG_ACCESS_TOKEN")
    if not ig_user_id or not access_token:
        sys.exit(
            "IG_BUSINESS_ACCOUNT_ID / IG_ACCESS_TOKEN이 .env에 설정되어 있지 않습니다. "
            ".env.example을 참고해 .env를 만드세요."
        )
    return ig_user_id, access_token


def create_media_container(ig_user_id, access_token, image_url, caption):
    resp = requests.post(
        f"{GRAPH_API_BASE}/{ig_user_id}/media",
        data={"image_url": image_url, "caption": caption, "access_token": access_token},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["id"]


def wait_until_ready(container_id, access_token, timeout=60, interval=3):
    elapsed = 0
    while elapsed < timeout:
        resp = requests.get(
            f"{GRAPH_API_BASE}/{container_id}",
            params={"fields": "status_code", "access_token": access_token},
            timeout=30,
        )
        resp.raise_for_status()
        status = resp.json().get("status_code")
        if status == "FINISHED":
            return
        if status == "ERROR":
            sys.exit(f"미디어 컨테이너 처리 실패 (container_id={container_id})")
        time.sleep(interval)
        elapsed += interval
    sys.exit("미디어 컨테이너 준비 대기 시간 초과")


def publish_media(ig_user_id, access_token, container_id):
    resp = requests.post(
        f"{GRAPH_API_BASE}/{ig_user_id}/media_publish",
        data={"creation_id": container_id, "access_token": access_token},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--image-url", required=True, help="공개 접근 가능한 이미지 URL")
    parser.add_argument("--caption", required=True, help="캡션 텍스트 파일 경로")
    parser.add_argument("--dry-run", action="store_true", help="실제 게시 없이 요청 내용만 출력")
    args = parser.parse_args()

    caption_text = open(args.caption, encoding="utf-8").read().strip()

    if args.dry_run:
        print("[DRY RUN] 아래 내용으로 게시합니다:")
        print(f"  image_url: {args.image_url}")
        print(f"  caption:\n{caption_text}")
        return

    ig_user_id, access_token = get_credentials()
    container_id = create_media_container(ig_user_id, access_token, args.image_url, caption_text)
    print(f"미디어 컨테이너 생성: {container_id}")
    wait_until_ready(container_id, access_token)
    result = publish_media(ig_user_id, access_token, container_id)
    print(f"게시 완료: {result}")


if __name__ == "__main__":
    main()
