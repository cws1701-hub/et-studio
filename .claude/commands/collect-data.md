`data/matches/` 안의 경기 JSON들을 확인해서, 아직 `goalEvents`/`cardEvents`가
병합 안 된 파일이 있으면 알려줘 (`scripts/fetch_match_events.py`로 먼저 채워야 하는 파일들).

그 다음, 각 경기 JSON에 대해 추천 MOM 선수와 자체 평점(10점 만점)을 판단해서
다음 필드를 추가해줘:

- `mom`: 추천 MOM 선수 이름
- `momReason`: MOM으로 선정한 이유 (경기 데이터에 근거해서 1~2문장)
- `rating`: 자체 평점 (10점 만점, 소수점 1자리)

평점/MOM은 특정 사이트(WhoScored, SofaScore 등) 수치를 그대로 베끼지 말고,
경기 데이터(득점, 어시스트, 카드, 스코어 등)를 근거로 직접 판단해줘.

경기 데이터가 불확실하거나 `goalEvents`/`cardEvents`가 비어 있으면 추측하지 말고
`mom`/`rating`에 "확인 필요"로 표시해줘.

수정한 JSON 파일은 `data/matches/` 안의 원래 파일에 그대로 덮어써줘.
