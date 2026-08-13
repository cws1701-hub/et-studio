#!/usr/bin/env python3
"""인스타그램 이미지/릴스 자동 게시 (Meta Graph API). docs/INSTAGRAM_SETUP.md 참고.

주의: Graph API는 공개적으로 접근 가능한 이미지/영상 URL이 필요합니다. 로컬 파일
경로가 아니라 이미 호스팅된 파일의 URL을 --image-url 또는 --video-url로 전달하세요.

사용법 (이미지):
    python scripts/post_instagram.py \\
        --image-url https://example.com/intro_1.jpg \\
        --caption content/cerezo-osaka-jy/captions/intro.txt

사용법 (릴스):
    python scripts/post_instagram.py \\
        --video-url https://example.com/intro_reel.mp4 \\
        --caption content/cerezo-osaka-jy/captions/intro.txt \\
        --cover-url https://example.com/intro_reel_cover.jpg
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


def create_image_container(ig_user_id, access_token, image_url, caption):
    resp = requests.post(
        f"{GRAPH_API_BASE}/{ig_user_id}/media",
        data={"image_url": image_url, "caption": caption, "access_token": access_token},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["id"]


def create_reels_container(ig_user_id, access_token, video_url, caption, cover_url=None, share_to_feed=True):
    data = {
        "media_type": "REELS",
        "video_url": video_url,
        "caption": caption,
        "share_to_feed": "true" if share_to_feed else "false",
        "access_token": access_token,
    }
    if cover_url:
        data["cover_url"] = cover_url
    resp = requests.post(f"{GRAPH_API_BASE}/{ig_user_id}/media", data=data, timeout=30)
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
        print(f"  처리 중... (status={status}, {elapsed}s 경과)")
        time.sleep(interval)
        elapsed += interval
    sys.exit("미디어 컨테이너 준비 대기 시간 초과 — 영상이 길거나 서버가 혼잡할 수 있습니다. 잠시 후 다시 시도하세요.")


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
    parser.add_argument("--image-url", help="공개 접근 가능한 이미지 URL (이미지 게시용)")
    parser.add_argument("--video-url", help="공개 접근 가능한 영상 URL (릴스 게시용, mp4 권장 9:16)")
    parser.add_argument("--cover-url", help="릴스 커버 이미지 URL (선택)")
    parser.add_argument(
        "--no-share-to-feed", action="store_true", help="릴스를 피드에 노출하지 않고 릴스 탭에만 게시"
    )
    parser.add_argument("--caption", required=True, help="캡션 텍스트 파일 경로")
    parser.add_argument("--dry-run", action="store_true", help="실제 게시 없이 요청 내용만 출력")
    args = parser.parse_args()

    if bool(args.image_url) == bool(args.video_url):
        sys.exit("--image-url 또는 --video-url 중 정확히 하나를 지정하세요.")

    caption_text = open(args.caption, encoding="utf-8").read().strip()
    is_reels = bool(args.video_url)

    if args.dry_run:
        print("[DRY RUN] 아래 내용으로 게시합니다:")
        print(f"  type: {'REELS' if is_reels else 'IMAGE'}")
        print(f"  media_url: {args.video_url or args.image_url}")
        if is_reels and args.cover_url:
            print(f"  cover_url: {args.cover_url}")
        print(f"  caption:\n{caption_text}")
        return

    ig_user_id, access_token = get_credentials()

    if is_reels:
        container_id = create_reels_container(
            ig_user_id,
            access_token,
            args.video_url,
            caption_text,
            cover_url=args.cover_url,
            share_to_feed=not args.no_share_to_feed,
        )
        print(f"릴스 컨테이너 생성: {container_id} (영상 처리 대기 중, 시간이 걸릴 수 있습니다)")
        wait_until_ready(container_id, access_token, timeout=180, interval=5)
    else:
        container_id = create_image_container(ig_user_id, access_token, args.image_url, caption_text)
        print(f"이미지 컨테이너 생성: {container_id}")
        wait_until_ready(container_id, access_token)

    result = publish_media(ig_user_id, access_token, container_id)
    print(f"게시 완료: {result}")


if __name__ == "__main__":
    main()
