지정된 경기ID(ARGUMENTS로 전달됨)에 대해 사람이 최종 검수를 마쳤다는 뜻이다.
아래 순서로 처리해줘:

1. 다음 경로들에서 해당 경기ID를 가진 결과물 파일을 전부 찾는다 (날짜 폴더는 와일드카드로 탐색):
   - `output/instagram/*/[경기ID]_script.md`
   - `output/naverblog/*/[경기ID]_post.md`
   - `output/youtube/*/[경기ID]_script.md`
2. 찾은 각 파일의 YAML 프런트매터에서 `status: pending_approval`을
   `status: approved`로 바꿔준다. 이미 `approved`나 `posted`인 파일은 건드리지 않고
   그대로 둔다는 것을 알려줘.
3. 프런트매터가 없거나 해당 경기ID의 파일을 하나도 못 찾으면, 먼저
   `/write-instagram`, `/write-blog`, `/write-youtube`로 대본을 생성해야 한다고
   안내하고 아무것도 바꾸지 않는다.
4. 바뀐 파일 목록을 요약해서 보여주고, 커밋·푸시해줘 (다음 자동 체크 때
   `scripts/publish_approved.py`가 `status: approved`인 항목을 찾아서
   인스타그램/유튜브는 자동 게시를, 네이버 블로그는 여전히 사람이 직접 붙여넣어
   발행해야 한다는 점을 함께 안내한다).

승인은 매치 단위로 인스타/블로그/유튜브를 한꺼번에 처리한다 — 플랫폼별로 따로
승인하고 싶다면 사용자가 그렇게 명시적으로 요청할 것이다.
