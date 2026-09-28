---
name: harness
description: Plan or run a phased implementation in this repository using phases/index.json, self-contained step files, executable acceptance criteria, and scripts/execute.py. Use when the user asks for the harness workflow, phase planning, step creation, or phase execution.
---

# Harness 단계 작업

## A. 탐색과 논의

`AGENTS.md`와 `docs/PRD.md`, `docs/ARCHITECTURE.md`, `docs/ADR.md` 및 작업과 관련된 문서를 읽고 실제 프로젝트 목표와 제약을 확인한다. 이 저장소의 `docs/`는 애플리케이션 설계 템플릿이며 예시 기술 스택이 곧 현재 구현이라는 뜻은 아니다. 미정인 설계 결정이나 실행 불가능한 AC는 사용자와 구체화한다.

## B. Step 설계

구현 계획을 요청받으면 각 step의 범위, 선행 파일, 작업 내용, 실행 가능한 AC를 제시한다. 요청 범위에 phase 파일 생성이 포함되면 아래 형식으로 작성한다.

1. 한 step은 가능한 한 한 레이어/모듈만 다룬다. 필요한 선행 작업은 앞 step으로 분리한다.
2. 각 step은 별도의 Codex 실행에서 읽히므로 대화 참조 없이 자기완결적으로 쓴다. 관련 문서와 선행 step 산출물의 **저장소 상대 경로**를 명시한다.
3. 함수·클래스의 인터페이스와 필수 불변조건(멱등성, 보안, 데이터 무결성 등)을 명시하되 내부 구현은 불필요하게 고정하지 않는다.
4. AC에는 해당 프로젝트에서 실제 실행 가능한 커맨드를 넣는다. 하네스 자체를 변경하는 step이라면 `python3 -m pytest scripts/test_execute.py -q`가 한 예다. 아직 없는 `npm` 스크립트를 AC로 쓰지 않는다.
5. 금지사항은 행동과 이유를 구체적으로 쓴다. step `name`은 `project-setup`, `api-layer`처럼 짧은 kebab-case slug로 쓴다.

## C. 파일 형식

`phases/index.json`은 여러 task의 현황이다. 기존 파일이 있으면 `phases` 배열에 새 항목을 추가한다.

```json
{
  "phases": [
    { "dir": "0-mvp", "status": "pending" }
  ]
}
```

`phases/0-mvp/index.json`은 task 상세다. `phase`는 디렉토리명과 일치시키고, `project`는 `AGENTS.md`의 프로젝트명을 사용한다. step 번호는 0부터 시작한다.

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

상태는 `pending` / `completed` / `error` / `blocked` 중 하나다. 성공 시 step 작업자가 `summary`에 산출물·핵심 결정을 한 줄로 기록한다. AC 실패 시 `error_message`, 사용자 개입이 필요하면 `blocked_reason`을 기록한다. `summary`는 다음 step 프롬프트에 누적된다. `created_at`(task), `started_at`(step), `completed_at` / `failed_at` / `blocked_at`(상태 전이)은 실행기가 기록하므로 새 계획에 미리 넣지 않는다.

각 step마다 `phases/0-mvp/step0.md`와 같은 파일을 만든다. 예를 들어 하네스 자체를 변경하는 step은 다음처럼 쓸 수 있다. 애플리케이션 작업이면 파일 경로와 AC를 그 프로젝트의 실제 구성에 맞게 바꾼다.

````markdown
# Step 0: executor-tests

## 읽어야 할 파일

- AGENTS.md
- docs/ARCHITECTURE.md
- docs/ADR.md
- scripts/execute.py
- scripts/test_execute.py

먼저 파일을 읽고 기존 동작을 확인하라.

## 작업

scripts/execute.py의 대상 기능을 구현한다. 변경할 함수의 입력·출력과 지켜야 할 불변조건을 구체적으로 적는다.

## Acceptance Criteria

```bash
python3 -m pytest scripts/test_execute.py -q
```

## 검증과 결과 기록

1. 위 AC 명령을 직접 실행하고 AGENTS.md의 CRITICAL 규칙과 관련 설계 결정을 확인한다.
2. AC 통과: phases/0-mvp/index.json의 이 step을 `completed`로 바꾸고 `summary`에 산출물을 기록한다.
3. AC 실패: `error`와 실제 `error_message`를 기록한다. 사용자 개입이 필요한 경우 `blocked`와 구체적인 `blocked_reason`을 기록하고 중단한다.

## 금지사항

- 다른 step 파일을 수정하지 마라. 이유: 이 step의 범위가 아니다.
- 직접 브랜치를 전환하거나 commit/push하지 마라. 이유: 상위 실행기가 담당한다.
- 다른 에이전트나 모델에 재위임하지 마라. 이유: step 실행은 한 Codex 호출로 관리된다.
````

## D. 실행 및 복구

```bash
python3 scripts/execute.py 0-mvp
python3 scripts/execute.py 0-mvp --model <configured-model>
python3 scripts/execute.py 0-mvp --push
```

실행기는 `feat-{phase}` 브랜치를 준비하고 `AGENTS.md` + `docs/*.md`를 step 프롬프트에 주입하며, 완료된 step의 summary를 누적한다. 각 step은 최초 실행 포함 최대 3회 호출한다(교정 기회 최대 2회). step 작업자는 별도 재시도 루프를 돌리지 않는다. 실행기가 코드 `feat`와 결과 메타데이터 `chore`를 분리 커밋하고 타임스탬프를 남긴다. `--push`는 전체 phase 완료 후에만 푸시한다.

실패 원인은 `phases/{task}/stepN-output.json`의 `exitCode`, 원시 JSONL `stdout`, `stderr`와 index의 `error_message`/`blocked_reason`에서 확인한다. `error`는 문제를 해결한 뒤 해당 step의 `status`를 `pending`으로 바꾸고 `error_message`, `failed_at`을 지운다. `blocked`는 외부 조건을 해결한 뒤 `status`를 `pending`으로 바꾸고 `blocked_reason`, `blocked_at`을 지운다. 이전 완료 step은 유지하고 실행기를 재실행한다. Codex는 Claude의 `Stop`/`PreToolUse` 훅을 실행하지 않는다. 검증은 step AC를 명시적으로 실행하며 파일 쓰기는 Codex sandbox와 적용 가능한 규칙을 따른다.
