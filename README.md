# Harness Framework 사용법

Harness는 큰 작업을 범위가 분명한 여러 phase와 step으로 나누어 실행하는 도구입니다. 각 step은 필요한 맥락과 실행 가능한 Acceptance Criteria(AC)를 담은 파일로 정의하고, 독립적인 Claude Code CLI 세션에서 실행합니다. 실행기는 진행 상태와 완료 요약을 파일에 남겨 다음 step으로 전달하므로, 완료한 step을 건너뛰고 중단된 작업을 이어갈 수 있습니다.

## 사용할 브랜치

| 작업 | 브랜치 | 도구 |
|---|---|---|
| Claude Code용 Harness | [`main`](https://github.com/lucky-ych/harness_framework/tree/main) | Claude Code CLI, `CLAUDE.md`, `.claude/commands/` |
| Codex CLI용 Harness | [`codex`](https://github.com/lucky-ych/harness_framework/tree/codex) | Codex CLI, `AGENTS.md`, `.agents/skills/harness`, `.agents/skills/harness-review` |

저장소를 복제한 뒤 사용할 브랜치로 이동합니다.

```bash
git clone https://github.com/lucky-ych/harness_framework.git
cd harness_framework
git switch main
```

Codex 브랜치로 작업할 때는 원격 브랜치를 가져온 다음 전환합니다.

```bash
git fetch origin
git switch codex
```

Codex 브랜치에서는 `$harness`와 `$harness-review`로 각각 `.agents/skills/harness`, `.agents/skills/harness-review`를 사용합니다. 자세한 내용은 [Codex 브랜치 README](https://github.com/lucky-ych/harness_framework/blob/codex/README.md)를 참고하세요. 이 문서의 아래 실행 절차는 현재 `main`의 Claude Code 구현을 설명합니다.

## 준비

`main`의 실행기는 Python 3.9 이상과 Git, 인증이 완료된 Claude Code CLI가 필요합니다. 실행기는 Python 표준 라이브러리만 사용합니다. 저장소의 테스트를 실행하려면 별도로 `pytest`를 설치하세요.

```bash
python3 --version
git --version
claude --version
claude
```

`claude`를 처음 실행할 때 CLI 안내에 따라 로그인과 인증을 완료합니다. 이 저장소는 애플리케이션이 아니라 Harness 템플릿이므로 `package.json`이나 `requirements.txt`는 없습니다. 템플릿의 npm 명령은 실제 애플리케이션의 명령에 맞춰 바꿔야 합니다.

## 프로젝트 설정과 Claude 명령

먼저 템플릿 문서를 실제 애플리케이션에 맞게 채웁니다.

- `CLAUDE.md`: 프로젝트 기술 스택, 아키텍처 규칙, 개발·검증 명령
- `docs/PRD.md`, `docs/ARCHITECTURE.md`, `docs/ADR.md`, `docs/UI_GUIDE.md`: 제품 요구사항, 구조, 기술 결정, UI 지침
- `.claude/commands/harness.md`: `/harness`로 사용할 계획 작성 및 phase 파일 생성 절차
- `.claude/commands/review.md`: `/review` 코드 리뷰 체크리스트
- `.claude/settings.json`: Claude Code 훅 설정 예시

Claude Code를 저장소 루트에서 실행한 뒤 `/harness`를 사용해 문서를 바탕으로 작업을 계획하고 step 초안을 검토합니다. 계획에 동의한 다음 phase 파일을 작성하도록 요청하면 됩니다. `/review`는 변경 사항을 아키텍처·기술 스택·테스트·규칙 기준으로 검토합니다.

현재 `.claude/settings.json`의 Stop 훅은 `npm run lint`, `npm run build`, `npm run test`를 실행하고, Bash용 PreToolUse 훅은 일부 위험 명령 문자열을 검사합니다. 이 저장소에는 npm 프로젝트가 없으므로 실제 앱의 명령으로 조정해야 합니다. 문자열 검사는 가드레일 예시이며 모든 위험한 동작을 막는다고 보장하지 않습니다.

## phase와 step 파일 만들기

계획은 아래 세 종류의 파일로 저장합니다. task 디렉터리 이름, `index.json`의 `phase`, 실행 명령의 인수는 서로 같은 kebab-case 이름을 사용하세요. step 순번은 0부터 시작하고 파일 이름도 `step0.md`부터 시작합니다.

```text
phases/
├── index.json
└── 0-mvp/
    ├── index.json
    └── step0.md
```

`phases/index.json`은 전체 task 목록입니다.

```json
{
  "phases": [
    { "dir": "0-mvp", "status": "pending" }
  ]
}
```

각 task의 `phases/0-mvp/index.json`에는 프로젝트 이름과 step 목록을 둡니다.

```json
{
  "project": "프로젝트명",
  "phase": "0-mvp",
  "steps": [
    { "step": 0, "name": "project-setup", "status": "pending" }
  ]
}
```

상태 값은 `pending`, `completed`, `error`, `blocked`입니다. 새 계획은 모두 `pending`으로 시작합니다. 실행기가 생성하는 타임스탬프는 직접 넣지 않아도 됩니다. step이 완료되면 한 줄 `summary`를 기록하고, 이 요약은 이후 step의 프롬프트에 누적 전달됩니다.

`phases/0-mvp/step0.md`는 독립 세션에 필요한 맥락, 구체적인 작업, 실제로 실행 가능한 AC를 모두 포함해야 합니다. 예를 들면:

~~~markdown
# Step 0: project-setup

## 읽어야 할 파일
- `CLAUDE.md`
- `docs/ARCHITECTURE.md`

## 작업
프로젝트 초기 구조를 만들고 필요한 설정을 추가한다.

## Acceptance Criteria
```bash
python3 -m pytest scripts/test_execute.py -q
```

## 검증 절차
1. 위 AC를 실행하고 결과를 확인한다.
2. `CLAUDE.md`와 아키텍처 지침을 따르는지 확인한다.
3. `phases/0-mvp/index.json`의 이 step을 갱신한다. 성공하면 `completed`와 `summary`, 실패하면 `error`와 `error_message`, 사용자 개입이 필요하면 `blocked`와 `blocked_reason`을 기록한다.

## 금지사항
- 이 step의 범위를 벗어난 기능을 추가하지 않는다.
~~~

위 AC는 이 저장소의 Harness 테스트를 확인하는 예시입니다. 실제 애플리케이션의 step에는 해당 앱의 테스트·빌드 등으로 바꾸세요. 각 step에는 관련 문서와 앞선 step의 산출물 경로를 적어, 세션이 대화 기록 없이도 작업을 이해하게 합니다.

step을 더 추가할 때는 상세 인덱스의 `steps` 배열에 항목을 넣고 대응하는 `step1.md`, `step2.md` 파일도 함께 만듭니다.

계획과 프로젝트 지침은 실행 전에 커밋해 두세요. 실행기는 `git add -A`로 저장소 변경을 스테이징하므로, 해당 task에만 사용하는 깨끗한 Git worktree에서 시작하고 무관한 수정이나 미추적 파일을 두지 마세요.

## 실행

`main`에서 Claude Code용 작업을 시작할 때 저장소 루트에서 실행합니다. 새 `feat-<phase>` 브랜치는 현재 체크아웃된 브랜치를 기준으로 만들어지므로 먼저 `main`에 있는지 확인하세요.

```bash
git switch main
python3 scripts/execute.py 0-mvp
```

모든 step이 성공한 뒤 원격 `origin`에 브랜치를 push하려면 `--push`를 추가합니다.

```bash
python3 scripts/execute.py 0-mvp --push
```

실행기는 `feat-0-mvp` 브랜치를 만들거나 기존 브랜치를 체크아웃하고, 미완료 step을 순서대로 실행합니다. 이미 `completed`인 step은 건너뜁니다. 완료된 산출물의 요약을 다음 step에 전달하고, 코드 변경(`feat`)과 상태·메타데이터 변경(`chore`)을 분리해 커밋합니다. 실행 시작·완료·실패·차단 시각은 JSON 인덱스에 기록하며 `phases/<phase>/step<N>-output.json` 결과 파일은 Git에서 무시됩니다.

Claude 세션은 `claude -p --dangerously-skip-permissions --output-format json`으로 실행되고, 호출당 제한 시간은 1800초입니다. 이 옵션은 무인 실행 중 권한 확인을 건너뛰므로 신뢰할 수 있는 프로젝트에서만 사용하세요. 실행기 자체는 각 step을 최대 3회 호출합니다(최초 실행과 최대 2회 재시도). 이는 Claude 호출 내부의 모델 작업 횟수 제한을 뜻하지 않습니다.

## 오류와 테스트

`phases/<phase>/index.json`에서 `error` 상태의 원인을 수정한 뒤 해당 step을 `pending`으로 바꾸고 `error_message`를 제거합니다. `blocked` 상태에서는 `blocked_reason`에 적힌 사용자 입력, 인증 또는 수동 설정을 해결한 뒤 상태를 `pending`으로 바꾸고 `blocked_reason`을 제거합니다. 이미 완료한 step은 그대로 두고 같은 명령을 다시 실행하면 기존 `feat-<phase>` 브랜치에서 이어갑니다. CLI가 없거나 인증되지 않았다면 먼저 설치·인증 문제를 해결하세요.

테스트는 격리된 가상환경에서 실행할 수 있습니다.

```bash
python3 -m venv /tmp/harness-framework-venv
source /tmp/harness-framework-venv/bin/activate
python3 -m pip install pytest
python3 -m pytest scripts/test_execute.py -q
deactivate
```

이 저장소의 테스트에는 `pytest`가 필요합니다. Harness 실행기 자체에는 외부 Python 패키지가 필요하지 않습니다.
