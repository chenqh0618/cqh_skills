import re
import subprocess
import tempfile
import unittest
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]


class InitializationChoicesTest(unittest.TestCase):
    def scaffold(self, project, *args):
        return subprocess.run(["bash", str(SKILL / "scripts/scaffold.sh"), str(project), *args],
                              capture_output=True, text=True)

    def test_scrna_choices_are_recorded_without_installing(self):
        for project_class, mode in (("lightweight", "shared"), ("complex", "project")):
            with self.subTest(project_class=project_class), tempfile.TemporaryDirectory() as temp:
                project = Path(temp)
                result = self.scaffold(project, "--domain", "scrna", "--project-class", project_class,
                                       "--env-mode", mode, "--reason", "任务要求独立记录")
                self.assertEqual(result.returncode, 0, result.stderr)
                background = (project / "mgmt/PROJECT.md").read_text()
                resources = (project / "mgmt/RESOURCES.md").read_text()
                dependencies = (project / ".project/DEPENDENCIES.md").read_text()
                self.assertIn(project_class, background)
                self.assertIn(f"`{mode}`", dependencies)
                self.assertIn("scRNA_v2", dependencies)
                self.assertIn("planned", dependencies)
                self.assertNotIn("scRNA_v2", resources)
                self.assertNotIn("DEPENDENCIES.md", resources)
                self.assertNotIn(f"`{mode}`", resources)
                self.assertFalse((project / "envs").exists())
                self.assertEqual(list((project / "analysis").glob("A*_*")), [])

    def test_other_domain_has_no_automatic_scrna_reference(self):
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp)
            result = self.scaffold(project, "--domain", "scrna_atac_custom", "--project-class", "complex",
                                   "--env-mode", "project", "--reason", "独立多组学项目")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertNotIn("scRNA_v2", (project / "mgmt/RESOURCES.md").read_text())
            self.assertNotIn("scRNA_v2", (project / ".project/DEPENDENCIES.md").read_text())

    def test_incomplete_choices_fail_before_any_writes(self):
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp)
            result = self.scaffold(project, "--domain", "scrna")
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(list(project.iterdir()), [])

    def test_explicit_reference_and_user_choice_are_preserved(self):
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp) / "project"; project.mkdir()
            ref = Path(temp) / "custom ref"; ref.mkdir()
            (ref / "VERSION").write_text("9.1\n")
            result = self.scaffold(project, "--domain", "scrna", "--project-class", "complex",
                                   "--env-mode", "shared", "--reason", "用户明确选用固定共享环境",
                                   "--reference-root", str(ref))
            self.assertEqual(result.returncode, 0, result.stderr)
            dependencies = (project / ".project/DEPENDENCIES.md").read_text()
            self.assertIn(str(ref), dependencies)
            self.assertIn("9.1", dependencies)
            self.assertIn("`shared`", dependencies)
            self.assertNotIn(str(ref), (project / "mgmt/RESOURCES.md").read_text())

    def test_unclassified_skeleton_has_dependencies_without_fabricated_choices(self):
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp)
            result = self.scaffold(project)
            self.assertEqual(result.returncode, 0, result.stderr)
            dependencies = (project / ".project/DEPENDENCIES.md").read_text()
            self.assertNotIn("默认环境方式", dependencies)
            self.assertNotIn("scRNA_v2", dependencies)
            self.assertFalse((project / "envs").exists())
            self.assertFalse((project / ".project/environments/USAGE.md").exists())
            self.assertFalse((project / "resources_ref").exists())

    def test_reference_files_and_links_are_ignored_but_metadata_is_trackable(self):
        for existing_ignore in (False, True):
            with self.subTest(existing_ignore=existing_ignore), tempfile.TemporaryDirectory() as temp:
                project = Path(temp) / "project"
                project.mkdir()
                if existing_ignore:
                    (project / ".gitignore").write_text("# user rule\ncustom.tmp\n")
                result = self.scaffold(project)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertFalse((project / "resources_ref").exists())
                reference = project / "resources_ref/scenic/test.feather"
                reference.parent.mkdir(parents=True)
                reference.write_bytes(b"reference fixture")
                shared = Path(temp) / "shared-index"
                shared.mkdir()
                (shared / "source.txt").write_text("unchanged")
                alias = project / "resources_ref/genome/custom-index"
                alias.parent.mkdir()
                alias.symlink_to(shared, target_is_directory=True)
                metadata = project / ".project/reference-manifest.json"
                metadata.write_text("{}\n")
                for path, expected in ((reference, 0), (alias, 0), (metadata, 1)):
                    check = subprocess.run(["git", "check-ignore", "--quiet", str(path)],
                                           cwd=project, capture_output=True, text=True)
                    self.assertEqual(check.returncode, expected, check.stderr)
                self.assertEqual((shared / "source.txt").read_text(), "unchanged")
                if existing_ignore:
                    self.assertTrue((project / ".gitignore").read_text().startswith("# user rule\ncustom.tmp\n"))

    def test_generated_dependency_entry_links_resolve(self):
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp)
            result = self.scaffold(project)
            self.assertEqual(result.returncode, 0, result.stderr)
            dependencies = project / ".project/DEPENDENCIES.md"
            for name in ("CLAUDE.md", "analysis/CLAUDE.md", "explore/CLAUDE.md", ".project/WORKFLOW.md"):
                source = project / name
                targets = re.findall(r'\[[^\]]+\]\(([^)]+)\)', source.read_text())
                dependency_entries = [target for target in targets if "DEPENDENCIES.md" in target]
                self.assertTrue(dependency_entries, name)
                for target in dependency_entries:
                    self.assertEqual((source.parent / target).resolve(), dependencies.resolve())

            targets = re.findall(r'\[[^\]]+\]\(([^)]+)\)', dependencies.read_text())
            workflow_entries = [target for target in targets if "WORKFLOW.md" in target]
            self.assertTrue(workflow_entries)
            for target in workflow_entries:
                self.assertEqual((dependencies.parent / target.split("#", 1)[0]).resolve(),
                                 (project / ".project/WORKFLOW.md").resolve())
