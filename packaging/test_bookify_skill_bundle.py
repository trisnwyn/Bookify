"""Safety and determinism tests for the Bookify skill bundler (stdlib only).

Run with: python -m unittest packaging/test_bookify_skill_bundle.py
"""

from __future__ import annotations

import gzip
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import bookify_skill_bundle as bundle


class BundleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._temp = tempfile.TemporaryDirectory(prefix="bookify-bundle-tests-")
        cls.temp = Path(cls._temp.name)
        cls.archive = cls.temp / "bookify-skill.tar.gz"
        cls.pack = bundle.pack(cls.archive, check_determinism=True)

    @classmethod
    def tearDownClass(cls) -> None:
        cls._temp.cleanup()

    def test_deterministic_archive(self) -> None:
        self.assertTrue(self.pack["determinism"]["identical"])
        self.assertEqual(
            self.pack["determinism"]["secondSha256"], self.pack["archiveSha256"]
        )
        self.assertEqual(self.pack["archiveBytes"], self.archive.stat().st_size)

    def test_manifest_covers_every_member(self) -> None:
        with tarfile.open(self.archive, "r:gz") as archive:
            members = archive.getmembers()
            manifest = json.loads(
                archive.extractfile("bookify/MANIFEST.json").read().decode()
            )
        names = {member.name for member in members}
        expected = {f"bookify/{entry['path']}" for entry in manifest["files"]}
        expected.add("bookify/MANIFEST.json")
        self.assertEqual(names, expected)
        self.assertEqual(manifest["fileCount"], len(manifest["files"]))
        self.assertEqual(
            manifest["payloadBytes"], sum(entry["size"] for entry in manifest["files"])
        )
        executable = [entry for entry in manifest["files"] if entry["path"].endswith("/typst")]
        self.assertEqual(len(executable), 1)
        self.assertEqual(executable[0]["mode"], "0755")
        for probe in ("probe/probe.sh", "probe/diagram.sh", "probe/chart.sh"):
            entry = next(item for item in manifest["files"] if item["path"] == f"engine/{probe}")
            self.assertEqual(entry["mode"], "0755")

    def test_no_caches_private_paths_or_absolute_original_root(self) -> None:
        with tarfile.open(self.archive, "r:gz") as archive:
            names = [member.name for member in archive.getmembers()]
            for name in names:
                self.assertNotIn("__pycache__", name)
                self.assertFalse(name.endswith(".pyc"))
                self.assertNotIn("/.venv/", name)
                self.assertNotIn("/.cache/", name)
                self.assertNotIn("/build/", name)
                self.assertNotIn("/.pytest_cache/", name)
                self.assertFalse(name.startswith("/"))
            for member in archive.getmembers():
                if not member.isfile():
                    continue
                handle = archive.extractfile(member)
                self.assertIsNotNone(handle)
                data = handle.read()
                self.assertNotIn(str(bundle.ROOT).encode(), data, member.name)
                self.assertNotIn(b"trial deck", data.lower(), member.name)

    def test_archive_has_no_symlinks(self) -> None:
        with tarfile.open(self.archive, "r:gz") as archive:
            for member in archive.getmembers():
                self.assertTrue(member.isfile() or member.isdir(), member.name)
                self.assertFalse(member.issym() or member.islnk(), member.name)

    def test_extract_and_verify(self) -> None:
        into = self.temp / "extract"
        result = bundle.extract(self.archive, into)
        self.assertTrue(result["ok"])
        self.assertTrue((into / "bookify" / "SKILL.md").is_file())
        self.assertTrue((into / "bookify" / "engine" / "pyproject.toml").is_file())
        self.assertEqual(
            bundle.verify_install(into / "bookify")["fileCount"], result["fileCount"]
        )

    def test_install_is_no_clobber_and_atomic(self) -> None:
        target = self.temp / "installed" / "bookify"
        first = bundle.install(self.archive, target)
        self.assertTrue(first["ok"])
        marker = target / "SKILL.md"
        digest = hashlib.sha256(marker.read_bytes()).hexdigest()
        with self.assertRaises(bundle.BundleError):
            bundle.install(self.archive, target)
        self.assertEqual(hashlib.sha256(marker.read_bytes()).hexdigest(), digest)

    def test_install_refuses_broken_symlink_before_resolving(self) -> None:
        parent = self.temp / "broken-symlink"
        parent.mkdir()
        target = parent / "bookify"
        missing = self.temp / "missing-target"
        target.symlink_to(missing)
        with self.assertRaises(bundle.BundleError):
            bundle.install(self.archive, target)
        self.assertTrue(target.is_symlink())
        self.assertEqual([entry.name for entry in parent.iterdir()], ["bookify"])
        self.assertFalse(missing.exists())

    def test_install_cli_reports_errors_as_json_without_traceback(self) -> None:
        parent = self.temp / "cli-broken"
        parent.mkdir()
        target = parent / "bookify"
        target.symlink_to(self.temp / "missing-cli-target")
        process = subprocess.run(
            [
                sys.executable,
                str(Path(bundle.__file__)),
                "install",
                "--archive",
                str(self.archive),
                "--target",
                str(target),
            ],
            capture_output=True,
            text=True,
            cwd=str(self.temp),
        )
        self.assertEqual(process.returncode, 2, process.stderr)
        self.assertNotIn("Traceback", process.stderr)
        reported = json.loads(process.stderr)
        self.assertFalse(reported["ok"])
        self.assertIn("refusing to overwrite existing skill", reported["error"])

    def test_staging_oserror_is_reported_as_bundle_error(self) -> None:
        parent = self.temp / "not-a-directory"
        parent.write_text("blocking file")
        with self.assertRaises(bundle.BundleError):
            bundle.extract(self.archive, parent)

    def test_rename_oserror_is_reported_as_bundle_error(self) -> None:
        target = self.temp / "rename-failure" / "bookify"
        with mock.patch.object(bundle.os, "rename", side_effect=OSError("simulated rename failure")):
            with self.assertRaises(bundle.BundleError):
                bundle.install(self.archive, target)
        self.assertFalse(target.exists())

    def test_runtime_files_are_tolerated_after_setup(self) -> None:
        target = self.temp / "installed-runtime" / "bookify"
        bundle.install(self.archive, target)
        (target / "engine" / ".venv" / "bin").mkdir(parents=True)
        (target / "engine" / ".venv" / "bin" / "python").write_text("stub")
        (target / "engine" / "work").mkdir()
        (target / "engine" / "work" / "out.txt").write_text("disposable")
        (target / "engine" / "build").mkdir()
        (target / "engine" / "build" / "verify.json").write_text("{}")
        self.assertTrue(bundle.verify_install(target)["ok"])

    def test_tamper_is_detected(self) -> None:
        target = self.temp / "installed-tamper" / "bookify"
        bundle.install(self.archive, target)
        with (target / "SKILL.md").open("a") as handle:
            handle.write("\ntampered\n")
        with self.assertRaises(bundle.BundleError):
            bundle.verify_install(target)

    def _write_tar(self, path: Path, members: list[tuple[tarfile.TarInfo, bytes | None]]) -> None:
        with path.open("wb") as raw:
            with gzip.GzipFile(fileobj=raw, mode="wb", mtime=0, filename="") as gz:
                with tarfile.open(fileobj=gz, mode="w", format=tarfile.GNU_FORMAT) as archive:
                    for info, data in members:
                        archive.addfile(info, io.BytesIO(data) if data is not None else None)

    def _member(self, name: str, data: bytes | None = None, kind: bytes = tarfile.REGTYPE):
        info = tarfile.TarInfo(name)
        info.mtime = 0
        info.mode = 0o644
        info.uid = info.gid = 0
        info.uname = info.gname = ""
        info.type = kind
        if data is not None:
            info.size = len(data)
        return info, data

    def _member_text(self, name: str) -> str:
        with tarfile.open(self.archive, "r:gz") as archive:
            handle = archive.extractfile(name)
            self.assertIsNotNone(handle, name)
            return handle.read().decode()

    def _manifest_paths(self) -> set[str]:
        manifest = json.loads(self._member_text("bookify/MANIFEST.json"))
        return {entry["path"] for entry in manifest["files"]}

    def test_traversal_archive_is_rejected(self) -> None:
        path = self.temp / "traversal.tar.gz"
        self._write_tar(path, [self._member("bookify/../../escape", b"x")])
        into = self.temp / "traversal-out"
        with self.assertRaises(bundle.BundleError):
            bundle.extract(path, into)
        self.assertFalse((self.temp / "escape").exists())

    def test_absolute_path_archive_is_rejected(self) -> None:
        path = self.temp / "absolute.tar.gz"
        self._write_tar(path, [self._member("/bookify/SKILL.md", b"x")])
        with self.assertRaises(bundle.BundleError):
            bundle.extract(path, self.temp / "absolute-out")

    def test_symlink_archive_is_rejected(self) -> None:
        path = self.temp / "symlink.tar.gz"
        info, _ = self._member("bookify/link", None, tarfile.SYMTYPE)
        info.linkname = "/etc/passwd"
        self._write_tar(path, [(info, None)])
        with self.assertRaises(bundle.BundleError):
            bundle.extract(path, self.temp / "symlink-out")

    def test_outside_prefix_archive_is_rejected(self) -> None:
        path = self.temp / "outside.tar.gz"
        self._write_tar(path, [self._member("other/SKILL.md", b"x")])
        with self.assertRaises(bundle.BundleError):
            bundle.extract(path, self.temp / "outside-out")

    def test_packaged_top_level_skill_and_readme_are_deliverable(self) -> None:
        skill = self._member_text("bookify/SKILL.md")
        readme = self._member_text("bookify/README.md")

        self.assertTrue(skill.startswith("---\n"))
        frontmatter = skill.split("---", 2)[1]
        self.assertIn("name:", frontmatter)
        self.assertIn("description:", frontmatter)
        for phrase in ("BOOKIFY_ENGINE", "side-left", "side-right", "full"):
            self.assertIn(phrase, skill)
        for text in (skill, readme):
            self.assertNotIn(str(bundle.ROOT), text)
        self.assertIn("verify_manifest.py", readme)
        self.assertLess(
            readme.index("verify_manifest.py"),
            readme.index("packaging/bookify_skill_bundle.py"),
        )

    def test_packaged_skill_and_readme_reference_existing_payload_paths(self) -> None:
        paths = self._manifest_paths()
        for required in (
            "SKILL.md",
            "README.md",
            "LICENCES.md",
            "references/checklist.md",
            "licences/OFL-1.1.txt",
            "licences/fonts-metadata.md",
            "licences/python-dependencies.md",
            "examples/catalogue.pdf",
            "engine/pyproject.toml",
            "engine/uv.lock",
            "engine/toolchain.lock.json",
            "engine/content/catalogue.yaml",
            "verify_manifest.py",
        ):
            self.assertIn(required, paths)

        readme = self._member_text("bookify/README.md")
        skill = self._member_text("bookify/SKILL.md")
        for referenced in (
            "references/checklist.md",
            "licences/OFL-1.1.txt",
            "licences/fonts-metadata.md",
            "examples/catalogue.pdf",
            "engine/pyproject.toml",
            "verify_manifest.py",
        ):
            self.assertIn(referenced, readme + skill)
        verify_section = readme.split("## Verify the installation", 1)[1]
        self.assertIn('python "$BOOKIFY_SKILL/verify_manifest.py"', verify_section)
        self.assertLess(
            verify_section.index("verify_manifest.py"),
            verify_section.index("packaging/bookify_skill_bundle.py"),
        )

    def test_packaged_verify_recipe_runs_from_payload_without_source_tree(self) -> None:
        into = self.temp / "readme-extract"
        bundle.extract(self.archive, into)
        skill_root = into / "bookify"
        script = skill_root / "verify_manifest.py"
        self.assertTrue(script.is_file())

        env = {
            name: value
            for name, value in os.environ.items()
            if name not in {"PYTHONPATH", "VIRTUAL_ENV", "UV_PROJECT_ENVIRONMENT"}
        }
        env["PYTHONNOUSERSITE"] = "1"

        direct = subprocess.run(
            [sys.executable, str(script)],
            cwd=str(skill_root),
            env=env,
            capture_output=True,
            text=True,
        )
        self.assertEqual(direct.returncode, 0, direct.stderr)
        direct_result = json.loads(direct.stdout)
        self.assertTrue(direct_result["ok"])
        self.assertEqual(Path(direct_result["root"]).resolve(), skill_root.resolve())

        unrelated = self.temp / "unrelated-cwd"
        unrelated.mkdir()
        relocated = subprocess.run(
            [sys.executable, str(script), "--target", str(skill_root)],
            cwd=str(unrelated),
            env=env,
            capture_output=True,
            text=True,
        )
        self.assertEqual(relocated.returncode, 0, relocated.stderr)
        relocated_result = json.loads(relocated.stdout)
        self.assertTrue(relocated_result["ok"])
        self.assertEqual(Path(relocated_result["root"]).resolve(), skill_root.resolve())
        self.assertNotIn(str(bundle.ROOT), relocated.stdout)

    def test_source_allowlist_stays_explicit(self) -> None:
        with tarfile.open(self.archive, "r:gz") as archive:
            names = {member.name for member in archive.getmembers()}
        for forbidden in (
            "bookify/.opencode",
            "bookify/docs",
            "bookify/build",
            "bookify/dist",
            "bookify/.venv",
        ):
            self.assertFalse(any(name == forbidden or name.startswith(forbidden + "/") for name in names))
        self.assertIn("bookify/engine/skill/bookify/SKILL.md", names)
        self.assertIn("bookify/engine/tests/test_skill.py", names)
        self.assertIn("bookify/engine/probe/probe.sh", names)
        self.assertIn("bookify/engine/probe/diagram.sh", names)
        self.assertIn("bookify/engine/probe/chart.sh", names)
        self.assertIn("bookify/examples/catalogue.pdf", names)


if __name__ == "__main__":
    unittest.main()
