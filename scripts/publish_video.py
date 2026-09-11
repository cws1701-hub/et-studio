#!/usr/bin/env python3
"""렌더링된 영상(mp4)을 별도 공개 GitHub 저장소에 올려서, Meta Graph API가
읽을 수 있는 공개 URL(raw.githubusercontent.com)을 만듭니다.

Instagram Graph API는 공개적으로 접근 가능한 영상 URL을 요구하기 때문에
필요한 단계입니다 (docs/INSTAGRAM_SETUP.md 참고). 유튜브 업로드는 로컬 파일을
직접 올리므로 이 단계가 필요 없습니다 (scripts/upload_youtube.py).

.env에 VIDEO_ASSETS_REPO(형식: "owner/repo", 공개 저장소)를 설정해야 합니다.
그 저장소에 push 권한이 있어야 하고(이 세션에서는 add_repo로 access="push" 추가),
로컬에서 실행할 때는 git이 해당 저장소에 푸시할 수 있도록 인증이 되어 있어야
합니다 (gh auth, SSH 키, 또는 GITHUB_TOKEN 환경변수 중 하나).

사용법:
    python scripts/publish_video.py --file output/instagram/2026-09-11/575335_xxx_video.mp4
"""
import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = REPO_ROOT / ".cache" / "video-assets-repo"


def run(cmd: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess:
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        sys.exit(f"명령 실패: {' '.join(cmd)}\n{result.stderr}")
    return result


def clone_url(assets_repo: str) -> str:
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        return f"https://x-access-token:{token}@github.com/{assets_repo}.git"
    return f"https://github.com/{assets_repo}.git"


def ensure_repo_clone(assets_repo: str) -> Path:
    if CACHE_DIR.exists():
        run(["git", "fetch", "origin"], cwd=CACHE_DIR)
        default_branch = get_default_branch(CACHE_DIR)
        run(["git", "checkout", default_branch], cwd=CACHE_DIR)
        run(["git", "reset", "--hard", f"origin/{default_branch}"], cwd=CACHE_DIR)
    else:
        CACHE_DIR.parent.mkdir(parents=True, exist_ok=True)
        run(["git", "clone", "--depth", "1", clone_url(assets_repo), str(CACHE_DIR)])
    return CACHE_DIR


def get_default_branch(repo_dir: Path) -> str:
    result = run(["git", "symbolic-ref", "refs/remotes/origin/HEAD"], cwd=repo_dir)
    return result.stdout.strip().rsplit("/", 1)[-1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True, help="업로드할 로컬 mp4 파일 경로")
    args = parser.parse_args()

    load_dotenv()
    assets_repo = os.environ.get("VIDEO_ASSETS_REPO")
    if not assets_repo:
        sys.exit(
            "VIDEO_ASSETS_REPO가 .env에 설정되어 있지 않습니다 (형식: owner/repo, 공개 저장소). "
            "docs/VIDEO_PIPELINE.md를 참고해주세요."
        )

    local_file = Path(args.file)
    if not local_file.exists():
        sys.exit(f"파일을 찾을 수 없습니다: {local_file}")

    print(f"[publish_video] {assets_repo} 클론/갱신 중...")
    repo_dir = ensure_repo_clone(assets_repo)

    dest_rel = f"assets/{local_file.name}"
    dest_path = repo_dir / dest_rel
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(local_file, dest_path)

    run(["git", "add", dest_rel], cwd=repo_dir)
    diff = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=repo_dir)
    if diff.returncode == 0:
        print("[publish_video] 이미 동일한 파일이 올라가 있습니다 (변경 없음).")
    else:
        run(["git", "commit", "-m", f"Add {local_file.name}"], cwd=repo_dir)
        run(["git", "push", "origin", get_default_branch(repo_dir)], cwd=repo_dir)
        print(f"[publish_video] 푸시 완료: {dest_rel}")

    default_branch = get_default_branch(repo_dir)
    public_url = f"https://raw.githubusercontent.com/{assets_repo}/{default_branch}/{dest_rel}"
    print(public_url)


if __name__ == "__main__":
    main()
