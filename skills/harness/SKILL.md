---
name: harness
description: Plan phased work into self-contained step files with concrete acceptance criteria, initialize harness templates in a target Git project, and run steps through the bundled Codex executor with recoverable state. Use for harness planning, phase/step creation, execution, or recovery.
---

# Harness 단계 작업

두 경로를 구분한다.

- **스킬 디렉토리**: 이 SKILL.md가 있는 폴더. `scripts/`, `assets/`, `references/`는 여기 기준으로 읽는다. 아래 `<skill-dir>`이 이 폴더다.
- **대상 프로젝트**: 작업할 Git 저장소의 루트. 사용자가 지정하거나 현재 작업 디렉토리로 확인하고, 모든 스크립트에 `--project-root <대상>`으로 명시한다. 스킬 설치 위치에서 유추하지 않는다.

## A. 탐색

대상 프로젝트의 `AGENTS.md`와 `docs/PRD.md`, `docs/ARCHITECTURE.md`, `docs/ADR.md` 및 관련 문서를 읽고 목표·제약을 파악한다. `{...}` 미작성 필드는 규칙으로 간주하지 않고 사용자와 구체화한다. 이 파일들이 없고 초기화가 허용된 작업이면 누락 파일만 만든다.

```bash
python3 <skill-dir>/scripts/init_project.py --project-root <대상>
```

이 명령은 없는 파일(AGENTS.md, docs 3종, phases/index.json)만 만들고 기존 내용은 보존하며, 로그 파일 ignore 패턴을 `.gitignore`에 추가한다. git init·커밋·브랜치 전환은 하지 않는다. 생성된 템플릿의 `{...}` 필드는 프로젝트에 맞게 채운다.

## B. Step 설계

1. 한 step은 가능한 한 한 레이어/모듈만 다루고, 선행 작업은 앞 step으로 분리한다.
2. 각 step은 별도 Codex 실행에서 읽히므로 대화 참조 없이 자기완결적으로 쓴다. 읽을 문서와 선행 산출물은 **대상 프로젝트 기준 상대 경로**로 적는다.
3. 인터페이스와 필수 불변조건(멱등성, 보안, 데이터 무결성)은 명시하되 내부 구현은 불필요하게 고정하지 않는다.
4. AC에는 대상 프로젝트에서 **실제로 실행 가능한** 명령만 넣는다. 아직 없는 스크립트를 쓰지 않는다.
5. 금지사항은 행동과 이유를 함께 쓴다. step `name`은 짧은 kebab-case slug다.

phase·step JSON 스키마와 step 파일 예시는 `<skill-dir>/references/state-schema.md`, `<skill-dir>/references/step-example.md`를 읽는다. phase 이름은 `0-mvp`처럼 단일 상대 이름이어야 한다.

계획이나 파일 생성 요청은 실행 승인이 아니다. 실행은 Git을 변경하고 Codex를 호출하므로 사용자가 실행을 요청했을 때만 진행한다.

## C. 실행

실행 전 확인:

- 대상 프로젝트의 Git 루트에서 **깨끗한 전용 worktree**여야 한다. 실행기가 `git add -A`로 전체 변경을 커밋하므로 무관한 변경이 섞이면 안 된다. 계획 파일은 먼저 커밋한다.
- 현재 브랜치가 프로젝트 정책상 올바른 기준 브랜치인지 확인한다. 실행기는 고정 이름 `feat-{phase}`(phase 값은 phase index의 `phase`)를 현재 HEAD에서 만들거나 체크아웃한다.

```bash
python3 <skill-dir>/scripts/execute.py 0-mvp --project-root <대상>
python3 <skill-dir>/scripts/execute.py 0-mvp --project-root <대상> --model <configured-model>   # 선택
python3 <skill-dir>/scripts/execute.py 0-mvp --project-root <대상> --push                        # phase 완료 후 push
```

`--project-root`를 생략하면 현재 작업 디렉토리가 대상이며, 반드시 Git 루트여야 한다. 실행기는 `codex exec --sandbox workspace-write --json`을 호출하고 `approval_policy=never`를 명시한다. `--model`이 없으면 사용자의 Codex 설정을 따른다. 각 step은 최초 포함 최대 3회 호출(교정 최대 2회)이고, step 작업자는 별도 재시도·재위임을 하지 않는다. 코드 `feat` 커밋과 메타데이터 `chore` 커밋은 실행기가 만든다. `--push`는 phase 전체 완료 후에만 push한다.

Claude의 `Stop`/`PreToolUse` 훅은 Codex에서 실행되지 않는다. 검증은 step AC를 직접 실행하는 것으로, 쓰기 범위는 Codex sandbox와 적용 가능한 규칙으로 관리한다.

## D. 상태 확인과 복구

로그는 `phases/{phase}/stepN-output.json`(exitCode, 원시 JSONL stdout, stderr)이고 index의 `error_message`/`blocked_reason`과 함께 본다. `error`/`blocked` step은 원인을 해결한 뒤 수동으로 `pending`으로 되돌리고 실행기를 다시 실행한다. 절차는 `<skill-dir>/references/recovery.md`를 따른다.
