---
name: harness-review
description: Review a target project's changes or harness phase against its AGENTS.md, architecture and ADR decisions, step acceptance criteria, and recorded results. Read-only unless the user authorizes fixes. Use when a harness implementation review is requested.
---

# Harness 변경 리뷰

대상 프로젝트(사용자가 지정한 Git 루트, 없으면 현재 작업 디렉토리)의 `AGENTS.md`, `docs/ARCHITECTURE.md`, `docs/ADR.md`와 대상 phase의 `index.json`, step 파일을 읽는다. `{...}` 미작성 필드는 규칙으로 간주하지 않는다. 변경 파일과 `phases/{phase}/stepN-output.json` 결과를 확인하고, AC와 `AGENTS.md`에 적힌 **그 프로젝트의 실제** 검증 명령을 실행할 수 있으면 직접 실행한다. 존재하지 않는 스크립트나 다른 프로젝트의 테스트 명령을 가정하지 않는다.

다음 항목별로 결과와 근거를 표로 제시한다. 실행하지 못한 명령은 성공으로 표시하지 말고 이유를 적는다.

| 항목 | 결과 | 근거/수정 방안 |
| --- | --- | --- |
| 아키텍처 준수 | 통과/실패/미확인 | 디렉토리와 설계 의도 |
| 기술 스택/ADR 준수 | 통과/실패/미확인 | 실제 결정 사항 |
| 테스트 및 AC | 통과/실패/미확인 | 명령과 결과 |
| CRITICAL 규칙 | 통과/실패/미확인 | AGENTS.md 해당 규칙 |
| 빌드 가능 여부 | 통과/실패/해당 없음/미확인 | 실제 빌드 명령과 결과 |

문제가 있으면 파일 위치, 재현 방법, 구체적인 수정 방안을 덧붙인다. 리뷰만 요청받았다면 코드와 index 상태를 바꾸지 않는다. 사용자가 수정을 허가한 범위에서만 고친다. Codex는 Claude 훅을 실행하지 않으므로 명시적 AC 결과와 sandbox 범위로 확인한다.
