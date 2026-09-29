# 프로젝트: {프로젝트명}

이 저장소는 Codex 기반 step 하네스의 템플릿이다. 아래 프로젝트 필드를 실제 애플리케이션에 맞게 채우고 `docs/`의 기획·설계 문서도 함께 갱신한다. `docs/`의 Next.js 예시는 아직 구현된 애플리케이션을 뜻하지 않는다.

## 대상 애플리케이션 기술 스택

- {프레임워크 (예: Next.js)}
- {언어 (예: TypeScript strict mode)}
- {스타일링 (예: Tailwind CSS)}

## 대상 애플리케이션 아키텍처 규칙

- CRITICAL: {절대 지켜야 할 규칙 1 (예: 모든 API 로직은 서버 라우트에서 처리)}
- CRITICAL: {절대 지켜야 할 규칙 2 (예: 클라이언트에서 비밀 키를 사용하지 않기)}
- {일반 규칙 (예: 컴포넌트와 타입을 별도 디렉토리에 두기)}

## 개발 프로세스

- CRITICAL: 새 기능은 실패하는 테스트를 먼저 작성하고, 통과하는 최소 구현을 만든다 (TDD).
- 커밋 메시지는 Conventional Commits 형식을 따른다 (`feat:`, `fix:`, `docs:`, `refactor:`, `chore:` 등).
- 하네스 step 실행 중에는 `scripts/execute.py`가 브랜치 전환과 두 단계 커밋을 담당한다. step 작업자는 직접 커밋·푸시하거나 다른 에이전트/모델에 재위임하지 않는다.
- 각 step의 Acceptance Criteria에 **해당 프로젝트에서 실제 실행 가능한** 검증 명령을 적고 직접 실행한다. Codex는 예전 Claude `Stop`/`PreToolUse` 훅을 실행하지 않는다. 검증은 AC 명령으로, 파일 쓰기 범위는 Codex sandbox와 적용 가능한 규칙으로 관리한다.

## 이 저장소의 검증 명령

이 저장소의 실행기는 Python이며, 아래 명령은 **하네스 자체**를 검사한다.

```bash
python3 -m pip install -r requirements-dev.txt
python3 -m pytest scripts/test_execute.py scripts/test_portable_skill.py -q
```

## 대상 애플리케이션 명령 예시

아래 명령은 애플리케이션을 만든 뒤 해당 스크립트가 실제 존재할 때만 step AC에 사용한다. 현재 하네스의 검증 명령이 아니다.

```bash
npm run dev
npm run build
npm run lint
npm test
```
