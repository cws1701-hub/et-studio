# 영상 제작 & 자동 업로드 파이프라인

`/write-instagram`, `/write-blog`, `/write-youtube`가 만드는 건 텍스트
대본입니다. 이 문서는 그 대본을 실제 영상으로 만들어 인스타그램/유튜브에
자동 게시하는 다음 단계를 설명합니다.

## 전체 흐름

```
경기 JSON (data/matches/)
   │
   ├─ scripts/build_graphics.py    → 자체 제작 그래픽 카드 (PNG, 방송 화면 미사용)
   ├─ scripts/generate_tts.py      → 나레이션 음성 (ElevenLabs, mp3)
   ├─ scripts/assemble_video.py    → 그래픽 + 음성 + 자막 합성 (ffmpeg, mp4)
   │
   ├─ [사람] /approve [경기ID]      → status: pending_approval → approved
   │
   └─ scripts/publish_approved.py  → 승인된 것만 실제 게시
         ├─ 인스타그램: scripts/publish_video.py(공개 URL 호스팅) → post_instagram.py
         ├─ 유튜브: scripts/upload_youtube.py (로컬 파일 직접 업로드)
         └─ 네이버 블로그: 자동 게시 안 함 (공식 API 없음, 사람이 직접 붙여넣기)
```

**최종 업로드는 반드시 사람이 `/approve`를 실행해야 시작됩니다.** 대본이
생성됐다고 자동으로 게시되지 않습니다 (CLAUDE.md 원칙).

## 필요한 시스템 패키지

```bash
sudo apt-get install -y ffmpeg fonts-nanum
```

- `ffmpeg`: 영상 합성 (subtitles 필터가 libass를 통해 자막을 굽습니다)
- `fonts-nanum`: 그래픽 카드와 자막에 쓰는 한글 폰트(나눔고딕)

## 필요한 자격 증명 (`.env`)

| 변수 | 용도 | 발급처 |
|---|---|---|
| `ELEVENLABS_API_KEY`, `ELEVENLABS_VOICE_ID` | 나레이션 음성 합성 | https://elevenlabs.io |
| `VIDEO_ASSETS_REPO`, `GITHUB_TOKEN` | 인스타그램용 영상 공개 호스팅 | 아래 참고 |
| `IG_BUSINESS_ACCOUNT_ID`, `IG_ACCESS_TOKEN` | 인스타그램 게시 | `docs/INSTAGRAM_SETUP.md` |
| `YOUTUBE_CLIENT_ID`, `YOUTUBE_CLIENT_SECRET`, `YOUTUBE_REFRESH_TOKEN` | 유튜브 업로드 | `docs/YOUTUBE_SETUP.md` |

### 인스타그램용 영상 공개 호스팅 (`VIDEO_ASSETS_REPO`)

Meta Graph API는 영상을 **공개적으로 접근 가능한 URL**로만 받습니다. 이
저장소는 비공개일 수 있으므로, 렌더링된 영상만 올릴 **별도의 공개 GitHub
저장소**를 하나 만들어 사용합니다.

1. GitHub에서 새 **공개(Public)** 저장소 생성 (예: `et-studio-assets`)
2. `.env`에 `VIDEO_ASSETS_REPO=<owner>/et-studio-assets` 설정
3. 이 세션에서 실행할 경우 `add_repo` 도구로 그 저장소에 `access: "push"`
   권한을 추가해두면 `scripts/publish_video.py`가 바로 push할 수 있습니다.
   로컬 PC에서 실행할 경우 `git push`가 가능하도록 `gh auth login` 등으로
   미리 인증해두거나 `.env`의 `GITHUB_TOKEN`을 채워주세요.

`scripts/publish_video.py`는 렌더링된 mp4를 이 저장소의 `assets/`
폴더에 커밋·푸시하고, `https://raw.githubusercontent.com/<owner>/<repo>/<branch>/assets/<파일명>`
형태의 URL을 반환합니다.

## 승인 게이트 (approval gate)

`/write-instagram`, `/write-blog`, `/write-youtube`가 만드는 모든 결과물
`.md` 파일 맨 위에는 YAML 프런트매터가 있습니다:

```yaml
---
matchId: 575335
platform: instagram
status: pending_approval
---
```

사람이 내용을 검수한 뒤 `/approve 575335`를 실행하면 `status`가 `approved`로
바뀝니다. 이후 `scripts/publish_approved.py`(매일 자동 체크의 일부로 실행됨)가
`approved` 상태인 항목만 찾아서 그래픽/음성/영상을 만들고 실제로 게시한
뒤 `status: posted`로 표시합니다.

- 자격 증명이 없거나 이 환경의 네트워크 정책으로 API 호출이 막히면, 그
  단계에서 멈추고 `approved` 상태를 유지합니다 (다음 체크 때 재시도).
- 이미 만들어진 그래픽/음성/영상은 다시 만들지 않습니다(멱등).
- 네이버 블로그는 승인되어도 자동 게시되지 않습니다 — 사람이 직접
  스마트에디터에 붙여넣어야 합니다.

## 수동으로 한 단계씩 실행하기

```bash
python scripts/build_graphics.py --match-file 575335_xxx.json
python scripts/generate_tts.py --match-id 575335 --platform instagram
python scripts/assemble_video.py --match-id 575335 --platform instagram
# /approve 575335 실행 후
python scripts/publish_approved.py
```

`--dry-run`을 붙이면 실제로 게시하지 않고 어떤 명령이 실행될지만 확인할 수
있습니다: `python scripts/publish_approved.py --dry-run`
