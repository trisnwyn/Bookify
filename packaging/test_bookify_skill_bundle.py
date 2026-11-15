"""Safety and determinism tests for the Bookify skill bundler (stdlib only).

Run with: python -m unittest packaging/test_bookify_skill_bundle.py
"""

from __future__ import annotations

import gzip
import hashlib
import io
import json
import os
import re
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
                self.assertNotIn("/.opencode/", name)
                self.assertNotIn("/docs/", name)
                self.assertFalse(name.startswith("/"))
            self.assertNotIn("bookify/engine/content/trial.yaml", names)
            self.assertNotIn("bookify/engine/content/agent-skill", names)
            for member in archive.getmembers():
                if not member.isfile():
                    continue
                handle = archive.extractfile(member)
                self.assertIsNotNone(handle)
                data = handle.read()
                self.assertNotIn(str(bundle.ROOT).encode(), data, member.name)
                # A packaged test may guard against the host home path, but it
                # must use Path.home() rather than embedding the literal.
                self.assertNotIn(str(Path.home()).encode(), data, member.name)
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
        canonical = (bundle.ROOT / "skill" / "bookify" / "SKILL.md").read_text()
        canonical_name = re.search(r"^name:\s*(.+)$", canonical, re.M)
        packaged_name = re.search(r"^name:\s*(.+)$", frontmatter, re.M)
        self.assertIsNotNone(canonical_name)
        self.assertIsNotNone(packaged_name)
        self.assertEqual(canonical_name.group(1).strip(), packaged_name.group(1).strip())
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
            "LICENSE",
            "LICENCES.md",
            "references/checklist.md",
            "references/modes-and-playbooks.md",
            "references/source-and-provenance.md",
            "references/editorial.md",
            "references/visual-design.md",
            "references/limits.md",
            "commands/bookify.md",
            "commands/bookify-source-faithful.md",
            "commands/bookify-teachable-textbook.md",
            "licences/OFL-1.1.txt",
            "licences/fonts-metadata.md",
            "licences/python-dependencies.md",
            "examples/catalogue.pdf",
            "engine/pyproject.toml",
            "engine/uv.lock",
            "engine/toolchain.lock.json",
            "engine/content/catalogue.yaml",
            "engine/content/specimen.yaml",
            "engine/fixtures/agent-skill/source.pdf",
            "engine/skill/bookify/commands/bookify.md",
            "engine/skill/bookify/references/editorial.md",
            "verify_manifest.py",
        ):
            self.assertIn(required, paths)

        license_text = self._member_text("bookify/LICENSE")
        self.assertIn("MIT License", license_text)
        self.assertIn("Tris Nguyen", license_text)
        # The rights record names the licence file, so the bundle must carry it.
        self.assertIn("`LICENSE`", self._member_text("bookify/LICENCES.md"))

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

    def test_packaged_docs_never_instruct_writing_inside_the_engine(self) -> None:
        skill = self._member_text("bookify/SKILL.md")
        readme = self._member_text("bookify/README.md")
        flat_skill = " ".join(skill.split())

        self.assertNotIn("write under `work/` inside the engine", flat_skill)
        self.assertIn("never write inside the installed engine", flat_skill)
        self.assertNotIn("keep every write under", flat_skill)

        for block in re.findall(r"```sh\n(.*?)```", readme, re.S):
            if 'cd "$BOOKIFY_SKILL/engine"' in block:
                self.assertNotIn("--out dist/", block)
                self.assertNotIn("--build-dir work/", block)

        catalogue = readme.split("The catalogue reproduction", 1)[1].split("Expected:", 1)[0]
        self.assertIn('cd "$WS/engine"', catalogue)
        self.assertNotIn('cd "$BOOKIFY_SKILL/engine"', catalogue)

    def test_packaged_readme_references_only_the_current_release_archive(self) -> None:
        readme = self._member_text("bookify/README.md")
        current = "bookify-skill-v2-final.tar.gz"

        referenced = set(re.findall(r"bookify-skill[\w.-]*\.tar\.gz", readme))
        self.assertEqual(referenced, {current})
        self.assertNotIn("bookify-skill-plan2-layout.tar.gz", readme)
        self.assertNotIn("bookify-skill.tar.gz", readme)
        self.assertTrue(
            (bundle.ROOT / "dist" / current).is_file(),
            f"README references a missing archive: dist/{current}",
        )

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
        self.assertIn("bookify/engine/skill/bookify/commands/bookify.md", names)
        self.assertIn("bookify/engine/skill/bookify/references/editorial.md", names)
        # The suite is source-checkout evidence: it reads content/agent-skill and
        # the development OCR copy, both excluded from the payload.
        self.assertFalse(any(name.startswith("bookify/engine/tests/") for name in names))
        self.assertFalse(any(name.startswith("bookify/engine/packaging/") for name in names))
        self.assertIn("bookify/engine/probe/probe.sh", names)
        self.assertIn("bookify/engine/probe/diagram.sh", names)
        self.assertIn("bookify/engine/probe/chart.sh", names)
        self.assertIn("bookify/examples/catalogue.pdf", names)
        # Three slash entries and all six top-level guides.
        for command in bundle.COMMAND_NAMES:
            self.assertIn(f"bookify/commands/{command}.md", names)
        for guide in bundle.REFERENCE_NAMES:
            self.assertIn(f"bookify/references/{guide}.md", names)
        # The private trial manuscript is never packaged.
        self.assertNotIn("bookify/engine/content/trial.yaml", names)
        self.assertIn("bookify/engine/content/specimen.yaml", names)

    def test_ocr_development_artefacts_are_excluded(self) -> None:
        with tarfile.open(self.archive, "r:gz") as archive:
            members = archive.getmembers()
            names = [member.name for member in members]

            for name in names:
                self.assertFalse(
                    name.endswith(".traineddata"),
                    f"OCR language data leaked: {name}",
                )
                self.assertNotIn("/vendor/ocr/tessdata/", name)
                self.assertNotIn("/fixtures/ocr-capability/build/", name)
                self.assertFalse(
                    name.startswith("bookify/engine/tools/ocr/tesseract"),
                    f"OCR development CLI leaked: {name}",
                )

            for member in members:
                if not member.name.startswith("bookify/engine/tools/ocr/"):
                    continue
                if not member.isfile():
                    continue
                handle = archive.extractfile(member)
                self.assertIsNotNone(handle)
                with handle:
                    self.assertNotEqual(
                        handle.read(4),
                        b"\x7fELF",
                        f"ELF binary in tools/ocr: {member.name}",
                    )

    def test_required_ocr_support_files_are_packaged(self) -> None:
        paths = self._manifest_paths()
        for required in (
            "engine/src/bookify/intake/ocr.py",
            "engine/src/bookify/verify/checks/machine_read.py",
            "engine/src/bookify/verify/checks/ocr_free.py",
            "engine/tools/ocr/ocr_harness.py",
            "engine/tools/ocr/ocr.lock.fragment.json",
            "engine/tools/ocr/README.md",
            "engine/tools/ocr/LICENSE",
            "engine/fixtures/ocr-capability/fixture.pdf",
            "engine/fixtures/ocr-capability/README.md",
            "engine/fixtures/ocr-capability/build_fixture.py",
            "engine/fixtures/ocr-capability/source/fixture.typ",
            "engine/fixtures/ocr-capability/source/trial-balance.typ",
            "engine/fixtures/ocr-capability/source/cash-receipts.typ",
        ):
            self.assertIn(required, paths)
        # The released fixture is the public synthetic PDF, not a build product.
        fixture = next(
            entry
            for entry in json.loads(self._member_text("bookify/MANIFEST.json"))["files"]
            if entry["path"] == "engine/fixtures/ocr-capability/fixture.pdf"
        )
        self.assertEqual(
            fixture["sha256"],
            "c3c09d6f57b57f04dd3eefc6724a5b51dcb8466fbaa42ff0ca6333941ba3481d",
        )

    def test_top_level_skill_and_readme_document_ocr_setup_and_boundary(self) -> None:
        skill = " ".join(self._member_text("bookify/SKILL.md").split())
        readme = " ".join(self._member_text("bookify/README.md").split())
        combined = skill + " " + readme

        for phrase in (
            "intake-only",
            "system `tesseract`",
            "tesseract-langpack-eng",
            "tesseract-langpack-vie",
            "opt-in",
            "tone-mark",
            "11.65 s",
            "39 minutes",
            "13 minutes",
        ):
            self.assertIn(phrase, combined, phrase)
        for text in (skill, readme):
            self.assertIn("never need OCR", text)
            self.assertIn("never shipped", text)
            self.assertIn("OCR-free", text)
        # The development copy is described as excluded, not as a fallback.
        self.assertIn("never shipped", readme)
        self.assertNotIn("silent fallback", readme)

        # The packaged OCR setup guide repeats the system-package requirement
        # and the development-copy exclusion, so an operator never has to read
        # the source checkout to learn the supported engine.
        ocr_setup = " ".join(
            self._member_text("bookify/engine/tools/ocr/README.md").split()
        )
        for phrase in (
            "system Tesseract package",
            "sudo dnf install tesseract tesseract-langpack-eng",
            "never appear in the public bundle",
            "never need OCR",
        ):
            self.assertIn(phrase, ocr_setup, phrase)

    def test_build_and_verify_source_never_invokes_ocr(self) -> None:
        with tarfile.open(self.archive, "r:gz") as archive:
            for member in archive.getmembers():
                if not member.isfile():
                    continue
                if not member.name.startswith(
                    (
                        "bookify/engine/src/bookify/publish/",
                        "bookify/engine/src/bookify/verify/",
                    )
                ):
                    continue
                if not member.name.endswith(".py"):
                    continue
                handle = archive.extractfile(member)
                self.assertIsNotNone(handle)
                text = handle.read().decode("utf-8", "replace")
                lowered = text.lower()
                self.assertNotIn("tesseract", lowered, member.name)
                self.assertNotIn("traineddata", lowered, member.name)
                self.assertNotIn("intake.ocr", lowered, member.name)

    def test_manifest_declares_commands_and_guides_with_parity(self) -> None:
        manifest = json.loads(self._member_text("bookify/MANIFEST.json"))
        self.assertEqual(set(manifest["commands"]), set(bundle.COMMAND_NAMES))
        self.assertEqual(
            manifest["guides"],
            sorted(f"references/{name}.md" for name in bundle.REFERENCE_NAMES),
        )
        self.assertEqual(manifest["entrypoints"]["commands"], "commands/")
        files = {entry["path"]: entry for entry in manifest["files"]}
        for name in bundle.COMMAND_NAMES:
            entry = manifest["commands"][name]
            self.assertEqual(entry["path"], f"commands/{name}.md")
            self.assertEqual(entry["mode"], bundle.COMMAND_MODES[name])
            self.assertEqual(entry["defaultAlias"], name == bundle.COMMAND_DEFAULT_ALIAS)
            self.assertEqual(entry["sha256"], files[f"commands/{name}.md"]["sha256"])
            canonical = (bundle.ROOT / "skill" / "bookify" / "commands" / f"{name}.md").read_bytes()
            self.assertEqual(self._member_text(f"bookify/commands/{name}.md").encode(), canonical)
            self.assertEqual(
                (bundle.PAYLOAD / "commands" / f"{name}.md").read_bytes(), canonical
            )
        for name in bundle.REFERENCE_NAMES:
            canonical = (
                bundle.ROOT / "skill" / "bookify" / "references" / f"{name}.md"
            ).read_bytes()
            self.assertEqual(
                self._member_text(f"bookify/references/{name}.md").encode(), canonical
            )
        self.assertEqual(len([path for path in files if path.startswith("commands/")]), 3)

    def test_packaged_commands_load_skill_and_declare_two_authoritative_modes(self) -> None:
        modes = set()
        for name in bundle.COMMAND_NAMES:
            text = self._member_text(f"bookify/commands/{name}.md")
            modes.add(bundle.COMMAND_MODES[name])
            self.assertIn("Bookify skill", text)
            self.assertIn("$ARGUMENTS", text)
            standalone = [line for line in text.splitlines() if line.strip() == "$ARGUMENTS"]
            self.assertEqual(len(standalone), 1)
            self.assertIn("source-faithful", text)
            self.assertIn("attachments", text.lower())
            self.assertIn("Preserve any", text)
            self.assertIn("Do not ask", text)
            self.assertIn("which mode", text)
            self.assertIn("Do not\nrely on `@path`", text)
            # No shell interpolation line and no frontmatter agent/model pin.
            for line in text.splitlines():
                self.assertFalse(line.lstrip().startswith("!"), line)
            frontmatter = text.split("---", 2)[1]
            self.assertNotIn("agent:", frontmatter)
            self.assertNotIn("model:", frontmatter)
            self.assertNotIn("subtask:", frontmatter)
        self.assertEqual(modes, {"source-faithful", "teachable"})
        teachable = self._member_text("bookify/commands/bookify-teachable-textbook.md")
        flat = " ".join(teachable.split())
        self.assertIn("natural coursebook prose", flat)
        self.assertIn("the provided materials suggest", flat)
        self.assertIn("citation", flat)
        self.assertIn("uncertainty", flat)
        strict = self._member_text("bookify/commands/bookify-source-faithful.md")
        self.assertIn("no teaching apparatus", strict)
        self.assertIn("no outside material", strict)

    def test_relocated_payload_runs_with_source_repository_denied(self) -> None:
        into = self.temp / "source-denied"
        bundle.extract(self.archive, into)
        skill_root = into / "bookify"
        script = skill_root / "verify_manifest.py"
        self.assertTrue(script.is_file())

        site = self.temp / "deny-site"
        site.mkdir()
        (site / "sitecustomize.py").write_text(
            "import os\n"
            "import sys\n"
            "_root = os.environ.get('BOOKIFY_DENY_ROOT', '')\n"
            "def _hook(event, args):\n"
            "    if not _root or not args:\n"
            "        return\n"
            "    if event not in {'open', 'os.listdir', 'os.scandir', 'os.chdir'}:\n"
            "        return\n"
            "    try:\n"
            "        candidate = os.path.abspath(os.fsdecode(args[0]))\n"
            "    except (TypeError, ValueError):\n"
            "        return\n"
            "    if candidate == _root or candidate.startswith(_root + os.sep):\n"
            "        raise PermissionError('source repository access denied: ' + candidate)\n"
            "sys.addaudithook(_hook)\n"
        )
        home = self.temp / "denied-home"
        temporary = self.temp / "denied-tmp"
        unrelated = self.temp / "denied-cwd"
        for directory in (home, temporary, unrelated):
            directory.mkdir()
        env = {
            name: value
            for name, value in os.environ.items()
            if name
            not in {
                "PYTHONPATH",
                "PYTHONHOME",
                "VIRTUAL_ENV",
                "UV_PROJECT_ENVIRONMENT",
                "CONDA_PREFIX",
            }
        }
        env.update(
            {
                "PYTHONPATH": str(site),
                "PYTHONNOUSERSITE": "1",
                "HOME": str(home),
                "TMPDIR": str(temporary),
                "BOOKIFY_DENY_ROOT": str(bundle.ROOT),
            }
        )

        probe = subprocess.run(
            [
                sys.executable,
                "-c",
                f"open({str(bundle.ROOT / 'README.md')!r}).read()",
            ],
            cwd=str(unrelated),
            env=env,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(probe.returncode, 0)
        self.assertIn("source repository access denied", probe.stderr)

        relocated = subprocess.run(
            [sys.executable, str(script), "--target", str(skill_root)],
            cwd=str(unrelated),
            env=env,
            capture_output=True,
            text=True,
        )
        self.assertEqual(relocated.returncode, 0, relocated.stderr)
        result = json.loads(relocated.stdout)
        self.assertTrue(result["ok"])
        self.assertEqual(Path(result["root"]).resolve(), skill_root.resolve())
        self.assertNotIn(str(bundle.ROOT), relocated.stdout)


def _write_small_archive(directory: Path, label: str) -> Path:
    """Build a small valid bundle archive for install/upgrade tests.

    The real archive is already packed once by ``BundleTests``; using a small
    archive keeps collision and rollback tests fast and independent of the
    engine payload.
    """
    directory.mkdir(parents=True, exist_ok=True)
    base = Path(tempfile.mkdtemp(prefix="small-bundle-", dir=directory))
    contents = {
        "SKILL.md": (
            f"---\nname: Bookify\ndescription: {label}\n---\n\n# {label}\n".encode()
        ),
        "README.md": f"# {label}\n".encode(),
        "engine/pyproject.toml": b'[project]\nname = "bookify"\nversion = "0.1.0"\n',
        "references/checklist.md": f"# Checklist {label}\n".encode(),
    }
    for command in bundle.COMMAND_NAMES:
        contents[f"commands/{command}.md"] = f"# {label} {command}\n".encode()
    payload: dict[str, tuple[Path, int]] = {}
    for arcname, data in contents.items():
        path = base / arcname
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        path.chmod(0o644)
        payload[arcname] = (path, 0o644)
    manifest = bundle._manifest_bytes(payload)
    archive = base / "bundle.tar.gz"
    bundle._write_archive(archive, payload, manifest)
    return archive


def _archive_text(archive_path: Path, name: str) -> str:
    with tarfile.open(archive_path, "r:gz") as archive:
        handle = archive.extractfile(name)
        if handle is None:
            raise AssertionError(f"not a file in archive: {name}")
        return handle.read().decode()


class CommandInstallationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._temp = tempfile.TemporaryDirectory(prefix="bookify-command-tests-")
        cls.temp = Path(cls._temp.name)
        cls.archive = _write_small_archive(cls.temp / "archives", "release-one")
        cls.blobs = {
            name: _archive_text(cls.archive, f"bookify/commands/{name}.md").encode()
            for name in bundle.COMMAND_NAMES
        }

    @classmethod
    def tearDownClass(cls) -> None:
        cls._temp.cleanup()

    def _global_like_target(self, name: str) -> Path:
        parent = self.temp / name / ".config" / "opencode"
        parent.mkdir(parents=True)
        target = parent / "commands"
        target.mkdir()
        return target

    def test_installs_three_commands_and_verifies(self) -> None:
        target = self._global_like_target("fresh")
        result = bundle.install_commands(self.archive, target)
        self.assertTrue(result["ok"])
        self.assertEqual(sorted(result["installed"]), sorted(f"{n}.md" for n in bundle.COMMAND_NAMES))
        for name in bundle.COMMAND_NAMES:
            self.assertEqual((target / f"{name}.md").read_bytes(), self.blobs[name])
        verified = bundle.verify_commands(self.archive, target)
        self.assertTrue(verified["ok"])
        self.assertEqual(verified["commands"], [f"{name}.md" for name in bundle.COMMAND_NAMES])

    def test_identical_commands_are_idempotent_without_rewrite(self) -> None:
        target = self._global_like_target("idempotent")
        bundle.install_commands(self.archive, target)
        before = {path.name: path.stat().st_mtime_ns for path in target.iterdir()}
        result = bundle.install_commands(self.archive, target)
        self.assertEqual(result["installed"], [])
        self.assertEqual(sorted(result["unchanged"]), sorted(bundle.COMMAND_NAMES))
        after = {path.name: path.stat().st_mtime_ns for path in target.iterdir()}
        self.assertEqual(before, after)

    def test_collision_refuses_all_before_writing_anything(self) -> None:
        target = self._global_like_target("collision")
        (target / "other.md").write_text("someone else's command\n")
        (target / "bookify-source-faithful.md").write_text("user edited command\n")
        with self.assertRaises(bundle.BundleError) as raised:
            bundle.install_commands(self.archive, target)
        message = str(raised.exception)
        self.assertIn("refusing to overwrite", message)
        self.assertIn("bookify-source-faithful.md", message)
        # The preflight refusal leaves the other two commands unwritten and the
        # unrelated command untouched.
        self.assertEqual((target / "other.md").read_text(), "someone else's command\n")
        self.assertEqual(
            (target / "bookify-source-faithful.md").read_text(), "user edited command\n"
        )
        self.assertFalse((target / "bookify.md").exists())
        self.assertFalse((target / "bookify-teachable-textbook.md").exists())

    def test_symlinked_command_file_is_refused(self) -> None:
        target = self._global_like_target("symlink-file")
        outside = self.temp / "symlink-outside.md"
        outside.write_text("outside\n")
        (target / "bookify.md").symlink_to(outside)
        with self.assertRaises(bundle.BundleError):
            bundle.install_commands(self.archive, target)
        self.assertEqual(outside.read_text(), "outside\n")
        self.assertFalse((target / "bookify-source-faithful.md").exists())

    def test_symlinked_commands_directory_is_refused(self) -> None:
        real = self.temp / "real-commands"
        real.mkdir()
        link = self.temp / "linked-commands"
        link.symlink_to(real)
        with self.assertRaises(bundle.BundleError):
            bundle.install_commands(self.archive, link)
        self.assertEqual(list(real.iterdir()), [])

    def test_broken_symlink_target_is_refused(self) -> None:
        link = self.temp / "broken-commands"
        link.symlink_to(self.temp / "missing-commands")
        with self.assertRaises(bundle.BundleError):
            bundle.install_commands(self.archive, link)
        self.assertFalse((self.temp / "missing-commands").exists())

    def test_project_install_creates_only_the_final_directory(self) -> None:
        project = self.temp / "project"
        (project / ".opencode").mkdir(parents=True)
        target = project / ".opencode" / "commands"
        result = bundle.install_commands(self.archive, target, create=True)
        self.assertTrue(result["ok"])
        self.assertTrue(target.is_dir())
        self.assertTrue((target / "bookify.md").is_file())

    def test_create_requires_an_existing_parent(self) -> None:
        target = self.temp / "missing-parent" / "commands"
        with self.assertRaises(bundle.BundleError):
            bundle.install_commands(self.archive, target, create=True)
        self.assertFalse(target.exists())

    def test_partial_install_failure_rolls_back_installed_commands(self) -> None:
        target = self._global_like_target("rollback")
        real_rename = bundle.os.rename
        calls = {"count": 0}

        def flaky_rename(source: Path, destination: Path) -> None:
            calls["count"] += 1
            if calls["count"] == 2:
                raise OSError("simulated rename failure")
            real_rename(source, destination)

        with mock.patch.object(bundle.os, "rename", side_effect=flaky_rename):
            with self.assertRaises(bundle.BundleError):
                bundle.install_commands(self.archive, target)
        self.assertEqual(list(target.iterdir()), [])

    def test_force_flag_is_rejected_and_writes_nothing(self) -> None:
        target = self._global_like_target("force")
        process = subprocess.run(
            [
                sys.executable,
                str(Path(bundle.__file__)),
                "install-commands",
                "--archive",
                str(self.archive),
                "--target",
                str(target),
                "--force",
            ],
            capture_output=True,
            text=True,
            cwd=str(self.temp),
        )
        self.assertNotEqual(process.returncode, 0)
        self.assertEqual(list(target.iterdir()), [])


class SkillUpgradeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._temp = tempfile.TemporaryDirectory(prefix="bookify-upgrade-tests-")
        cls.temp = Path(cls._temp.name)
        cls.previous = _write_small_archive(cls.temp / "archives", "release-one")
        cls.current = _write_small_archive(cls.temp / "archives", "release-two")

    @classmethod
    def tearDownClass(cls) -> None:
        cls._temp.cleanup()

    def _install_previous(self, name: str) -> Path:
        target = self.temp / name / "bookify"
        bundle.install(self.previous, target)
        return target

    def _manifest_sha(self, target: Path) -> str:
        return hashlib.sha256((target / "MANIFEST.json").read_bytes()).hexdigest()

    def test_upgrade_replaces_verified_payload_and_keeps_backup(self) -> None:
        target = self._install_previous("upgrade-ok")
        previous_sha = self._manifest_sha(target)
        backup = self.temp / "upgrade-ok-backup"
        result = bundle.upgrade(
            self.current,
            target,
            expect_manifest_sha256=previous_sha,
            backup=backup,
        )
        self.assertTrue(result["ok"])
        self.assertEqual(result["previousManifestSha256"], previous_sha)
        self.assertTrue((target / "SKILL.md").read_text().endswith("# release-two\n"))
        self.assertTrue((backup / "SKILL.md").read_text().endswith("# release-one\n"))
        self.assertTrue(bundle.verify_install(target)["ok"])
        self.assertNotEqual(self._manifest_sha(target), previous_sha)

    def test_upgrade_refuses_unknown_manifest_hash(self) -> None:
        target = self._install_previous("upgrade-unknown")
        backup = self.temp / "upgrade-unknown-backup"
        with self.assertRaises(bundle.BundleError):
            bundle.upgrade(
                self.current,
                target,
                expect_manifest_sha256="0" * 64,
                backup=backup,
            )
        self.assertTrue((target / "SKILL.md").read_text().endswith("# release-one\n"))
        self.assertFalse(backup.exists())

    def test_upgrade_refuses_user_edited_payload(self) -> None:
        target = self._install_previous("upgrade-edited")
        previous_sha = self._manifest_sha(target)
        with (target / "SKILL.md").open("a") as handle:
            handle.write("\nlocal edit\n")
        backup = self.temp / "upgrade-edited-backup"
        with self.assertRaises(bundle.BundleError):
            bundle.upgrade(
                self.current,
                target,
                expect_manifest_sha256=previous_sha,
                backup=backup,
            )
        self.assertIn("local edit", (target / "SKILL.md").read_text())
        self.assertFalse(backup.exists())

    def test_upgrade_refuses_existing_backup(self) -> None:
        target = self._install_previous("upgrade-backup-exists")
        previous_sha = self._manifest_sha(target)
        backup = self.temp / "upgrade-backup-exists-backup"
        backup.mkdir()
        with self.assertRaises(bundle.BundleError):
            bundle.upgrade(
                self.current,
                target,
                expect_manifest_sha256=previous_sha,
                backup=backup,
            )
        self.assertTrue((target / "SKILL.md").read_text().endswith("# release-one\n"))

    def test_upgrade_rolls_back_when_the_new_payload_fails_verification(self) -> None:
        target = self._install_previous("upgrade-rollback")
        previous_sha = self._manifest_sha(target)
        backup = self.temp / "upgrade-rollback-backup"
        real_verify = bundle._verify_manifest
        calls = {"count": 0}

        def flaky_verify(path: Path, *, allow_runtime: bool) -> dict:
            calls["count"] += 1
            if calls["count"] == 2:
                raise bundle.BundleError("simulated post-install verification failure")
            return real_verify(path, allow_runtime=allow_runtime)

        with mock.patch.object(bundle, "_verify_manifest", side_effect=flaky_verify):
            with self.assertRaises(bundle.BundleError):
                bundle.upgrade(
                    self.current,
                    target,
                    expect_manifest_sha256=previous_sha,
                    backup=backup,
                )
        self.assertTrue((target / "SKILL.md").read_text().endswith("# release-one\n"))
        self.assertEqual(self._manifest_sha(target), previous_sha)
        self.assertFalse(backup.exists())

    def test_upgrade_refuses_symlinked_target(self) -> None:
        real = self._install_previous("upgrade-symlink-real")
        link = self.temp / "upgrade-symlink-target"
        link.symlink_to(real)
        with self.assertRaises(bundle.BundleError):
            bundle.upgrade(
                self.current,
                link,
                expect_manifest_sha256=self._manifest_sha(real),
                backup=self.temp / "upgrade-symlink-backup",
            )
        self.assertTrue((real / "SKILL.md").read_text().endswith("# release-one\n"))

    def test_upgrade_cli_has_no_force(self) -> None:
        process = subprocess.run(
            [
                sys.executable,
                str(Path(bundle.__file__)),
                "upgrade",
                "--archive",
                str(self.current),
                "--target",
                str(self.temp / "cli-upgrade-target"),
                "--expect-manifest-sha256",
                "0" * 64,
                "--backup",
                str(self.temp / "cli-upgrade-backup"),
                "--force",
            ],
            capture_output=True,
            text=True,
            cwd=str(self.temp),
        )
        self.assertNotEqual(process.returncode, 0)


if __name__ == "__main__":
    unittest.main()
