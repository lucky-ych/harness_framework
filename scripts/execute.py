#!/usr/bin/env python3
"""저장소 호환용 CLI. 실제 실행기는 skills/harness/scripts/execute.py 에 있다.

Usage:
    python3 scripts/execute.py <phase-dir> [--project-root DIR] [--model MODEL] [--push]

--project-root 를 생략하면 현재 작업 디렉토리가 대상 프로젝트 루트다.
"""

import importlib.util
from pathlib import Path

CANONICAL = Path(__file__).resolve().parent.parent / "skills" / "harness" / "scripts" / "execute.py"


def _load():
    spec = importlib.util.spec_from_file_location("harness_execute", CANONICAL)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    _load().main()


if __name__ == "__main__":
    main()
