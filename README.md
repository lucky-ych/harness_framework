# Codex Harness 템플릿

이 저장소의 `main` 브랜치는 Claude용, `codex` 브랜치는 Codex용 하네스 템플릿이다. 이 브랜치는 애플리케이션 구현이 아니라, 문서로 작업을 설계하고 단계별로 실행하는 Python 도구를 제공한다. `docs/`의 Next.js 관련 내용은 채워 넣을 예시다.

## 준비

Python 3.9 이상과 Git이 필요하다. 새로 복제할 때는 Codex 브랜치를 선택한다.

```bash
git clone --branch codex https://github.com/lucky-ych/harness_framework.git
cd harness_framework
codex --version
```

1. Codex CLI를 설치하고 **본인의 Codex 설정과 인증 방식**으로 로그인한다. `codex` 명령을 PATH에서 실행할 수 있어야 한다. OpenCodex나 별도의 제공자 설정은 필요하지 않다.
2. `AGENTS.md`의 프로젝트명, 기술 스택, CRITICAL 규칙을 실제 프로젝트에 맞게 채우고 `docs/PRD.md`, `docs/ARCHITECTURE.md`, `docs/ADR.md` 등 설계 문서를 작성한다.
3. 신뢰한 저장소에서 `.codex/config.toml`은 대화형 기본값으로 `workspace-write` sandbox와 `on-request` 승인을 사용한다. 모델과 제공자는 이 저장소가 지정하지 않는다.

Codex에서 `$harness`로 단계 계획·파일 생성을, `$harness-review`로 변경 리뷰를 요청할 수 있다. 배포용 원본은 `skills/harness/`와 `skills/harness-review/`이고, `.agents/skills/`의 SKILL.md는 이 저장소에서 스킬을 찾기 위한 진입점이다. Codex는 상위 경로의 `AGENTS.md`도 읽으며, 실행기는 같은 규칙과 `docs/*.md`를 각 step 프롬프트에 명시적으로 포함한다.

## Phase 작성과 실행

`$harness`로 설계한 뒤 `phases/index.json`에 task 디렉토리와 `pending` 상태를 등록한다. `phases/0-mvp/index.json`에는 프로젝트명, phase명, 0부터 시작하는 step 번호, kebab-case 이름, `pending` 상태를 넣는다. 각 step을 `phases/0-mvp/step0.md`와 같은 독립된 파일로 작성하고, 읽을 파일, 작업 범위, **실제로 실행 가능한** Acceptance Criteria 명령을 명시한다. 다음은 최소 구조다.

```text
phases/
├── index.json
└── 0-mvp/
    ├── index.json
    ├── step0.md
    └── step1.md
```

```json
{"phases": [{"dir": "0-mvp", "status": "pending"}]}
```

```json
{
  "project": "ExampleProject",
  "phase": "0-mvp",
  "steps": [
    {"step": 0, "name": "project-setup", "status": "pending"},
    {"step": 1, "name": "core-types", "status": "pending"}
  ]
}
```

```bash
python3 scripts/execute.py 0-mvp
python3 scripts/execute.py 0-mvp --model <configured-model>  # 선택 사항
python3 scripts/execute.py 0-mvp --push                      # 완료 후 push
```

`scripts/execute.py`는 `skills/harness/scripts/execute.py`를 호출하는 호환용 CLI다. 대상 프로젝트는 `--project-root`로 지정하며 생략하면 **현재 작업 디렉토리**다(스크립트 위치로 추정하지 않는다). 이 경로는 반드시 대상 Git 저장소의 루트여야 하고, phase 이름은 `0-mvp` 같은 단일 상대 이름이어야 한다.

실행 전에 계획과 설정을 커밋하고, 해당 작업만 담은 깨끗한 워크트리에서 시작한다. 실행기가 `git add -A`를 사용하므로 무관한 변경이나 미추적 파일을 섞지 않는다. 새 작업 브랜치는 현재 브랜치에서 만들어지므로 Codex용 작업은 `codex` 브랜치를 기반으로 준비한다.

실행기는 `feat-{phase}` 브랜치를 준비하고 step을 순서대로 호출한다. 각 호출은 `codex exec --sandbox workspace-write --json --cd <repo> -c approval_policy=never -` 형식이며 전체 프롬프트를 표준 입력으로 전달한다. 대화형 기본 승인과 달리 이 무인 실행에서는 승인 요청을 기다리지 않도록 `never`를 명시한다. `--model`을 생략하면 사용자의 Codex 모델 설정을 따른다. 각 step은 최초 실행 1회와 교정 기회 최대 2회다. 완료 step의 `summary`가 다음 step에 전달된다. step 작업자는 AC를 실행하고 index 상태를 기록하며, 브랜치 전환과 코드/메타데이터 두 단계 커밋은 상위 실행기가 담당한다.

`phases/0-mvp/stepN-output.json`에는 마지막 호출의 원시 JSONL `stdout`, `stderr`, `exitCode`가 JSON 봉투로 저장된다. 실행 종료 코드가 실패면 step이 `completed`라고 기록되어도 성공 처리하지 않는다. 실행기는 `created_at`, `started_at`, `completed_at`, `failed_at`, `blocked_at` 타임스탬프를 적절한 상태에 기록한다.

## 스킬 패키지로 다른 프로젝트에 설치

`skills/harness/`와 `skills/harness-review/` 폴더는 각각 독립적으로 동작한다. **Git이 추적하는 파일만**(`__pycache__`, `*.pyc` 제외) 복사한다. 같은 이름의 스킬이 이미 있으면 덮어쓰지 않으므로, 갱신하려면 기존 폴더를 직접 확인한 뒤 교체한다. 대상은 `~/.agents/skills/`(또는 대상 저장소의 `.agents/skills/`)다. 런타임은 Python 3.9+ 표준 라이브러리만 쓰며 이 저장소의 `.codex/`, `docs/`, 루트 `scripts/`를 참조하지 않는다.

```bash
DEST=~/.agents/skills
mkdir -p "$DEST"
for name in harness harness-review; do
  if [ -e "$DEST/$name" ]; then echo "이미 있음, 건너뜀: $DEST/$name" >&2
  else git ls-files -z "skills/$name" | while IFS= read -r -d '' f; do
    rel="${f#skills/$name/}"
    mkdir -p "$DEST/$name/$(dirname "$rel")"; cp "$f" "$DEST/$name/$rel"
  done; fi
done
SKILL=$DEST/harness
TARGET=/path/to/target-repo          # 반드시 Git 루트

python3 "$SKILL/scripts/init_project.py" --project-root "$TARGET"   # 없는 템플릿만 생성
# 템플릿을 채우고 phase/step 파일을 작성해 커밋한 뒤, 깨끗한 전용 worktree에서:
python3 "$SKILL/scripts/execute.py" 0-mvp --project-root "$TARGET"
```

`init_project.py`는 `AGENTS.md`, `docs/PRD.md`, `docs/ARCHITECTURE.md`, `docs/ADR.md`, 빈 `phases/index.json`을 없을 때만 만들고 기존 파일은 보존한다(반복 실행해도 동일). 로그 ignore 패턴은 `.gitignore`에 추가만 하며, 심볼릭 링크 경로는 거부한다. git init·커밋·브랜치 전환·모델 설정은 하지 않는다.

## 복구와 검증

`error`이면 출력 파일의 오류와 `error_message`를 확인하고 문제를 해결한다. 해당 step의 `status`를 `pending`으로 바꾸고 `error_message`, `failed_at`을 지운 다음 다시 실행한다. `blocked`이면 `blocked_reason`의 외부 조건을 해결하고 `status`를 `pending`으로 바꾸며 `blocked_reason`, `blocked_at`을 지운다. 이미 완료된 step과 그 summary는 그대로 사용한다. CLI 실행 자체가 실패하면 현재 step은 `pending`으로 남으며 출력 파일의 `stderr`를 보고 설치·인증·환경 문제를 복구한다.

하네스 자체를 수정할 때는 Python 개발 의존성을 설치하고 테스트한다.

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements-dev.txt
python3 -m pytest scripts/test_execute.py scripts/test_portable_skill.py -q
```

대상 애플리케이션의 `npm run build`, `npm test` 등은 실제 스크립트를 만든 뒤 해당 step의 AC에 넣는다. Codex는 Claude의 `Stop`/`PreToolUse` 훅을 실행하지 않는다. 이 브랜치에서는 step의 명시적 AC 검증과 Codex sandbox·규칙을 사용한다. 이 저장소의 `.codex/config.toml`은 대화형 기본값이고, 무인 실행의 승인 설정은 실행기 CLI 인자로 별도 지정한다.

Codex 설정의 자세한 의미는 공식 문서의 [비대화형 실행](https://learn.chatgpt.com/docs/non-interactive-mode), [저장소 스킬](https://developers.openai.com/codex/skills), [AGENTS.md](https://developers.openai.com/codex/guides/agents-md), [프로젝트 설정](https://developers.openai.com/codex/config-basic)을 참고한다.
