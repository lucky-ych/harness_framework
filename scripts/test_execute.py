"""Codex step executor의 상태 전이와 프로세스 호출을 검증한다."""

import json
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent))
import execute as ex


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_project(tmp_path):
    """phases/, AGENTS.md, docs/ 를 갖춘 임시 프로젝트 구조."""
    phases_dir = tmp_path / "phases"
    phases_dir.mkdir()

    agents_md = tmp_path / "AGENTS.md"
    agents_md.write_text("# Rules\n- rule one\n- rule two")

    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "arch.md").write_text("# Architecture\nSome content")
    (docs_dir / "guide.md").write_text("# Guide\nAnother doc")

    return tmp_path


@pytest.fixture
def phase_dir(tmp_project):
    """step 3개를 가진 phase 디렉토리."""
    d = tmp_project / "phases" / "0-mvp"
    d.mkdir()

    index = {
        "project": "TestProject",
        "phase": "mvp",
        "steps": [
            {"step": 0, "name": "setup", "status": "completed", "summary": "프로젝트 초기화 완료"},
            {"step": 1, "name": "core", "status": "completed", "summary": "핵심 로직 구현"},
            {"step": 2, "name": "ui", "status": "pending"},
        ],
    }
    (d / "index.json").write_text(json.dumps(index, indent=2, ensure_ascii=False))
    (d / "step2.md").write_text("# Step 2: UI\n\nUI를 구현하세요.")

    return d


@pytest.fixture
def top_index(tmp_project):
    """phases/index.json (top-level)."""
    top = {
        "phases": [
            {"dir": "0-mvp", "status": "pending"},
            {"dir": "1-polish", "status": "pending"},
        ]
    }
    p = tmp_project / "phases" / "index.json"
    p.write_text(json.dumps(top, indent=2))
    return p


@pytest.fixture
def executor(tmp_project, phase_dir):
    """테스트용 StepExecutor 인스턴스. git 호출은 별도 mock 필요."""
    with patch.object(ex, "ROOT", tmp_project):
        inst = ex.StepExecutor("0-mvp")
    # 내부 경로를 tmp_project 기준으로 재설정
    inst._root = str(tmp_project)
    inst._phases_dir = tmp_project / "phases"
    inst._phase_dir = phase_dir
    inst._phase_dir_name = "0-mvp"
    inst._index_file = phase_dir / "index.json"
    inst._top_index_file = tmp_project / "phases" / "index.json"
    return inst


# ---------------------------------------------------------------------------
# _stamp (= 이전 now_iso)
# ---------------------------------------------------------------------------

class TestStamp:
    def test_returns_kst_timestamp(self, executor):
        result = executor._stamp()
        assert "+0900" in result

    def test_format_is_iso(self, executor):
        result = executor._stamp()
        dt = datetime.strptime(result, "%Y-%m-%dT%H:%M:%S%z")
        assert dt.tzinfo is not None

    def test_is_current_time(self, executor):
        before = datetime.now(ex.StepExecutor.TZ).replace(microsecond=0)
        result = executor._stamp()
        after = datetime.now(ex.StepExecutor.TZ).replace(microsecond=0) + timedelta(seconds=1)
        parsed = datetime.strptime(result, "%Y-%m-%dT%H:%M:%S%z")
        assert before <= parsed <= after


# ---------------------------------------------------------------------------
# _read_json / _write_json
# ---------------------------------------------------------------------------

class TestJsonHelpers:
    def test_roundtrip(self, tmp_path):
        data = {"key": "값", "nested": [1, 2, 3]}
        p = tmp_path / "test.json"
        ex.StepExecutor._write_json(p, data)
        loaded = ex.StepExecutor._read_json(p)
        assert loaded == data

    def test_save_ensures_ascii_false(self, tmp_path):
        p = tmp_path / "test.json"
        ex.StepExecutor._write_json(p, {"한글": "테스트"})
        raw = p.read_text()
        assert "한글" in raw
        assert "\\u" not in raw

    def test_save_indented(self, tmp_path):
        p = tmp_path / "test.json"
        ex.StepExecutor._write_json(p, {"a": 1})
        raw = p.read_text()
        assert "\n" in raw

    def test_load_nonexistent_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            ex.StepExecutor._read_json(tmp_path / "nope.json")


# ---------------------------------------------------------------------------
# _load_guardrails
# ---------------------------------------------------------------------------

class TestLoadGuardrails:
    def test_loads_agents_md_and_docs(self, executor, tmp_project):
        with patch.object(ex, "ROOT", tmp_project):
            result = executor._load_guardrails()
        assert "# Rules" in result
        assert "rule one" in result
        assert "# Architecture" in result
        assert "# Guide" in result

    def test_sections_separated_by_divider(self, executor, tmp_project):
        with patch.object(ex, "ROOT", tmp_project):
            result = executor._load_guardrails()
        assert "---" in result

    def test_docs_sorted_alphabetically(self, executor, tmp_project):
        with patch.object(ex, "ROOT", tmp_project):
            result = executor._load_guardrails()
        arch_pos = result.index("arch")
        guide_pos = result.index("guide")
        assert arch_pos < guide_pos

    def test_no_agents_md(self, executor, tmp_project):
        (tmp_project / "AGENTS.md").unlink()
        with patch.object(ex, "ROOT", tmp_project):
            result = executor._load_guardrails()
        assert "AGENTS.md" not in result
        assert "Architecture" in result

    def test_no_docs_dir(self, executor, tmp_project):
        import shutil
        shutil.rmtree(tmp_project / "docs")
        with patch.object(ex, "ROOT", tmp_project):
            result = executor._load_guardrails()
        assert "Rules" in result
        assert "Architecture" not in result

    def test_empty_project(self, tmp_path):
        with patch.object(ex, "ROOT", tmp_path):
            # executor가 필요 없는 static-like 동작이므로 임시 인스턴스
            phases_dir = tmp_path / "phases" / "dummy"
            phases_dir.mkdir(parents=True)
            idx = {"project": "T", "phase": "t", "steps": []}
            (phases_dir / "index.json").write_text(json.dumps(idx))
            inst = ex.StepExecutor.__new__(ex.StepExecutor)
            result = inst._load_guardrails()
        assert result == ""


# ---------------------------------------------------------------------------
# _build_step_context
# ---------------------------------------------------------------------------

class TestBuildStepContext:
    def test_includes_completed_with_summary(self, phase_dir):
        index = json.loads((phase_dir / "index.json").read_text())
        result = ex.StepExecutor._build_step_context(index)
        assert "Step 0 (setup): 프로젝트 초기화 완료" in result
        assert "Step 1 (core): 핵심 로직 구현" in result

    def test_excludes_pending(self, phase_dir):
        index = json.loads((phase_dir / "index.json").read_text())
        result = ex.StepExecutor._build_step_context(index)
        assert "ui" not in result

    def test_excludes_completed_without_summary(self, phase_dir):
        index = json.loads((phase_dir / "index.json").read_text())
        del index["steps"][0]["summary"]
        result = ex.StepExecutor._build_step_context(index)
        assert "setup" not in result
        assert "core" in result

    def test_empty_when_no_completed(self):
        index = {"steps": [{"step": 0, "name": "a", "status": "pending"}]}
        result = ex.StepExecutor._build_step_context(index)
        assert result == ""

    def test_has_header(self, phase_dir):
        index = json.loads((phase_dir / "index.json").read_text())
        result = ex.StepExecutor._build_step_context(index)
        assert result.startswith("## 이전 Step 산출물")


# ---------------------------------------------------------------------------
# _build_preamble
# ---------------------------------------------------------------------------

class TestBuildPreamble:
    def test_includes_project_name(self, executor):
        result = executor._build_preamble("", "")
        assert "TestProject" in result

    def test_includes_guardrails(self, executor):
        result = executor._build_preamble("GUARD_CONTENT", "")
        assert "GUARD_CONTENT" in result

    def test_includes_step_context(self, executor):
        ctx = "## 이전 Step 산출물\n\n- Step 0: done"
        result = executor._build_preamble("", ctx)
        assert "이전 Step 산출물" in result

    def test_executor_owns_commits_and_no_recursive_delegation(self, executor):
        result = executor._build_preamble("", "")
        assert "직접 git commit/push 하지 마라" in result
        assert "다른 에이전트나 모델을 호출하지 말고" in result

    def test_includes_rules(self, executor):
        result = executor._build_preamble("", "")
        assert "작업 규칙" in result
        assert "AC" in result

    def test_no_retry_section_by_default(self, executor):
        result = executor._build_preamble("", "")
        assert "이전 시도 실패" not in result

    def test_retry_section_with_prev_error(self, executor):
        result = executor._build_preamble("", "", prev_error="타입 에러 발생")
        assert "이전 시도 실패" in result
        assert "타입 에러 발생" in result

    def test_does_not_delegate_retry_policy(self, executor):
        result = executor._build_preamble("", "")
        assert "회 수정 시도" not in result

    def test_includes_index_path(self, executor):
        result = executor._build_preamble("", "")
        assert "phases/0-mvp/index.json" in result


# ---------------------------------------------------------------------------
# _update_top_index
# ---------------------------------------------------------------------------

class TestUpdateTopIndex:
    def test_completed(self, executor, top_index):
        executor._top_index_file = top_index
        executor._update_top_index("completed")
        data = json.loads(top_index.read_text())
        mvp = next(p for p in data["phases"] if p["dir"] == "0-mvp")
        assert mvp["status"] == "completed"
        assert "completed_at" in mvp

    def test_error(self, executor, top_index):
        executor._top_index_file = top_index
        executor._update_top_index("error")
        data = json.loads(top_index.read_text())
        mvp = next(p for p in data["phases"] if p["dir"] == "0-mvp")
        assert mvp["status"] == "error"
        assert "failed_at" in mvp

    def test_blocked(self, executor, top_index):
        executor._top_index_file = top_index
        executor._update_top_index("blocked")
        data = json.loads(top_index.read_text())
        mvp = next(p for p in data["phases"] if p["dir"] == "0-mvp")
        assert mvp["status"] == "blocked"
        assert "blocked_at" in mvp

    def test_other_phases_unchanged(self, executor, top_index):
        executor._top_index_file = top_index
        executor._update_top_index("completed")
        data = json.loads(top_index.read_text())
        polish = next(p for p in data["phases"] if p["dir"] == "1-polish")
        assert polish["status"] == "pending"

    def test_nonexistent_dir_is_noop(self, executor, top_index):
        executor._top_index_file = top_index
        executor._phase_dir_name = "no-such-dir"
        original = json.loads(top_index.read_text())
        executor._update_top_index("completed")
        after = json.loads(top_index.read_text())
        for p_before, p_after in zip(original["phases"], after["phases"]):
            assert p_before["status"] == p_after["status"]

    def test_no_top_index_file(self, executor, tmp_path):
        executor._top_index_file = tmp_path / "nonexistent.json"
        executor._update_top_index("completed")  # should not raise


# ---------------------------------------------------------------------------
# _checkout_branch (mocked)
# ---------------------------------------------------------------------------

class TestCheckoutBranch:
    def _mock_git(self, executor, responses):
        call_idx = {"i": 0}
        def fake_git(*args):
            idx = call_idx["i"]
            call_idx["i"] += 1
            if idx < len(responses):
                return responses[idx]
            return MagicMock(returncode=0, stdout="", stderr="")
        executor._run_git = fake_git

    def test_already_on_branch(self, executor):
        self._mock_git(executor, [
            MagicMock(returncode=0, stdout="feat-mvp\n", stderr=""),
        ])
        executor._checkout_branch()  # should return without checkout

    def test_branch_exists_checkout(self, executor):
        self._mock_git(executor, [
            MagicMock(returncode=0, stdout="main\n", stderr=""),
            MagicMock(returncode=0, stdout="", stderr=""),
            MagicMock(returncode=0, stdout="", stderr=""),
        ])
        executor._checkout_branch()

    def test_branch_not_exists_create(self, executor):
        self._mock_git(executor, [
            MagicMock(returncode=0, stdout="main\n", stderr=""),
            MagicMock(returncode=1, stdout="", stderr="not found"),
            MagicMock(returncode=0, stdout="", stderr=""),
        ])
        executor._checkout_branch()

    def test_checkout_fails_exits(self, executor):
        self._mock_git(executor, [
            MagicMock(returncode=0, stdout="main\n", stderr=""),
            MagicMock(returncode=1, stdout="", stderr=""),
            MagicMock(returncode=1, stdout="", stderr="dirty tree"),
        ])
        with pytest.raises(SystemExit) as exc_info:
            executor._checkout_branch()
        assert exc_info.value.code == 1

    def test_no_git_exits(self, executor):
        self._mock_git(executor, [
            MagicMock(returncode=1, stdout="", stderr="not a git repo"),
        ])
        with pytest.raises(SystemExit) as exc_info:
            executor._checkout_branch()
        assert exc_info.value.code == 1


# ---------------------------------------------------------------------------
# _commit_step (mocked)
# ---------------------------------------------------------------------------

class TestCommitStep:
    def test_two_phase_commit(self, executor):
        calls = []
        def fake_git(*args):
            calls.append(args)
            if args[:2] == ("diff", "--cached"):
                return MagicMock(returncode=1)
            return MagicMock(returncode=0, stdout="", stderr="")
        executor._run_git = fake_git

        executor._commit_step(2, "ui")

        commit_calls = [c for c in calls if c[0] == "commit"]
        assert len(commit_calls) == 2
        assert "feat(mvp):" in commit_calls[0][2]
        assert "chore(mvp):" in commit_calls[1][2]

    def test_no_code_changes_skips_feat_commit(self, executor):
        call_count = {"diff": 0}
        calls = []
        def fake_git(*args):
            calls.append(args)
            if args[:2] == ("diff", "--cached"):
                call_count["diff"] += 1
                if call_count["diff"] == 1:
                    return MagicMock(returncode=0)
                return MagicMock(returncode=1)
            return MagicMock(returncode=0, stdout="", stderr="")
        executor._run_git = fake_git

        executor._commit_step(2, "ui")

        commit_msgs = [c[2] for c in calls if c[0] == "commit"]
        assert len(commit_msgs) == 1
        assert "chore" in commit_msgs[0]


# ---------------------------------------------------------------------------
# _invoke_codex (mocked)
# ---------------------------------------------------------------------------

class TestInvokeCodex:
    def test_invokes_codex_with_stdin_and_cwd(self, executor):
        raw_jsonl = '{"type":"thread.started"}\n{"type":"turn.completed"}\n'
        mock_result = MagicMock(returncode=0, stdout=raw_jsonl, stderr="")
        step = {"step": 2, "name": "ui"}
        preamble = "PREAMBLE\n"

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            output = executor._invoke_codex(step, preamble)

        cmd = mock_run.call_args[0][0]
        assert cmd == ["codex", "exec", "--sandbox", "workspace-write", "--json",
                       "--cd", executor._root, "-c", "approval_policy=never", "-"]
        kwargs = mock_run.call_args.kwargs
        assert kwargs["cwd"] == executor._root
        assert kwargs["input"].startswith("PREAMBLE\n")
        assert "UI를 구현하세요" in kwargs["input"]
        assert kwargs["capture_output"] and kwargs["text"]
        assert output["stdout"] == raw_jsonl

    def test_optional_model_only_when_supplied(self, executor):
        executor._model = "configured-choice"
        with patch("subprocess.run", return_value=MagicMock(returncode=0, stdout="", stderr="")) as mock_run:
            executor._invoke_codex({"step": 2, "name": "ui"}, "")
        assert mock_run.call_args.args[0][-3:] == ["--model", "configured-choice", "-"]

    def test_saves_output_json(self, executor):
        mock_result = MagicMock(returncode=0, stdout='{"ok": true}', stderr="")
        step = {"step": 2, "name": "ui"}

        with patch("subprocess.run", return_value=mock_result):
            executor._invoke_codex(step, "preamble")

        output_file = executor._phase_dir / "step2-output.json"
        assert output_file.exists()
        data = json.loads(output_file.read_text())
        assert data["step"] == 2
        assert data["name"] == "ui"
        assert data["exitCode"] == 0

    def test_nonexistent_step_file_exits(self, executor):
        step = {"step": 99, "name": "nonexistent"}
        with pytest.raises(SystemExit) as exc_info:
            executor._invoke_codex(step, "preamble")
        assert exc_info.value.code == 1

    def test_timeout_is_1800(self, executor):
        mock_result = MagicMock(returncode=0, stdout="{}", stderr="")
        step = {"step": 2, "name": "ui"}

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            executor._invoke_codex(step, "preamble")

        assert mock_run.call_args[1]["timeout"] == 1800

    def test_timeout_preserves_partial_output_and_reason(self, executor):
        exc = subprocess.TimeoutExpired("codex", 1800, output=b'{"type":"thread.started"}\n', stderr=b"slow")
        with patch("subprocess.run", side_effect=exc):
            output = executor._invoke_codex({"step": 2, "name": "ui"}, "")
        assert output["exitCode"] is None
        assert output["stdout"] == '{"type":"thread.started"}\n'
        assert "timed out" in output["stderr"]
        assert "slow" in output["stderr"]

    def test_missing_binary_is_logged_as_launch_error(self, executor):
        with patch("subprocess.run", side_effect=FileNotFoundError("codex")):
            output = executor._invoke_codex({"step": 2, "name": "ui"}, "")
        assert output["exitCode"] is None
        assert output["launchError"] is True
        assert "Could not launch Codex CLI" in output["stderr"]
        assert json.loads((executor._phase_dir / "step2-output.json").read_text()) == output

    def test_other_launch_error_is_logged(self, executor):
        with patch("subprocess.run", side_effect=PermissionError("execution denied")):
            output = executor._invoke_codex({"step": 2, "name": "ui"}, "")
        assert output["launchError"] is True
        assert "execution denied" in output["stderr"]


class TestStepLoop:
    @staticmethod
    def _set_step(executor, status, **fields):
        index = executor._read_json(executor._index_file)
        step = index["steps"][2]
        step.update(status=status, **fields)
        executor._write_json(executor._index_file, index)

    def test_completed_step_requires_clean_process_exit(self, executor):
        prompts = []

        def fake_codex(cmd, **kwargs):
            prompts.append(kwargs["input"])
            if len(prompts) == 1:
                self._set_step(executor, "completed", summary="false success")
                return subprocess.CompletedProcess(cmd, 17, '{"type":"turn.failed"}\n', "process failed")
            index = executor._read_json(executor._index_file)
            assert index["steps"][2]["status"] == "pending"
            assert "summary" not in index["steps"][2]
            self._set_step(executor, "completed", summary="actual work")
            return subprocess.CompletedProcess(cmd, 0, '{"type":"turn.completed"}\n', "")

        with patch("subprocess.run", side_effect=fake_codex), patch.object(executor, "_commit_step") as commit:
            assert executor._execute_single_step({"step": 2, "name": "ui"}, "RULES")

        assert len(prompts) == 2
        assert "process failed" in prompts[1]
        assert "Step 0 (setup): 프로젝트 초기화 완료" in prompts[0]
        assert "Step 1 (core): 핵심 로직 구현" in prompts[0]
        assert "직접 git commit/push 하지 마라" in prompts[0]
        assert "false success" not in prompts[1]
        commit.assert_called_once_with(2, "ui")
        index = executor._read_json(executor._index_file)
        assert index["steps"][2]["status"] == "completed"
        assert index["steps"][2]["summary"] == "actual work"
        assert "completed_at" in index["steps"][2]
        assert index["steps"][0]["status"] == "completed"

    def test_three_total_attempts_end_in_error(self, executor, top_index):
        calls = []

        def fake_codex(cmd, **kwargs):
            calls.append(kwargs["input"])
            if len(calls) == 1:
                self._set_step(executor, "error", error_message="AC failed")
                return subprocess.CompletedProcess(cmd, 0, "", "")
            if len(calls) == 2:
                return subprocess.CompletedProcess(cmd, 0, "", "")
            self._set_step(executor, "completed", summary="not really done")
            return subprocess.CompletedProcess(cmd, 1, "", "last process failure")

        with patch("subprocess.run", side_effect=fake_codex), patch.object(executor, "_commit_step") as commit:
            with pytest.raises(SystemExit) as exc_info:
                executor._execute_single_step({"step": 2, "name": "ui"}, "")

        assert exc_info.value.code == 1
        assert len(calls) == 3
        assert "AC failed" in calls[1]
        assert "Step did not update status" in calls[2]
        index = executor._read_json(executor._index_file)
        step = index["steps"][2]
        assert step["status"] == "error"
        assert "last process failure" in step["error_message"]
        assert "summary" not in step and "completed_at" not in step
        assert "failed_at" in step
        assert executor._read_json(top_index)["phases"][0]["status"] == "error"
        commit.assert_called_once_with(2, "ui")

    def test_blocked_step_stops_without_retry(self, executor, top_index):
        def fake_codex(cmd, **kwargs):
            self._set_step(executor, "blocked", blocked_reason="API key required")
            return subprocess.CompletedProcess(cmd, 0, "", "")

        with patch("subprocess.run", side_effect=fake_codex) as run, patch.object(executor, "_commit_step") as commit:
            with pytest.raises(SystemExit) as exc_info:
                executor._execute_single_step({"step": 2, "name": "ui"}, "")

        assert exc_info.value.code == 2
        run.assert_called_once()
        commit.assert_not_called()
        step = executor._read_json(executor._index_file)["steps"][2]
        assert step["status"] == "blocked" and "blocked_at" in step
        assert executor._read_json(top_index)["phases"][0]["status"] == "blocked"

    def test_missing_cli_fails_fast_and_preserves_pending_step(self, executor, top_index):
        with patch("subprocess.run", side_effect=FileNotFoundError("codex")) as run, patch.object(executor, "_commit_step") as commit:
            with pytest.raises(SystemExit) as exc_info:
                executor._execute_single_step({"step": 2, "name": "ui"}, "")

        assert exc_info.value.code == 1
        run.assert_called_once()
        commit.assert_not_called()
        index = executor._read_json(executor._index_file)
        assert [s["status"] for s in index["steps"]] == ["completed", "completed", "pending"]
        assert executor._read_json(top_index)["phases"][0]["status"] == "pending"
        assert executor._read_json(executor._phase_dir / "step2-output.json")["launchError"]

    def test_timeout_is_bounded_and_recoverable(self, executor):
        calls = []

        def fake_codex(cmd, **kwargs):
            calls.append(kwargs["input"])
            if len(calls) == 1:
                raise subprocess.TimeoutExpired(cmd, 1800, output=b'partial\n', stderr=b'stalled')
            self._set_step(executor, "completed", summary="recovered")
            return subprocess.CompletedProcess(cmd, 0, '{"type":"turn.completed"}\n', "")

        with patch("subprocess.run", side_effect=fake_codex), patch.object(executor, "_commit_step"):
            assert executor._execute_single_step({"step": 2, "name": "ui"}, "")
        assert len(calls) == 2
        assert "timed out" in calls[1]


# ---------------------------------------------------------------------------
# progress_indicator (= 이전 Spinner)
# ---------------------------------------------------------------------------

class TestProgressIndicator:
    def test_context_manager(self):
        import time
        with ex.progress_indicator("test") as pi:
            time.sleep(0.15)
        assert pi.elapsed >= 0.1

    def test_elapsed_increases(self):
        import time
        with ex.progress_indicator("test") as pi:
            time.sleep(0.2)
        assert pi.elapsed > 0


# ---------------------------------------------------------------------------
# main() CLI 파싱 (mocked)
# ---------------------------------------------------------------------------

class TestMainCli:
    def test_no_args_exits(self):
        with patch("sys.argv", ["execute.py"]):
            with pytest.raises(SystemExit) as exc_info:
                ex.main()
            assert exc_info.value.code == 2  # argparse exits with 2

    def test_invalid_phase_dir_exits(self):
        with patch("sys.argv", ["execute.py", "nonexistent"]):
            with patch.object(ex, "ROOT", Path("/tmp/fake_nonexistent")):
                with pytest.raises(SystemExit) as exc_info:
                    ex.main()
                assert exc_info.value.code == 1

    def test_missing_index_exits(self, tmp_project):
        (tmp_project / "phases" / "empty").mkdir()
        with patch("sys.argv", ["execute.py", "empty"]):
            with patch.object(ex, "ROOT", tmp_project):
                with pytest.raises(SystemExit) as exc_info:
                    ex.main()
                assert exc_info.value.code == 1

    def test_model_and_push_are_forwarded(self):
        with patch("sys.argv", ["execute.py", "0-mvp", "--model", "my-model", "--push"]), patch.object(ex, "StepExecutor") as cls:
            ex.main()
        cls.assert_called_once_with("0-mvp", auto_push=True, model="my-model")
        cls.return_value.run.assert_called_once()


# ---------------------------------------------------------------------------
# _check_blockers (= 이전 main() error/blocked 체크)
# ---------------------------------------------------------------------------

class TestCheckBlockers:
    def _make_executor_with_steps(self, tmp_project, steps):
        d = tmp_project / "phases" / "test-phase"
        d.mkdir(exist_ok=True)
        index = {"project": "T", "phase": "test", "steps": steps}
        (d / "index.json").write_text(json.dumps(index))

        with patch.object(ex, "ROOT", tmp_project):
            inst = ex.StepExecutor.__new__(ex.StepExecutor)
        inst._root = str(tmp_project)
        inst._phases_dir = tmp_project / "phases"
        inst._phase_dir = d
        inst._phase_dir_name = "test-phase"
        inst._index_file = d / "index.json"
        inst._top_index_file = tmp_project / "phases" / "index.json"
        inst._phase_name = "test"
        inst._total = len(steps)
        return inst

    def test_error_step_exits_1(self, tmp_project):
        steps = [
            {"step": 0, "name": "ok", "status": "completed"},
            {"step": 1, "name": "bad", "status": "error", "error_message": "fail"},
        ]
        inst = self._make_executor_with_steps(tmp_project, steps)
        with pytest.raises(SystemExit) as exc_info:
            inst._check_blockers()
        assert exc_info.value.code == 1

    def test_blocked_step_exits_2(self, tmp_project):
        steps = [
            {"step": 0, "name": "ok", "status": "completed"},
            {"step": 1, "name": "stuck", "status": "blocked", "blocked_reason": "API key"},
        ]
        inst = self._make_executor_with_steps(tmp_project, steps)
        with pytest.raises(SystemExit) as exc_info:
            inst._check_blockers()
        assert exc_info.value.code == 2

    @pytest.mark.parametrize("bad_status,exit_code", [("error", 1), ("blocked", 2)])
    def test_detects_failure_before_completed_or_pending_tail(self, tmp_project, bad_status, exit_code):
        steps = [
            {"step": 0, "name": "bad", "status": bad_status},
            {"step": 1, "name": "done", "status": "completed"},
            {"step": 2, "name": "later", "status": "pending"},
        ]
        inst = self._make_executor_with_steps(tmp_project, steps)
        with pytest.raises(SystemExit) as exc_info:
            inst._check_blockers()
        assert exc_info.value.code == exit_code


def test_finalize_rejects_pending_steps(executor):
    with patch.object(executor, "_run_git") as git:
        with pytest.raises(SystemExit) as exc_info:
            executor._finalize()
    assert exc_info.value.code == 1
    git.assert_not_called()
    assert "completed_at" not in executor._read_json(executor._index_file)
