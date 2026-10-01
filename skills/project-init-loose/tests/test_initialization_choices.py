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
                self.assertIn(project_class, background)
                self.assertIn(f"`{mode}`", resources)
                self.assertIn("scRNA_v2", resources)
                self.assertIn("planned", resources)
                self.assertFalse((project / "envs").exists())
                self.assertEqual(list((project / "analysis").glob("A*_*")), [])

    def test_other_domain_has_no_automatic_scrna_reference(self):
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp)
            result = self.scaffold(project, "--domain", "scrna_atac_custom", "--project-class", "complex",
                                   "--env-mode", "project", "--reason", "独立多组学项目")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertNotIn("scRNA_v2", (project / "mgmt/RESOURCES.md").read_text())

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
            resources = (project / "mgmt/RESOURCES.md").read_text()
            self.assertIn(str(ref), resources)
            self.assertIn("9.1", resources)
            self.assertIn("`shared`", resources)
