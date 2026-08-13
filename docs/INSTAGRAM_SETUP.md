# 인스타그램 자동 게시 설정 가이드 (Meta Graph API)

인스타그램은 **비즈니스/크리에이터 계정 + Meta Graph API**로 이미지·릴스 자동
게시가 가능합니다 (2026년 기준 Content Publishing API). 아래 순서대로 진행하세요.

## 1. 계정 준비

1. 인스타그램 계정을 **프로페셔널 계정(비즈니스 또는 크리에이터)** 으로 전환
   (인스타그램 앱 → 설정 → 계정 유형 및 도구 → 프로페셔널 계정으로 전환)
2. 해당 인스타그램 계정을 **Facebook 페이지**에 연결 (Graph API는 연결된
   Facebook 페이지를 경유해서 인스타그램 계정에 접근합니다)

## 2. Meta 개발자 앱 생성

1. https://developers.facebook.com 에서 개발자 계정 등록
2. "앱 만들기" → 유형: **비즈니스**
3. 제품 추가: **Instagram Graph API** (또는 Instagram API with Instagram Login,
   앱 생성 시점의 Meta 콘솔 명칭을 따르세요)
4. 앱 설정에서 Facebook 페이지 ↔ 인스타그램 계정 연결 확인

## 3. 액세스 토큰 발급

1. Graph API 탐색기(Graph API Explorer)에서 아래 권한으로 사용자 토큰 발급
   - `instagram_basic`, `instagram_content_publish`, `pages_show_list`,
     `pages_read_engagement`
2. 단기 토큰 → **장기(60일) 토큰**으로 교환 (Meta 문서의 long-lived token 교환 절차)
3. 앱 검수(App Review)를 통과해야 실제 서비스 운영이 가능합니다. 검수 전에는
   본인/테스트 계정으로만 게시 가능 (Meta 정책은 자주 바뀌므로 발급 시점에
   Meta 공식 문서로 최종 확인하세요)
4. Instagram Business Account ID 조회:
   `GET /me/accounts` → 페이지 ID → `GET /{page-id}?fields=instagram_business_account`

## 4. 이 프로젝트에서 사용하기

`.env` 파일에 아래 값을 채웁니다 (`.env.example` 참고):

```
IG_BUSINESS_ACCOUNT_ID=xxxxxxxxxxxx
IG_ACCESS_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

이미지 게시:

```bash
python scripts/post_instagram.py \
  --image content/cerezo-osaka-jy/images/intro_1.jpg \
  --caption content/cerezo-osaka-jy/captions/intro.txt
```

`post_instagram.py`는 내부적으로 2단계 Graph API 흐름을 따릅니다:
1. `POST /{ig-user-id}/media` — 이미지 URL(공개 접근 가능해야 함) + 캡션으로
   컨테이너 생성
2. `POST /{ig-user-id}/media_publish` — 생성된 컨테이너를 실제 게시

> **주의**: Graph API는 이미지/영상을 **공개적으로 접근 가능한 URL**로 요구합니다.
> 로컬 파일을 바로 올릴 수 없으므로, 이미지를 먼저 어딘가(S3, GitHub Pages,
> 이미지 호스팅 등)에 업로드하고 그 URL을 사용해야 합니다. 릴스(동영상)도
> 동일한 원리이며 `media_type=REELS` 파라미터가 추가로 필요합니다.

## 5. 릴스 게시

`post_instagram.py`는 이미지와 릴스(영상) 게시를 모두 지원합니다.

```bash
python scripts/post_instagram.py \
  --video-url https://example.com/intro_reel.mp4 \
  --cover-url https://example.com/intro_reel_cover.jpg \
  --caption content/cerezo-osaka-jy/captions/intro.txt
```

- 영상 파일은 mp4, 9:16 비율, 3분 이내 권장이며 **공개 접근 가능한 URL**이어야 합니다.
- 내부적으로 `POST /{ig-user-id}/media`에 `media_type=REELS` + `video_url`로
  컨테이너를 만들고, 영상 처리 상태를 폴링(`GET /{container-id}?fields=status_code`)한
  뒤 `media_publish`로 게시합니다. 영상 처리는 이미지보다 오래 걸릴 수 있어
  최대 180초까지 대기합니다.
- `--cover-url`로 커버 이미지를 지정할 수 있고, `--no-share-to-feed`를 주면
  릴스 탭에만 노출되고 피드에는 공유되지 않습니다.
- `--dry-run`으로 실제 게시 없이 요청 내용만 먼저 확인해보세요.
