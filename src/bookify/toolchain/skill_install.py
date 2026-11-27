"""Cross-platform AI-agent skill installer (Claude Code, Codex, OpenCode, Cursor, Antigravity)."""

from __future__ import annotations

import json
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path

from bookify import runtime
from bookify.errors import BookifyError

MARKER_FILE = ".bookify-skill.json"
SKILL_ID = "bookify"


@dataclass(frozen=True)
class PlatformSpec:
    name: str
    label: str
    global_skill_dir: tuple[str, ...]
    project_skill_dir: tuple[str, ...]
    global_commands_dir: tuple[str, ...] | None = None
    project_commands_dir: tuple[str, ...] | None = None


PLATFORMS: dict[str, PlatformSpec] = {
    "claude": PlatformSpec(
        name="claude",
        label="Claude Code",
        global_skill_dir=(".claude", "skills", SKILL_ID),
        project_skill_dir=(".claude", "skills", SKILL_ID),
        global_commands_dir=(".claude", "commands"),
        project_commands_dir=(".claude", "commands"),
    ),
    "codex": PlatformSpec(
        name="codex",
        label="OpenAI Codex",
        global_skill_dir=(".agents", "skills", SKILL_ID),
        project_skill_dir=(".agents", "skills", SKILL_ID),
    ),
    "opencode": PlatformSpec(
        name="opencode",
        label="OpenCode",
        global_skill_dir=(".config", "opencode", "skills", SKILL_ID),
        project_skill_dir=(".opencode", "skills", SKILL_ID),
        global_commands_dir=(".config", "opencode", "commands"),
        project_commands_dir=(".opencode", "commands"),
    ),
    "cursor": PlatformSpec(
        name="cursor",
        label="Cursor",
        global_skill_dir=(".cursor", "skills", SKILL_ID),
        project_skill_dir=(".cursor", "skills", SKILL_ID),
    ),
    "antigravity": PlatformSpec(
        name="antigravity",
        label="Google Antigravity",
        global_skill_dir=(".gemini", "config", "skills", SKILL_ID),
        project_skill_dir=(".agents", "skills", SKILL_ID),
    ),
    "agents": PlatformSpec(
        name="agents",
        label="Universal Agent Skills (~/.agents/skills)",
        global_skill_dir=(".agents", "skills", SKILL_ID),
        project_skill_dir=(".agents", "skills", SKILL_ID),
    ),
}


def skill_source_dir(engine: Path | None = None) -> Path:
    root = engine or runtime.engine_root()
    for rel in ("skills/bookify", "skill/bookify"):
        candidate = root / rel
        if (candidate / "SKILL.md").is_file():
            return candidate
    raise BookifyError("INPUT_INVALID", f"bundled Bookify skill not found under {root}", str(root))


def _resolve_target(
    spec: PlatformSpec,
    *,
    scope: str,
    home: Path,
    project_dir: Path,
) -> tuple[Path, Path | None]:
    if scope == "global":
        skill_dir = home.joinpath(*spec.global_skill_dir)
        cmd_dir = home.joinpath(*spec.global_commands_dir) if spec.global_commands_dir else None
        return skill_dir, cmd_dir
    if scope == "project":
        skill_dir = project_dir.joinpath(*spec.project_skill_dir)
        cmd_dir = project_dir.joinpath(*spec.project_commands_dir) if spec.project_commands_dir else None
        return skill_dir, cmd_dir
    raise BookifyError("INPUT_INVALID", f"unsupported scope: {scope}", scope)


def _is_existing_bookify_install(target: Path) -> bool:
    if (target / MARKER_FILE).is_file():
        return True
    manifest = target / "MANIFEST.json"
    if manifest.is_file():
        try:
            data = json.loads(manifest.read_text())
            if data.get("bundleId") == SKILL_ID or data.get("prefix") == SKILL_ID:
                return True
        except (OSError, json.JSONDecodeError):
            pass
    skill_md = target / "SKILL.md"
    if skill_md.is_file():
        head = skill_md.read_text(encoding="utf-8", errors="ignore")[:500].lower()
        if "name: bookify" in head:
            return True
    return False


def list_platforms(
    *,
    scope: str = "global",
    home: Path | None = None,
    project_dir: Path | None = None,
) -> list[dict[str, object]]:
    base_home = (home or Path.home()).resolve()
    base_proj = (project_dir or Path.cwd()).resolve()
    rows: list[dict[str, object]] = []
    for spec in PLATFORMS.values():
        skill_dir, cmd_dir = _resolve_target(spec, scope=scope, home=base_home, project_dir=base_proj)
        rows.append(
            {
                "platform": spec.name,
                "label": spec.label,
                "skillDir": str(skill_dir),
                "commandsDir": str(cmd_dir) if cmd_dir else None,
                "installed": _is_existing_bookify_install(skill_dir),
            }
        )
    return rows


def install_skill(
    platform_name: str,
    *,
    scope: str = "global",
    target_override: Path | None = None,
    overwrite: bool = False,
    install_commands: bool = True,
    home: Path | None = None,
    project_dir: Path | None = None,
    engine: Path | None = None,
) -> dict[str, object]:
    """Atomically install the lightweight Bookify skill to one or all agent platforms."""
    if platform_name == "all":
        if target_override is not None:
            raise BookifyError("INPUT_INVALID", "--target cannot be combined with --platform all", "--target")
        results = [
            install_skill(
                name,
                scope=scope,
                overwrite=overwrite,
                install_commands=install_commands,
                home=home,
                project_dir=project_dir,
                engine=engine,
            )
            for name in ("claude", "codex", "opencode", "cursor", "antigravity")
        ]
        return {"ok": True, "platform": "all", "results": results}

    if platform_name not in PLATFORMS:
        raise BookifyError(
            "INPUT_INVALID",
            f"unknown platform {platform_name!r}; choose from {', '.join(PLATFORMS)} or all",
            platform_name,
        )

    spec = PLATFORMS[platform_name]
    source = skill_source_dir(engine)
    base_home = (home or Path.home()).resolve()
    base_proj = (project_dir or Path.cwd()).resolve()
    skill_dir, cmd_dir = _resolve_target(spec, scope=scope, home=base_home, project_dir=base_proj)
    if target_override is not None:
        skill_dir = target_override.expanduser().resolve()
        cmd_dir = None

    if skill_dir.is_symlink():
        raise BookifyError("INPUT_INVALID", f"refusing to overwrite symlink: {skill_dir}", str(skill_dir))
    if skill_dir.exists():
        if not overwrite and not _is_existing_bookify_install(skill_dir):
            raise BookifyError(
                "INPUT_INVALID",
                f"target exists and is not a Bookify skill install: {skill_dir} (pass --overwrite to replace)",
                str(skill_dir),
            )

    skill_dir.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=skill_dir.parent, prefix=".bookify-skill-") as stage_raw:
        staged = Path(stage_raw) / SKILL_ID
        shutil.copytree(source, staged)
        marker = {
            "skillId": SKILL_ID,
            "version": runtime.version(),
            "platform": spec.name,
            "scope": scope,
        }
        (staged / MARKER_FILE).write_text(json.dumps(marker, indent=2, sort_keys=True) + "\n")

        backup: Path | None = None
        if skill_dir.exists():
            backup = Path(stage_raw) / "previous"
            skill_dir.rename(backup)
        try:
            staged.rename(skill_dir)
        except Exception:
            if backup is not None and backup.exists() and not skill_dir.exists():
                backup.rename(skill_dir)
            raise

    installed_commands: list[str] = []
    if install_commands and cmd_dir is not None and (source / "commands").is_dir():
        cmd_dir.mkdir(parents=True, exist_ok=True)
        for cmd_file in sorted((source / "commands").glob("*.md")):
            dest_cmd = cmd_dir / cmd_file.name
            if dest_cmd.is_symlink():
                raise BookifyError("INPUT_INVALID", f"refusing to overwrite symlink command: {dest_cmd}", str(dest_cmd))
            shutil.copy2(cmd_file, dest_cmd)
            installed_commands.append(str(dest_cmd))

    return {
        "ok": True,
        "platform": spec.name,
        "label": spec.label,
        "scope": scope,
        "skillDir": str(skill_dir),
        "commands": installed_commands,
        "version": runtime.version(),
    }
