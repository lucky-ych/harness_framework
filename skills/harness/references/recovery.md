# 복구 절차

1. 실패한 step의 `phases/{phase}/stepN-output.json`에서 `exitCode`, `stdout`(JSONL), `stderr`를 읽고 phase index의 `error_message` 또는 `blocked_reason`을 확인한다. 실행기는 종료 코드 1(error/환경 오류)과 2(blocked)로 종료한다.
2. `error`: 원인을 고친 뒤 해당 step의 `status`를 `pending`으로 바꾸고 `error_message`, `failed_at`을 지운다.
3. `blocked`: 외부 조건(키, 인증, 수동 설정)을 해결한 뒤 `status`를 `pending`으로 바꾸고 `blocked_reason`, `blocked_at`을 지운다.
4. 최상위 `phases/index.json`의 해당 phase `status`도 `pending`으로 되돌린다.
5. 완료된 step과 `summary`는 그대로 두고 같은 명령으로 실행기를 다시 실행한다. 재실행도 step당 최대 3회 호출이다.
6. Codex CLI가 없거나 실행할 수 없으면(`launchError`) step은 `pending`으로 남는다. CLI 설치·인증·PATH를 복구한 뒤 재실행한다.
7. `--project-root`가 Git 루트가 아니라는 오류는 대상 경로를 `git rev-parse --show-toplevel` 결과로 바꿔 해결한다.

로그(`phase*-output.json`, `step*-output.json`)는 `init_project.py`가 추가한 ignore 패턴으로 커밋에서 제외된다.
