# 유튜브 자동 업로드 설정 가이드 (YouTube Data API v3)

인스타그램과 달리 유튜브는 로컬 mp4 파일을 그대로 API로 업로드할 수 있어서
별도의 공개 URL 호스팅이 필요 없습니다.

## 1. Google Cloud 프로젝트 준비

1. https://console.cloud.google.com 에서 프로젝트 생성 (또는 기존 프로젝트 사용)
2. "API 및 서비스" → "라이브러리"에서 **YouTube Data API v3** 활성화
3. "API 및 서비스" → "OAuth 동의 화면" 설정
   - User Type: 외부(External) — 개인 채널이면 테스트 사용자로 본인 계정만 등록해도 충분
   - 범위(Scope): `https://www.googleapis.com/auth/youtube.upload`

## 2. OAuth 클라이언트 생성

1. "API 및 서비스" → "사용자 인증 정보" → "사용자 인증 정보 만들기" → **OAuth 클라이언트 ID**
2. 애플리케이션 유형: **데스크톱 앱**
3. 생성된 클라이언트의 JSON 파일을 다운로드 (`client_secret_xxx.json`)

## 3. 리프레시 토큰 발급 (최초 1회, 로컬 PC에서)

이 저장소를 로컬에 클론한 뒤:

```bash
pip install -r requirements.txt
python scripts/youtube_oauth_setup.py --client-secrets /path/to/client_secret_xxx.json
```

브라우저가 열리고 본인 유튜브 계정으로 로그인·동의하면, 터미널에 아래 형식으로
값이 출력됩니다:

```
YOUTUBE_CLIENT_ID=xxxxx.apps.googleusercontent.com
YOUTUBE_CLIENT_SECRET=xxxxx
YOUTUBE_REFRESH_TOKEN=xxxxx
```

이 값들을 `.env`에 그대로 붙여넣으세요. 리프레시 토큰은 만료되지 않으므로
(계정에서 직접 취소하지 않는 한) 이후로는 브라우저 동의 없이 자동 인증됩니다.

이 발급 과정은 **브라우저가 있는 로컬 PC에서만** 가능합니다. 원격/헤드리스
환경(이 세션 포함)에서는 실행할 수 없습니다.

## 4. 업로드 테스트

```bash
python scripts/upload_youtube.py \
  --file output/youtube/2026-09-11/575335_xxx_video.mp4 \
  --title "테스트 업로드" \
  --description "설명" \
  --tags "축구,테스트" \
  --privacy unlisted
```

처음엔 `--privacy unlisted`로 테스트해서 실제로 잘 올라가는지 확인한 뒤,
운영 시 `scripts/publish_approved.py`가 자동으로 `public`으로 업로드합니다.

## 5. 할당량 참고

YouTube Data API는 기본적으로 일일 10,000 유닛 쿼터를 제공하고, 영상 업로드는
1회당 약 1,600 유닛을 소모합니다 (하루 약 6회 업로드 가능). 더 필요하면
Google Cloud Console에서 할당량 증설을 신청할 수 있습니다.
