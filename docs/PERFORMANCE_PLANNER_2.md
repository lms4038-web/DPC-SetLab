# Performance Planner 2.0

이번 버전은 실제 오디오 AI 분석 전 단계입니다. Rekordbox XML에 포함된 Cue 이름과 위치를 이용해 곡 구조를 추정합니다.

인식 가능한 대표 Cue 이름:

- Intro / Opening / 인트로
- Build / Pre Drop / 빌드
- Break / Breakdown / Verse / Vocal / 브레이크
- Drop / Chorus / Hook / Main / Peak / 드롭
- Outro / Ending / 아웃트로

피크 역할의 곡은 Drop 구간을, 브리지 역할의 곡은 Break 구간을, 클로징은 Outro가 포함된 구간을 우선합니다. Cue가 너무 적거나 구간이 평균 사용시간보다 지나치게 길면 해당 Cue를 사용하지 않고 BPM·프레이즈 추정으로 돌아갑니다.
