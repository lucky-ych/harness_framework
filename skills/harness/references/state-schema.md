# 상태 스키마

## 최상위 `phases/index.json`

```json
{
  "phases": [
    { "dir": "0-mvp", "status": "pending" }
  ]
}
```

기존 파일에는 `phases` 배열에 항목을 추가한다. 실행기가 `status`(`completed`/`error`/`blocked`)와 `completed_at`/`failed_at`/`blocked_at`을 갱신한다.

## phase `phases/0-mvp/index.json`

`phase`는 브랜치 `feat-{phase}`와 커밋 메시지에 쓰이며 디렉토리 이름과 맞추는 것을 권장한다. `project`는 AGENTS.md의 프로젝트명이다. step 번호는 0부터 시작한다.

```json
{
  "project": "ExampleProject",
  "phase": "0-mvp",
  "steps": [
    { "step": 0, "name": "project-setup", "status": "pending" },
    { "step": 1, "name": "core-types", "status": "pending" }
  ]
}
```

상태는 `pending` / `completed` / `error` / `blocked`다.

| 필드 | 기록 주체 | 의미 |
| --- | --- | --- |
| `summary` | step 작업자 | 완료 시 산출물 한 줄 요약. 다음 step 프롬프트에 누적된다 |
| `error_message` | 작업자/실행기 | AC 실패 내용 또는 최종 실패 사유 |
| `blocked_reason` | step 작업자 | 사용자 개입이 필요한 이유 |
| `created_at`, `started_at`, `completed_at`, `failed_at`, `blocked_at` | 실행기 | 타임스탬프. 계획에 미리 넣지 않는다 |

step 파일은 `phases/0-mvp/step0.md`처럼 step 번호로 만든다.
