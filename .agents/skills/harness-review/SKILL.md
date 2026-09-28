---
name: harness-review
description: Review changes in a harness phase or this repository against AGENTS.md, architecture and ADR decisions, step acceptance criteria, tests, and build commands. Use when the user asks for a harness implementation review.
---

# Harness 변경 리뷰

먼저 `AGENTS.md`, `docs/ARCHITECTURE.md`, `docs/ADR.md`와 대상 phase의 `index.json` 및 step 파일을 읽는다. 문서의 미작성 템플릿 값은 실제 구현 규칙으로 간주하지 않는다. 변경 파일과 실행 결과를 확인하고, 작성된 AC 명령을 직접 실행할 수 있으면 실행한다. 현재 Python 하네스 검증은 `python3 -m pytest scripts/test_execute.py -q`다. 대상 애플리케이션의 빌드/린트 명령은 실제 스크립트가 있을 때만 실행한다.

다음 항목별로 결과와 근거를 표로 제시한다. 실행하지 못한 명령은 성공으로 표시하지 말고 이유를 적는다.

| 항목 | 결과 | 근거/수정 방안 |
| --- | --- | --- |
| 아키텍처 준수 | 통과/실패/미확인 | 디렉토리와 설계 의도 |
| 기술 스택/ADR 준수 | 통과/실패/미확인 | 실제 결정 사항 |
| 테스트 및 AC | 통과/실패/미확인 | 명령과 결과 |
| CRITICAL 규칙 | 통과/실패/미확인 | AGENTS.md 해당 규칙 |
| 빌드 가능 여부 | 통과/실패/해당 없음/미확인 | 실제 빌드 명령과 결과 |

문제가 있으면 파일 위치, 재현 방법, 구체적인 수정 방안을 덧붙인다. Codex가 Claude 훅을 실행한다고 가정하지 말고 명시적 AC 검증 결과와 sandbox 범위를 확인한다. 리뷰만 요청받았다면 코드·index 상태를 임의로 바꾸지 않는다.
