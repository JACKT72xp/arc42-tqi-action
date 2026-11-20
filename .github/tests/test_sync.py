"""Exercise export provenance, tamper detection, deletions and unsafe source entries."""
from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/sync_upstream.py"


class SyncTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.source = self.root / "source"
        self.destination = self.root / "distribution"
        for repository in (self.source, self.destination):
            repository.mkdir()
            self.git(repository, "init", "-q")
            self.git(repository, "config", "user.email", "test@example.invalid")
            self.git(repository, "config", "user.name", "Test")
        self.subtree = self.source / "actions/arc42-tqi"
        (self.subtree / "src/arc42_tqi").mkdir(parents=True)
        for name in ("action.yml", "Dockerfile", "LICENSE", "src/arc42_tqi/cli.py"):
            (self.subtree / name).write_text("fixture\n")
        self.script = self.destination / ".github/scripts/sync_upstream.py"
        self.script.parent.mkdir(parents=True)
        shutil.copyfile(SCRIPT, self.script)
        self.revision = self.commit()

    def git(self, repository: Path, *args: str) -> str:
        return subprocess.check_output(["git", "-C", str(repository), *args], text=True).strip()

    def commit(self) -> str:
        self.git(self.source, "add", "--all")
        self.git(self.source, "commit", "-qm", "Fixture")
        return self.git(self.source, "rev-parse", "HEAD")

    def sync(self, *args: str) -> subprocess.CompletedProcess[str]:
        import sys
        return subprocess.run([sys.executable, str(self.script), "--source", str(self.source), *args],
                              capture_output=True, text=True, check=False)

    def test_repeatable_export_and_independent_tamper_check(self) -> None:
        self.assertEqual(self.sync("--ref", self.revision).returncode, 0)
        manifest = self.destination / "UPSTREAM.json"
        before = manifest.read_bytes()
        self.assertEqual(self.sync("--check").returncode, 0)
        self.assertEqual(self.sync("--ref", self.revision).returncode, 0)
        self.assertEqual(before, manifest.read_bytes())
        (self.destination / "action.yml").write_text("tampered")
        value = json.loads(manifest.read_text())
        value["files"]["action.yml"] = "forged"
        manifest.write_text(json.dumps(value))
        self.assertNotEqual(self.sync("--check").returncode, 0)

    def test_deletion_and_distribution_file_preservation(self) -> None:
        extra = self.subtree / "removed.txt"
        extra.write_text("remove me")
        first = self.commit()
        self.assertEqual(self.sync("--ref", first).returncode, 0)
        owned = self.destination / "DISTRIBUTION.md"
        owned.write_text("retain me")
        extra.unlink()
        second = self.commit()
        self.assertEqual(self.sync("--ref", second).returncode, 0)
        self.assertFalse((self.destination / "removed.txt").exists())
        self.assertEqual(owned.read_text(), "retain me")

    def test_reject_source_and_destination_symlinks(self) -> None:
        (self.subtree / "link").symlink_to("LICENSE")
        revision = self.commit()
        self.assertNotEqual(self.sync("--ref", revision).returncode, 0)
        (self.destination / "LICENSE").symlink_to(self.subtree / "LICENSE")
        self.assertNotEqual(self.sync("--ref", self.revision).returncode, 0)

    def test_distribution_documentation_and_reserved_paths(self) -> None:
        (self.subtree / "README.md").write_text(
            "# Action\nReplace `COMMIT_SHA` below with a commit.\n```yaml\n"
            "uses: JACKT72xp/architecture-actions-public/actions/arc42-tqi@COMMIT_SHA\n```\n"
            "## Repository layout\nOld monorepo layout\n"
        )
        (self.subtree / "CONTRIBUTING.md").write_text("upstream guide")
        revision = self.commit()
        self.assertEqual(self.sync("--ref", revision).returncode, 0)
        readme = (self.destination / "README.md").read_text()
        self.assertIn("JACKT72xp/arc42-tqi-action@COMMIT_SHA", readme)
        self.assertNotIn("Old monorepo layout", readme)
        self.assertIn("Marketplace distribution", readme)
        (self.subtree / "UPSTREAM.json").write_text("{}")
        self.assertNotEqual(self.sync("--ref", self.commit()).returncode, 0)

    def test_reject_additional_tracked_code(self) -> None:
        self.assertEqual(self.sync("--ref", self.revision).returncode, 0)
        (self.destination / "extra.py").write_text("unexpected = True")
        self.git(self.destination, "add", "extra.py")
        self.assertNotEqual(self.sync("--check").returncode, 0)


if __name__ == "__main__":
    unittest.main()
