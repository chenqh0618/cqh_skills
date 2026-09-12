import errno
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import tomllib
import unittest
from unittest.mock import patch


SKILL = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("task_tools", SKILL / "scripts/task_tools.py")
TASKS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(TASKS)


class WorkflowTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="loose-test-")
        self.addCleanup(self.temp.cleanup)
        # Exercise paths which broke sed-based substitution in earlier scaffolds.
        self.project = Path(self.temp.name) / "project space & # quote'"
        self.project.mkdir()

    def scaffold(self, ok=True):
        result = subprocess.run(["bash", str(SKILL / "scripts/scaffold.sh"), str(self.project)],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode == 0, ok, result.stdout + result.stderr)
        return result

    def command(self, *args, ok=True):
        result = subprocess.run([sys.executable, str(self.project / ".project/tasks.py"), *args],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode == 0, ok, result.stdout + result.stderr)
        return json.loads(result.stdout) if ok else result.stderr

    def new(self, side="analysis", name="exampleTask", upstream=()):
        result = self.command("new", side, name, "--agent", "codex", "--question", "测试输入与产物",
                              "--upstream", *upstream)
        return result["created"], Path(result["path"])

    def test_scaffold_preserves_existing_files_and_builds_both_adapters(self):
        (self.project / "data").mkdir()
        raw = self.project / "data/raw.bin"
        raw.write_bytes(b"original data\x00\xff")
        (self.project / ".gitignore").write_text("# user rule\ncustom.tmp\n")
        (self.project / ".claude/agents").mkdir(parents=True)
        unrelated = self.project / ".claude/agents/custom.md"
        unrelated.write_text("custom role")
        self.scaffold()
        self.assertEqual(raw.read_bytes(), b"original data\x00\xff")
        self.assertEqual(unrelated.read_text(), "custom role")
        self.assertTrue((self.project / ".gitignore").read_text().startswith("# user rule\ncustom.tmp\n"))
        self.assertIn(str(self.project), (self.project / "CLAUDE.md").read_text())
        for side in ("", "analysis", "explore", "mgmt", "_archived"):
            self.assertEqual((self.project / side / "AGENTS.md").resolve(),
                             self.project / side / "CLAUDE.md")
        for name in ("mgr", "analyst", "explorer", "reviewer"):
            role = tomllib.loads((self.project / ".codex/agents" / f"{name}.toml").read_text())
            self.assertEqual(role["name"], name)
            self.assertNotIn("model", role)
            claude = (self.project / ".claude/agents" / f"{name}.md").read_text()
            self.assertEqual(role["developer_instructions"], claude.split("---", 2)[2].strip())
        self.assertEqual(list((self.project / "analysis").glob("A*_*")), [])
        self.assertEqual(subprocess.run(["git", "-C", str(self.project), "rev-parse", "--verify", "HEAD"],
                                        capture_output=True).returncode, 128)

    def test_conflict_is_detected_before_changes(self):
        (self.project / "AGENTS.md").symlink_to("missing.md")
        self.scaffold(ok=False)
        self.assertEqual({x.name for x in self.project.iterdir()}, {"AGENTS.md"})

    def test_publication_failure_rolls_back_owned_files(self):
        (self.project / ".gitignore").write_text("original ignore\n")
        # Execute the shell's Python body with an injected filesystem failure.
        script = (SKILL / "scripts/scaffold.sh").read_text().split("<<'PY'\n", 1)[1].rsplit("\nPY", 1)[0]
        actual_rename = TASKS.os.rename

        def fail_role(source, destination):
            if str(destination).endswith(".claude/agents/mgr.md"):
                raise OSError(errno.ENOSPC, "injected publication failure")
            return actual_rename(source, destination)

        with patch.object(sys, "argv", ["-", str(SKILL / "scripts"), str(self.project)]), \
                patch("os.rename", side_effect=fail_role), self.assertRaises(SystemExit) as stopped:
            exec(compile(script, "scaffold-inline", "exec"), {"__name__": "__main__"})
        self.assertEqual(stopped.exception.code, 2)
        self.assertEqual({x.name for x in self.project.iterdir()}, {".gitignore"})
        self.assertEqual((self.project / ".gitignore").read_text(), "original ignore\n")
        self.scaffold()  # a normal retry succeeds

    def test_archive_restore_preserve_bytes_and_identity(self):
        self.scaffold()
        ident, path = self.new()
        self.command("start", ident, "--agent", "claude")
        self.command("finish", ident, "--status", "completed")
        (path / "scripts/replay.py").write_text(f"from pathlib import Path\nPath({str(path / 'results/replay.txt')!r}).write_text('replayed')\n")
        result = path / "results/original.bin"
        result.write_bytes(b"irreplaceable test output\x00")
        snapshots = {name: (path / name).read_bytes() for name in ("scripts/replay.py", "results/original.bin", "SUMMARY.md", "AS_RUN.md")}
        original_abstract = (path / "ABSTRACT.md").read_bytes()
        preview = self.command("archive", ident, "--reason", "用户明确弃用")
        self.assertTrue(path.exists())
        self.assertEqual((path / "ABSTRACT.md").read_bytes(), original_abstract)
        archive = Path(preview["destination"])
        self.command("archive", ident, "--reason", "用户明确弃用", "--apply", "--checked")
        self.assertFalse(path.exists())
        self.assertFalse(path.is_symlink())
        for name, content in snapshots.items():
            self.assertEqual((archive / name).read_bytes(), content)
        self.assertNotIn(ident + " |", (self.project / "TASKS.md").read_text())
        self.assertIn(ident + " |", (self.project / "_archived/INDEX.md").read_text())
        ident2, _ = self.new()
        self.assertEqual(ident2, "A02")
        self.command("start", ident, "--agent", "codex", ok=False)
        self.command("restore", ident)
        self.assertFalse(path.exists())
        self.command("restore", ident, "--apply")
        self.assertFalse(archive.exists())
        for name, content in snapshots.items():
            self.assertEqual((path / name).read_bytes(), content)
        subprocess.run([sys.executable, str(path / "scripts/replay.py")], check=True)
        self.assertEqual((path / "results/replay.txt").read_text(), "replayed")
        self.command("start", ident, "--agent", "codex")
        meta = TASKS.scan(self.project)[ident]["data"]
        self.assertEqual(meta["created_by"], "codex")
        self.assertEqual(meta["first_executed_by"], "claude")
        self.assertTrue(path.name.endswith("_codex"))

    def test_dependencies_and_running_status_block_archive(self):
        self.scaffold()
        ident, path = self.new()
        self.command("start", ident, "--agent", "codex")
        self.assertIn("known status", self.command("archive", ident, "--reason", "旧任务", ok=False))
        self.command("finish", ident, "--status", "completed")
        child, _ = self.new("explore", upstream=(ident,))
        self.assertIn("dependants", self.command("archive", ident, "--reason", "旧任务", ok=False))
        self.command("finish", child, "--status", "failed")
        self.assertIn("--checked", self.command("archive", ident, "--reason", "旧任务", "--apply", ok=False))
        self.command("archive", ident, "--reason", "旧任务", "--apply", "--checked")
        self.assertIn("Restore computational inputs", self.command("start", child, "--agent", "codex", ok=False))

    def test_failed_metadata_write_rolls_back_directory_without_another_write(self):
        self.scaffold()
        ident, path = self.new()
        units = TASKS.scan(self.project)
        before = (path / "ABSTRACT.md").read_bytes()
        args = type("Args", (), dict(command="archive", id=ident, reason="明确放弃未执行任务",
                                     replacement=None, apply=True, checked=True))()
        with patch.object(TASKS, "atomic_write", side_effect=OSError(errno.ENOSPC, "disk full")) as writer:
            with self.assertRaises(OSError):
                TASKS.transition(self.project, units, args)
            self.assertEqual(writer.call_count, 1)
        self.assertTrue(path.exists())
        self.assertFalse((self.project / "_archived/analysis" / path.name).exists())
        self.assertEqual((path / "ABSTRACT.md").read_bytes(), before)
        self.assertEqual(TASKS.scan(self.project)[ident]["data"]["status"], "planned")

    def test_legacy_metadata_and_duplicate_ids_fail_explicitly(self):
        self.scaffold()
        legacy = self.project / "analysis/A09_legacy_0801"
        legacy.mkdir()
        (legacy / "SUMMARY.md").write_text("old summary")
        self.command("index")
        self.assertIn("legacy", (self.project / "TASKS.md").read_text())
        ident, path = self.new()
        self.assertEqual(ident, "A10")
        self.command("archive", "A09", "--reason", "旧任务", ok=False)
        before = (self.project / "TASKS.md").read_bytes()
        abstract = path / "ABSTRACT.md"
        abstract.write_text(abstract.read_text().replace('id = "A10"', 'id = "A11"'))
        self.command("index", ok=False)
        self.assertEqual((self.project / "TASKS.md").read_bytes(), before)
        abstract.write_text(abstract.read_text().replace('id = "A11"', 'id = "A10"'))
        (self.project / "analysis/A010_duplicate_0901").mkdir()
        self.assertIn("Duplicate task ID", self.command("index", ok=False))

    def test_restore_conflicts_and_unmanaged_index_are_not_overwritten(self):
        self.scaffold()
        ident, path = self.new()
        self.command("archive", ident, "--reason", "放弃未运行任务", "--apply", "--checked")
        path.symlink_to("missing-output")
        self.command("restore", ident, "--apply", ok=False)
        self.assertTrue(path.is_symlink())
        path.unlink()
        (self.project / "TASKS.md").write_text("user maintained index")
        self.command("restore", ident, "--apply", ok=False)
        self.assertFalse(path.exists())
        self.assertEqual((self.project / "TASKS.md").read_text(), "user maintained index")

    def test_parallel_creation_does_not_reuse_numbers(self):
        self.scaffold()
        processes = [subprocess.Popen([sys.executable, str(self.project / ".project/tasks.py"),
                                      "new", "analysis", "parallelTask", "--agent", "codex", "--question", "并行任务"],
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) for _ in range(4)]
        created = []
        for process in processes:
            out, err = process.communicate(timeout=15)
            self.assertEqual(process.returncode, 0, out + err)
            created.append(json.loads(out)["created"])
        self.assertEqual(set(created), {"A01", "A02", "A03", "A04"})


if __name__ == "__main__":
    unittest.main()
