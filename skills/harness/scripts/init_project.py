#!/usr/bin/env python3
"""대상 프로젝트에 하네스 템플릿을 만든다. 이미 있는 파일은 절대 덮어쓰지 않는다.

Usage:
    python3 <skill-dir>/scripts/init_project.py [--project-root DIR]

--project-root 를 생략하면 현재 작업 디렉토리를 사용한다. git init, 커밋, 브랜치 전환,
provider 설정은 하지 않는다.
"""

import argparse
import sys
from pathlib import Path

ASSETS = Path(__file__).resolve().parent.parent / "assets"
TEMPLATES = ["AGENTS.md", "docs/PRD.md", "docs/ARCHITECTURE.md", "docs/ADR.md", "phases/index.json"]
NL = chr(10)
IGNORE_PATTERNS = ["phases/**/phase*-output.json", "phases/**/step*-output.json"]


class InitError(Exception):
    pass


def _check_destination(root: Path, rel: str) -> Path:
    """root 아래 목적지를 검사한다. 경로의 어떤 구성요소도 심볼릭 링크이면 거부한다."""
    cur = root
    for part in Path(rel).parts:
        cur = cur / part
        if cur.is_symlink():
            raise InitError(f"symlink destination is not allowed: {cur}")
    return cur


def init_project(project_root) -> dict:
    root = Path(project_root)
    if not root.is_dir():
        raise InitError(f"project root is not a directory: {root}")
    root = root.resolve()

    targets = [(rel, _check_destination(root, rel)) for rel in TEMPLATES + [".gitignore"]]
    result = {"created": [], "kept": [], "gitignore": "unchanged"}

    for rel, dest in targets[:-1]:
        if dest.exists():
            if not dest.is_file():
                raise InitError(f"destination is not a regular file: {dest}")
            result["kept"].append(rel)
            continue
        if dest.parent.exists() and not dest.parent.is_dir():
            raise InitError(f"parent is not a directory: {dest.parent}")
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text((ASSETS / rel).read_text(encoding="utf-8"), encoding="utf-8")
        result["created"].append(rel)

    gitignore = targets[-1][1]
    if gitignore.exists() and not gitignore.is_file():
        raise InitError(f"destination is not a regular file: {gitignore}")
    existing = gitignore.read_text(encoding="utf-8") if gitignore.exists() else ""
    tail = [line.strip() for line in existing.splitlines() if line.strip()][-len(IGNORE_PATTERNS):]
    if tail != IGNORE_PATTERNS:
        # 뒤의 부정(!) 규칙이 앞 규칙을 취소할 수 있으므로 필수 패턴을 항상 파일 끝에 둔다.
        prefix = "" if not existing or existing.endswith(NL) else NL
        gitignore.write_text(existing + prefix + NL.join(IGNORE_PATTERNS) + NL, encoding="utf-8")
        result["gitignore"] = "updated"
    return result


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Create missing harness project templates")
    parser.add_argument("--project-root", default=None,
                        help="Target project root (default: current directory)")
    args = parser.parse_args(argv)
    try:
        result = init_project(args.project_root or Path.cwd())
    except InitError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    for rel in result["created"]:
        print(f"created {rel}")
    for rel in result["kept"]:
        print(f"kept    {rel}")
    print(f".gitignore {result['gitignore']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
