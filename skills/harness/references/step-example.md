# step 파일 예시

경로와 AC는 대상 프로젝트의 실제 구성에 맞게 바꾼다. 아래 `<검증 명령>`은 자리표시자이며 실제로 존재하는 명령으로 교체해야 한다.

````markdown
# Step 0: project-setup

## 읽어야 할 파일

- AGENTS.md
- docs/ARCHITECTURE.md
- docs/ADR.md
- {이 step이 수정하거나 참고할 파일의 상대 경로}

먼저 파일을 읽고 기존 동작을 확인하라.

## 작업

{구현 대상, 함수·모듈의 입력·출력, 지켜야 할 불변조건}

## Acceptance Criteria

```bash
<검증 명령>
```

## 검증과 결과 기록

1. 위 AC 명령을 직접 실행하고 AGENTS.md의 CRITICAL 규칙과 관련 ADR을 확인한다.
2. AC 통과: phases/0-mvp/index.json의 이 step을 `completed`로 바꾸고 `summary`에 산출물을 기록한다.
3. AC 실패: `error`와 실제 `error_message`를 기록한다. 사용자 개입이 필요하면 `blocked`와 구체적인 `blocked_reason`을 기록하고 중단한다.

## 금지사항

- 다른 step 파일을 수정하지 마라. 이유: 이 step의 범위가 아니다.
- 직접 브랜치를 전환하거나 commit/push하지 마라. 이유: 상위 실행기가 담당한다.
- 다른 에이전트나 모델에 재위임하지 마라. 이유: step 실행은 한 Codex 호출로 관리된다.
````
