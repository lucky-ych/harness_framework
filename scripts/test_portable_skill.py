"""복사·설치된 harness 스킬이 대상 프로젝트만 변경하는지 검증한다. 실제 Codex는 호출하지 않는다."""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
SKILL_SRC = REPO / "skills" / "harness"
WRAPPER = REPO / "scripts" / "execute.py"

FAKE_CODEX = """#!{python}
import json, os, sys
prompt = sys.stdin.read()
with open(os.environ["FAKE_CODEX_LOG"], "a") as f:
    f.write(json.dumps({{"argv": sys.argv[1:], "cwd": os.getcwd(), "prompt": prompt}}) + "\\n")
cwd = sys.argv[sys.argv.index("--cd") + 1]
p = os.path.join(cwd, "phases", "0-mvp", "index.json")
if os.environ.get("FAKE_SWAP"):
    os.remove(p)
    os.symlink(os.environ["FAKE_SWAP"], p)
    sys.exit(0)
idx = json.load(open(p))
for s in idx["steps"]:
    if s["status"] == "pending":
        s["status"] = "completed"
        s["summary"] = "done " + s["name"]
        open(os.path.join(cwd, s["name"] + ".txt"), "w").write("x")
        break
json.dump(idx, open(p, "w"))
print(json.dumps({{"type": "done"}}))
"""

GIT_ENV = {
    "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.com",
    "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.com",
}


def git(cwd, *args):
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True,
                          env={**os.environ, **GIT_ENV})


@pytest.fixture
def skill(tmp_path):
    """스킬 폴더만 저장소 밖으로 복사한다."""
    dest = tmp_path / "installed" / "harness"
    shutil.copytree(SKILL_SRC, dest, ignore=shutil.ignore_patterns("__pycache__"))
    return dest


@pytest.fixture
def fake_bin(tmp_path):
    b = tmp_path / "bin"
    b.mkdir()
    exe = b / "codex"
    exe.write_text(FAKE_CODEX.format(python=sys.executable))
    exe.chmod(0o755)
    return b


@pytest.fixture
def target(tmp_path):
    t = tmp_path / "target"
    t.mkdir()
    assert git(t, "init").returncode == 0
    (t / "AGENTS.md").write_text("# Target rules\n")
    d = t / "phases" / "0-mvp"
    d.mkdir(parents=True)
    (d / "index.json").write_text(json.dumps({
        "project": "Target", "phase": "mvp",
        "steps": [{"step": 0, "name": "alpha", "status": "pending"}]}))
    (d / "step0.md").write_text("# Step 0\nDo alpha.")
    (t / ".gitignore").write_text("phases/**/step*-output.json\n")
    git(t, "add", "-A")
    assert git(t, "commit", "-m", "init").returncode == 0
    return t


@pytest.fixture
def env(tmp_path, fake_bin):
    return {**os.environ, **GIT_ENV, "PATH": f"{fake_bin}{os.pathsep}{os.environ['PATH']}",
            "FAKE_CODEX_LOG": str(tmp_path / "codex.log")}


def run_py(script, args, cwd, env):
    return subprocess.run([sys.executable, str(script), *args], cwd=cwd,
                          capture_output=True, text=True, env=env)


def calls(tmp_path):
    log = tmp_path / "codex.log"
    return [json.loads(l) for l in log.read_text().splitlines()] if log.exists() else []


def snapshot(path):
    return sorted(str(p.relative_to(path)) for p in path.rglob("*") if ".git" not in p.parts)


class TestRelocatedExecutor:
    def test_explicit_root_from_unrelated_cwd(self, skill, target, env, tmp_path):
        decoy = tmp_path / "decoy"
        decoy.mkdir()
        before_skill = snapshot(skill)

        r = run_py(skill / "scripts" / "execute.py", ["0-mvp", "--project-root", str(target)], decoy, env)

        assert r.returncode == 0, r.stdout + r.stderr
        [call] = calls(tmp_path)
        resolved = str(target.resolve())
        assert call["cwd"] == resolved
        assert call["argv"][call["argv"].index("--cd") + 1] == resolved
        assert "Target rules" in call["prompt"]
        assert (target / "alpha.txt").exists()
        assert git(target, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip() == "feat-mvp"
        subjects = git(target, "log", "--format=%s").stdout.splitlines()
        assert any(s.startswith("feat(mvp): step 0") for s in subjects)
        assert any(s.startswith("chore(mvp): step 0 output") for s in subjects)
        assert snapshot(decoy) == []
        assert snapshot(skill) == before_skill
        assert (target / "phases" / "0-mvp" / "step0-output.json").exists()

    def test_default_root_is_cwd(self, skill, target, env, tmp_path):
        r = run_py(skill / "scripts" / "execute.py", ["0-mvp"], target, env)
        assert r.returncode == 0, r.stdout + r.stderr
        assert calls(tmp_path)[0]["cwd"] == str(target.resolve())
        assert git(target, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip() == "feat-mvp"

    def test_subdirectory_is_not_a_git_root(self, skill, target, env, tmp_path):
        sub = target / "pkg"
        (sub / "phases" / "0-mvp").mkdir(parents=True)
        (sub / "phases" / "0-mvp" / "index.json").write_text(
            json.dumps({"project": "p", "phase": "mvp", "steps": [{"step": 0, "name": "a", "status": "pending"}]}))
        head = git(target, "rev-parse", "HEAD").stdout

        r = run_py(skill / "scripts" / "execute.py", ["0-mvp", "--project-root", str(sub)], tmp_path, env)

        assert r.returncode == 1
        assert "Git working-tree root" in r.stdout
        assert calls(tmp_path) == []
        assert git(target, "rev-parse", "HEAD").stdout == head
        assert git(target, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip() != "feat-mvp"

    def test_non_git_directory_rejected(self, skill, env, tmp_path):
        plain = tmp_path / "plain"
        (plain / "phases" / "0-mvp").mkdir(parents=True)
        (plain / "phases" / "0-mvp" / "index.json").write_text(
            json.dumps({"project": "p", "phase": "mvp", "steps": [{"step": 0, "name": "a", "status": "pending"}]}))
        r = run_py(skill / "scripts" / "execute.py", ["0-mvp", "--project-root", str(plain)], tmp_path, env)
        assert r.returncode == 1
        assert calls(tmp_path) == []

    @pytest.mark.parametrize("name", ["../outside", "/tmp/abs", "a/b", "..", ".", ""])
    def test_bad_phase_names_rejected(self, skill, target, env, tmp_path, name):
        r = run_py(skill / "scripts" / "execute.py", [name, "--project-root", str(target)], tmp_path, env)
        assert r.returncode == 1
        assert "invalid phase" in r.stdout
        assert calls(tmp_path) == []

    def test_symlinked_phase_dir_outside_target_rejected(self, skill, target, env, tmp_path):
        outside = tmp_path / "outside"
        outside.mkdir()
        (outside / "index.json").write_text(
            json.dumps({"project": "p", "phase": "mvp", "steps": [{"step": 0, "name": "a", "status": "pending"}]}))
        (target / "phases" / "linked").symlink_to(outside, target_is_directory=True)

        r = run_py(skill / "scripts" / "execute.py", ["linked", "--project-root", str(target)], tmp_path, env)

        assert r.returncode == 1
        assert "symlink" in r.stdout
        assert calls(tmp_path) == []
        assert snapshot(outside) == ["index.json"]

    def test_symlinked_output_file_cannot_redirect_log(self, skill, target, env, tmp_path):
        victim = tmp_path / "victim.json"
        victim.write_text("keep")
        (target / "phases" / "0-mvp" / "step0-output.json").symlink_to(victim)

        r = run_py(skill / "scripts" / "execute.py", ["0-mvp", "--project-root", str(target)], tmp_path, env)

        assert r.returncode == 1
        assert victim.read_text() == "keep"


INDEX_JSON = json.dumps({"project": "V", "phase": "mvp",
                         "steps": [{"step": 0, "name": "alpha", "status": "pending"}]})


class TestBoundaryAtPointOfUse:
    def test_checkout_that_redirects_index_fails_closed(self, skill, target, env, tmp_path):
        victim = tmp_path / "victim.json"
        victim.write_text(INDEX_JSON)
        base = git(target, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
        git(target, "checkout", "-b", "feat-mvp")
        idx = target / "phases" / "0-mvp" / "index.json"
        idx.unlink()
        idx.symlink_to(victim)
        git(target, "add", "-A")
        assert git(target, "commit", "-m", "alias").returncode == 0
        git(target, "checkout", base)

        r = run_py(skill / "scripts" / "execute.py", ["0-mvp", "--project-root", str(target)], tmp_path, env)

        assert r.returncode == 1, r.stdout
        assert victim.read_text() == INDEX_JSON
        assert calls(tmp_path) == []

    def test_child_redirecting_index_stops_run_and_push(self, skill, target, env, tmp_path):
        victim = tmp_path / "victim.json"
        victim.write_text(INDEX_JSON)
        origin = tmp_path / "origin.git"
        subprocess.run(["git", "init", "--bare", str(origin)], capture_output=True, check=True)
        git(target, "remote", "add", "origin", str(origin))

        r = run_py(skill / "scripts" / "execute.py", ["0-mvp", "--project-root", str(target), "--push"],
                   tmp_path, {**env, "FAKE_SWAP": str(victim)})

        assert r.returncode == 1, r.stdout
        assert victim.read_text() == INDEX_JSON
        assert len(calls(tmp_path)) == 1
        assert git(origin, "branch", "--list").stdout.strip() == ""

    def test_child_redirecting_top_index_stops_run(self, skill, target, env, tmp_path):
        victim = tmp_path / "top-victim.json"
        victim.write_text('{"phases": [{"dir": "0-mvp", "status": "pending"}]}')
        top = target / "phases" / "index.json"
        top.write_text(victim.read_text())
        git(target, "add", "-A")
        git(target, "commit", "-m", "top")
        swap = ("p = os.path.join(sys.argv[sys.argv.index('--cd') + 1], 'phases', 'index.json')\n"
                "os.remove(p)\nos.symlink(os.environ['TOP_VICTIM'], p)\n")
        fake = tmp_path / "bin" / "codex"
        src = fake.read_text().replace("cwd = sys.argv", swap + "cwd = sys.argv", 1)
        fake.write_text(src)

        r = run_py(skill / "scripts" / "execute.py", ["0-mvp", "--project-root", str(target)],
                   tmp_path, {**env, "TOP_VICTIM": str(victim)})

        assert r.returncode == 1, r.stdout
        assert victim.read_text() == '{"phases": [{"dir": "0-mvp", "status": "pending"}]}'


class TestRootWrapper:
    def test_wrapper_delegates_with_project_root(self, target, env, tmp_path):
        r = run_py(WRAPPER, ["0-mvp", "--project-root", str(target)], tmp_path, env)
        assert r.returncode == 0, r.stdout + r.stderr
        assert calls(tmp_path)[0]["cwd"] == str(target.resolve())

    def test_wrapper_defaults_to_cwd_not_repo(self, target, env, tmp_path):
        r = run_py(WRAPPER, ["0-mvp"], target, env)
        assert r.returncode == 0, r.stdout + r.stderr
        assert (target / "alpha.txt").exists()
        assert not (REPO / "alpha.txt").exists()

    def test_wrapper_without_args_is_usage_error(self, env, tmp_path):
        assert run_py(WRAPPER, [], tmp_path, env).returncode == 2


class TestInitProject:
    def init(self, skill, root, tmp_path, env):
        return run_py(skill / "scripts" / "init_project.py", ["--project-root", str(root)], tmp_path, env)

    def test_creates_templates_and_ignore_without_git_side_effects(self, skill, env, tmp_path):
        root = tmp_path / "fresh"
        root.mkdir()
        r = self.init(skill, root, tmp_path, env)
        assert r.returncode == 0, r.stderr
        for rel in ["AGENTS.md", "docs/PRD.md", "docs/ARCHITECTURE.md", "docs/ADR.md", "phases/index.json"]:
            assert (root / rel).is_file()
        assert json.loads((root / "phases" / "index.json").read_text()) == {"phases": []}
        ignore = (root / ".gitignore").read_text().splitlines()
        assert "phases/**/step*-output.json" in ignore and "phases/**/phase*-output.json" in ignore
        assert not (root / ".git").exists()
        assert sorted(p.name for p in (root / "phases").iterdir()) == ["index.json"]

    def test_preserves_existing_and_is_idempotent(self, skill, env, tmp_path):
        root = tmp_path / "proj"
        (root / "docs").mkdir(parents=True)
        (root / "AGENTS.md").write_text("custom rules")
        (root / "docs" / "PRD.md").write_text("my prd")
        (root / ".gitignore").write_text("node_modules")  # 개행 없음

        assert self.init(skill, root, tmp_path, env).returncode == 0
        first = {p: (root / p).read_text() for p in ["AGENTS.md", "docs/PRD.md", ".gitignore", "docs/ADR.md"]}
        assert first["AGENTS.md"] == "custom rules" and first["docs/PRD.md"] == "my prd"
        assert first[".gitignore"].startswith("node_modules\n")

        r = self.init(skill, root, tmp_path, env)
        assert r.returncode == 0
        assert "created" not in r.stdout and "unchanged" in r.stdout
        assert {p: (root / p).read_text() for p in first} == first

    def test_negated_ignore_rule_is_overridden_and_stable(self, skill, env, tmp_path):
        root = tmp_path / "neg"
        root.mkdir()
        git(root, "init")
        old = "phases/**/step*-output.json\n!phases/**/step*-output.json\n"
        (root / ".gitignore").write_text(old)

        assert self.init(skill, root, tmp_path, env).returncode == 0
        text = (root / ".gitignore").read_text()
        assert text.startswith(old)
        for name in ["step0-output.json", "phase0-output.json"]:
            rel = "phases/0-mvp/" + name
            assert git(root, "check-ignore", "--no-index", rel).returncode == 0
        assert self.init(skill, root, tmp_path, env).returncode == 0
        assert (root / ".gitignore").read_text() == text

    def test_default_root_is_cwd(self, skill, env, tmp_path):
        root = tmp_path / "cwdproj"
        root.mkdir()
        r = run_py(skill / "scripts" / "init_project.py", [], root, env)
        assert r.returncode == 0
        assert (root / "AGENTS.md").is_file()
        assert not (tmp_path / "AGENTS.md").exists()

    def test_symlinked_destination_rejected(self, skill, env, tmp_path):
        root = tmp_path / "proj"
        root.mkdir()
        outside = tmp_path / "outside"
        outside.mkdir()
        (root / "docs").symlink_to(outside, target_is_directory=True)
        r = self.init(skill, root, tmp_path, env)
        assert r.returncode == 1
        assert "symlink" in r.stderr
        assert list(outside.iterdir()) == []
        assert not (root / "AGENTS.md").exists()

    def test_symlinked_file_and_gitignore_rejected(self, skill, env, tmp_path):
        root = tmp_path / "proj"
        root.mkdir()
        victim = tmp_path / "victim"
        victim.write_text("keep")
        (root / ".gitignore").symlink_to(victim)
        r = self.init(skill, root, tmp_path, env)
        assert r.returncode == 1
        assert victim.read_text() == "keep"

    def test_missing_root_rejected(self, skill, env, tmp_path):
        r = self.init(skill, tmp_path / "nope", tmp_path, env)
        assert r.returncode == 1


def _head(t):
    return git(t, "rev-parse", "HEAD").stdout.strip()


class TestNoCommitAfterRedirect:
    def _origin(self, target, tmp_path):
        origin = tmp_path / "origin.git"
        subprocess.run(["git", "init", "--bare", str(origin)], capture_output=True, check=True)
        git(target, "remote", "add", "origin", str(origin))
        return origin

    def _swap_fake(self, tmp_path, dangling):
        swap = ("p = os.path.join(sys.argv[sys.argv.index('--cd') + 1], 'phases', 'index.json')\n"
                "if os.path.lexists(p):\n    os.remove(p)\n"
                "os.symlink(os.environ['TOP_VICTIM'], p)\n")
        fake = tmp_path / "bin" / "codex"
        fake.write_text(fake.read_text().replace("cwd = sys.argv", swap + "cwd = sys.argv", 1))

    @pytest.mark.parametrize("dangling", [False, True])
    def test_top_index_swap_creates_no_commit_or_push(self, skill, target, env, tmp_path, dangling):
        victim = tmp_path / "top-victim.json"
        if not dangling:
            victim.write_text('{"phases": []}')
        origin = self._origin(target, tmp_path)
        before = _head(target)
        self._swap_fake(tmp_path, dangling)
        r = run_py(skill / "scripts" / "execute.py", ["0-mvp", "--project-root", str(target), "--push"],
                   tmp_path, {**env, "TOP_VICTIM": str(victim)})
        assert r.returncode == 1, r.stdout
        assert _head(target) == before or git(target, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip() == "feat-mvp"
        assert git(target, "rev-list", "--count", f"{before}..HEAD").stdout.strip() == "0"
        assert git(origin, "branch", "--list").stdout.strip() == ""
        assert victim.exists() == (not dangling)
        if not dangling:
            assert victim.read_text() == '{"phases": []}'

    def test_phase_index_swap_creates_no_commit(self, skill, target, env, tmp_path):
        victim = tmp_path / "victim.json"
        victim.write_text(INDEX_JSON)
        origin = self._origin(target, tmp_path)
        before = _head(target)
        r = run_py(skill / "scripts" / "execute.py", ["0-mvp", "--project-root", str(target), "--push"],
                   tmp_path, {**env, "FAKE_SWAP": str(victim)})
        assert r.returncode == 1
        assert git(target, "rev-list", "--count", f"{before}..HEAD").stdout.strip() == "0"
        assert git(origin, "branch", "--list").stdout.strip() == ""
        assert victim.read_text() == INDEX_JSON

    def test_malformed_step_id_cannot_read_or_write_outside(self, skill, target, env, tmp_path):
        (tmp_path / "step..md").write_text("EXTERNAL STEP")
        idx = target / "phases" / "0-mvp" / "index.json"
        idx.write_text(json.dumps({"project": "T", "phase": "mvp",
                                   "steps": [{"step": "../../..", "name": "evil", "status": "pending"}]}))
        before = snapshot(tmp_path)
        r = run_py(skill / "scripts" / "execute.py", ["0-mvp", "--project-root", str(target)], tmp_path, env)
        assert r.returncode == 1
        assert calls(tmp_path) == []
        assert snapshot(tmp_path) == before
