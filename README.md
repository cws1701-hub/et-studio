# ET Studio — 일본 U15 축구 구단 소개 프로젝트

한국 학부모/선수를 대상으로 일본 U15(주니어유스) 축구 구단을 소개하고,
장기적으로 한국→일본 U15 구단 유학을 안내하는 콘텐츠 스튜디오입니다.

인스타그램(릴스)과 네이버 블로그에 발행할 콘텐츠를 구조화된 구단 DB에서
생성하는 파이프라인을 제공합니다.

## 폴더 구조

```
data/clubs/          # 구단 DB (구단당 YAML 1개, 사실관계 + 출처 + 검증상태)
content/<club_id>/   # 구단별 생성 콘텐츠 (blog/, reels/, captions/)
scripts/             # 콘텐츠 생성 및 발행 파이프라인 스크립트
docs/                # 기획 문서, 운영 가이드, API 연동 가이드
```

## 빠른 시작

```bash
pip install -r requirements.txt
cp .env.example .env   # 인스타그램 API 키 입력 (docs/INSTAGRAM_SETUP.md 참고)

# 1) 구단 DB 확인/수정: data/clubs/*.yaml
# 2) 블로그 초안 생성
python scripts/generate_blog_post.py --club cerezo-osaka-jy --topic intro
# 3) 릴스/쇼츠 대본 생성
python scripts/generate_reels_script.py --club cerezo-osaka-jy --topic intro
# 4) 네이버 블로그용 반자동 발행 초안(HTML) 생성 → 브라우저에서 열어 복사/붙여넣기
python scripts/naver_export.py --club cerezo-osaka-jy --topic intro
# 5) 인스타그램 자동 게시 (Graph API, 사전 설정 필요)
#    이미지는 공개 접근 가능한 URL이어야 합니다 (로컬 경로 불가) — 먼저 이미지 호스팅 후 URL 사용
python scripts/post_instagram.py --dry-run \
  --image-url https://example.com/content/cerezo-osaka-jy/intro_1.jpg \
  --caption content/cerezo-osaka-jy/captions/intro.txt
```

## 운영 원칙 (중요)

- **사실 검증 우선**: 유학/입단/학비 관련 정보는 구단 공식 확인 전까지 `미확인`으로 표기합니다.
  잘못된 정보로 학부모의 유학 결정에 영향을 주지 않도록 `data/clubs/*.yaml`의
  `verification` 필드와 `sources`를 항상 채웁니다. 자세한 규칙은
  `docs/FACT_CHECK_POLICY.md` 참고.
- **네이버 블로그는 반자동**: 네이버는 글쓰기 공식 API를 제공하지 않습니다.
  `naver_export.py`가 발행 직전 HTML까지 만들고, 실제 "발행" 버튼은 사람이 누릅니다.
  자세한 내용은 `docs/NAVER_SEMI_AUTO.md`.
- **인스타그램은 완전자동 가능**: Meta Graph API(비즈니스 계정 필요)로 이미지/릴스
  자동 게시가 가능합니다. 설정은 `docs/INSTAGRAM_SETUP.md`.

## 문서

- [docs/PLANNING.md](docs/PLANNING.md) — 전체 기획 (목표, 페르소나, 콘텐츠 필러, 로드맵)
- [docs/FACT_CHECK_POLICY.md](docs/FACT_CHECK_POLICY.md) — 사실 검증 규칙
- [docs/CLUB_RESEARCH_CHECKLIST.md](docs/CLUB_RESEARCH_CHECKLIST.md) — 구단 리서치 체크리스트
- [docs/CONTENT_CALENDAR.md](docs/CONTENT_CALENDAR.md) — 첫 4주 콘텐츠 캘린더
- [docs/INSTAGRAM_SETUP.md](docs/INSTAGRAM_SETUP.md) — 인스타그램 API 연동 가이드
- [docs/NAVER_SEMI_AUTO.md](docs/NAVER_SEMI_AUTO.md) — 네이버 블로그 반자동 발행 가이드
