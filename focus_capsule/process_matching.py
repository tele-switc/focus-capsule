"""Stable process matching shared by every focus-enforcement path."""

from __future__ import annotations

import os
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

import psutil

_WRAPPER_AFFIXES = (
    "app",
    "bootstrap",
    "client",
    "console",
    "desktop",
    "gui",
    "helper",
    "host",
    "launch",
    "launcher",
    "runtime",
    "start",
    "starter",
)
_GENERIC_WRAPPER_NAMES = frozenset(_WRAPPER_AFFIXES)
_RUNTIME_HOST_IDENTITIES = frozenset(
    {
        "cscript",
        "cscript.exe",
        "dotnet",
        "dotnet.exe",
        "electron",
        "electron.exe",
        "java",
        "java.exe",
        "javaw",
        "javaw.exe",
        "node",
        "node.exe",
        "nw",
        "nw.exe",
        "python",
        "python.exe",
        "pythonw",
        "pythonw.exe",
        "ruby",
        "ruby.exe",
        "rubyw",
        "rubyw.exe",
        "wscript",
        "wscript.exe",
    }
)


@dataclass(frozen=True)
class ProcessIdentity:
    process_name: str
    executable_path: str
    process_id: int


def process_identities(value: str) -> set[str]:
    """Return exact executable identities without fuzzy substring matching."""
    normalized = (value or "").strip().casefold().replace("\\", "/")
    if not normalized:
        return set()

    basename = normalized.rsplit("/", 1)[-1]
    identities = {normalized, basename}
    if basename.endswith(".exe"):
        identities.add(basename[:-4])
    elif basename.endswith(".app"):
        identities.add(basename[:-4])
    return {item for item in identities if item}


def _normalized_path(value: str) -> str:
    if not value:
        return ""
    try:
        return os.path.normcase(os.path.abspath(os.path.expandvars(value)))
    except (OSError, ValueError):
        return ""


def _is_runtime_host(process_name: str, executable_path: str) -> bool:
    identities = process_identities(process_name)
    identities.update(process_identities(executable_path))
    return bool(identities.intersection(_RUNTIME_HOST_IDENTITIES))


def _process_lineage(process_id: int, max_depth: int = 8) -> tuple[ProcessIdentity, ...]:
    """Return the live process and bounded ancestors, tolerating process races."""
    try:
        current = psutil.Process(int(process_id))
    except (psutil.Error, TypeError, ValueError):
        return ()

    result: list[ProcessIdentity] = []
    seen: set[int] = set()
    for _ in range(max(1, max_depth)):
        try:
            pid = int(current.pid)
            if pid <= 0 or pid in seen:
                break
            seen.add(pid)
            name = current.name().strip().casefold()
            try:
                executable_path = current.exe().strip()
            except (psutil.AccessDenied, psutil.NoSuchProcess, OSError):
                executable_path = ""
            result.append(ProcessIdentity(name, executable_path, pid))
            current = current.parent()
            if current is None:
                break
        except (psutil.AccessDenied, psutil.NoSuchProcess, psutil.ZombieProcess, OSError):
            break
    return tuple(result)


def _compact_identity(value: str) -> str:
    return "".join(character for character in Path(value).stem.casefold() if character.isalnum())


def _strip_wrapper_affixes(identity: str) -> str:
    result = identity
    changed = True
    while changed and result:
        changed = False
        for affix in _WRAPPER_AFFIXES:
            if result.startswith(affix) and len(result) > len(affix) + 2:
                result = result[len(affix) :]
                changed = True
            if result.endswith(affix) and len(result) > len(affix) + 2:
                result = result[: -len(affix)]
                changed = True
    return result


def _known_install_roots() -> tuple[Path, ...]:
    candidates = [
        os.environ.get("ProgramFiles", ""),
        os.environ.get("ProgramFiles(x86)", ""),
        os.environ.get("LOCALAPPDATA", ""),
        os.environ.get("APPDATA", ""),
    ]
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    if local_app_data:
        candidates.append(str(Path(local_app_data) / "Programs"))

    roots: list[Path] = []
    for candidate in candidates:
        if not candidate:
            continue
        path = Path(os.path.abspath(os.path.expandvars(candidate)))
        if path not in roots:
            roots.append(path)
    return tuple(sorted(roots, key=lambda path: len(path.parts), reverse=True))


def _path_is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _safe_shared_install_directory(selected_path: Path, foreground_path: Path) -> Path | None:
    try:
        common = Path(
            os.path.commonpath(
                (
                    os.path.abspath(selected_path),
                    os.path.abspath(foreground_path),
                )
            )
        )
    except (OSError, ValueError):
        return None

    if common in {selected_path, foreground_path}:
        common = common.parent
    windows_root = os.environ.get("WINDIR", "")
    if windows_root and _path_is_within(common, Path(os.path.abspath(windows_root))):
        return None

    for root in _known_install_roots():
        if not (_path_is_within(selected_path, root) and _path_is_within(foreground_path, root)):
            continue
        if common == root:
            return None
        try:
            if not common.relative_to(root).parts:
                return None
        except ValueError:
            return None
        return common

    # Portable applications are supported too, but a drive root or broad user
    # directory is never enough evidence.
    if len(common.parts) <= 2:
        return None
    if common not in {selected_path.parent, foreground_path.parent}:
        return None
    return common


def _executable_identities_are_related(
    selected_path: Path,
    foreground_path: Path,
    shared_directory: Path,
) -> bool:
    selected_raw = _compact_identity(selected_path.name)
    foreground_raw = _compact_identity(foreground_path.name)
    selected = _strip_wrapper_affixes(selected_raw)
    foreground = _strip_wrapper_affixes(foreground_raw)
    if not selected_raw or not foreground_raw:
        return False
    if selected_raw == foreground_raw or (selected and selected == foreground):
        return True
    if min(len(selected), len(foreground)) >= 5 and (
        selected in foreground or foreground in selected
    ):
        return True

    directory_identity = _strip_wrapper_affixes(_compact_identity(shared_directory.name))
    if not directory_identity:
        return False

    def wrapper_matches_app(wrapper: str, application: str) -> bool:
        is_wrapper = wrapper in _GENERIC_WRAPPER_NAMES or not _strip_wrapper_affixes(wrapper)
        return bool(
            is_wrapper
            and min(len(directory_identity), len(application)) >= 4
            and (
                directory_identity == application
                or directory_identity in application
                or application in directory_identity
            )
        )

    # Launchers can appear on either side: discovery may resolve a shortcut to
    # a launcher, while an already installed catalog entry can point directly
    # at the main executable and briefly foreground a sibling launcher/helper.
    return wrapper_matches_app(selected_raw, foreground) or wrapper_matches_app(
        foreground_raw,
        selected,
    )


def same_application_family(selected_path: str, foreground_path: str) -> bool:
    """Return whether two executable paths strongly identify the same app.

    A safe shared installation directory and related executable identities are
    both required. Merely sharing ``Program Files`` never grants access.
    """
    if not selected_path or not foreground_path:
        return False
    selected = Path(os.path.abspath(os.path.expandvars(selected_path)))
    foreground = Path(os.path.abspath(os.path.expandvars(foreground_path)))
    if os.path.normcase(selected) == os.path.normcase(foreground):
        return True
    shared = _safe_shared_install_directory(selected, foreground)
    if shared is None:
        return False
    return _executable_identities_are_related(selected, foreground, shared)


class ProcessMatcher:
    """Match foreground processes and learn verified launcher/runtime aliases."""

    def __init__(
        self,
        allowed_apps: Iterable[str] = (),
        allowed_app_paths: dict[str, str] | None = None,
    ):
        self._allowed_apps = tuple(
            dict.fromkeys(str(app).strip().casefold() for app in allowed_apps if str(app).strip())
        )
        self._allowed_app_paths = {
            str(process).strip().casefold(): str(path).strip()
            for process, path in (allowed_app_paths or {}).items()
            if str(process).strip() and str(path).strip()
        }
        self._learned_aliases: dict[str, set[str]] = {}
        self._learned_runtime_paths: dict[str, set[str]] = {}
        self._matched_app = ""

    @property
    def learned_aliases(self) -> dict[str, set[str]]:
        return {key: set(values) for key, values in self._learned_aliases.items()}

    @property
    def learned_runtime_paths(self) -> dict[str, set[str]]:
        return {key: set(values) for key, values in self._learned_runtime_paths.items()}

    @property
    def matched_app(self) -> str:
        return self._matched_app

    def _match_identity(
        self,
        process_name: str,
        executable_path: str,
        *,
        learn_family_alias: bool,
    ) -> str:
        process_ids = process_identities(process_name)
        if not process_ids:
            return ""
        normalized_executable = _normalized_path(executable_path)

        for allowed in self._allowed_apps:
            if (
                normalized_executable
                and normalized_executable
                in self._learned_runtime_paths.get(allowed, set())
            ):
                return allowed

            selected_path = self._allowed_app_paths.get(allowed, "")
            if process_ids.intersection(process_identities(allowed)):
                # A stored path is stronger than a process name. When both are
                # available, do not allow an unrelated executable that merely
                # copied the selected app's filename.
                if (
                    not selected_path
                    or not executable_path
                    or same_application_family(selected_path, executable_path)
                ):
                    return allowed
            if process_ids.intersection(self._learned_aliases.get(allowed, set())):
                return allowed

        if not executable_path:
            return ""
        for allowed, selected_path in self._allowed_app_paths.items():
            if not same_application_family(selected_path, executable_path):
                continue
            if learn_family_alias:
                self._learned_aliases.setdefault(allowed, set()).update(process_ids)
            return allowed
        return ""

    def is_allowed(
        self,
        process_name: str,
        executable_path: str = "",
        process_id: int = 0,
    ) -> bool:
        self._matched_app = ""
        direct_match = self._match_identity(
            process_name,
            executable_path,
            learn_family_alias=True,
        )
        if direct_match:
            self._matched_app = direct_match
            return True

        # Some desktop apps intentionally host their UI in a generic runtime.
        # Modern Anki, for example, is selected as anki.exe but its foreground
        # window belongs to pythonw.exe in AnkiProgramFiles. Only accept such a
        # host when its live ancestor chain contains the selected executable.
        # This avoids globally allowing every pythonw.exe/electron.exe process.
        if process_id <= 0 or not _is_runtime_host(process_name, executable_path):
            return False

        lineage = _process_lineage(process_id)
        descendants = lineage[1:] if lineage and lineage[0].process_id == process_id else lineage
        for ancestor in descendants:
            ancestor_match = self._match_identity(
                ancestor.process_name,
                ancestor.executable_path,
                learn_family_alias=False,
            )
            if not ancestor_match:
                continue
            normalized_runtime = _normalized_path(executable_path)
            if normalized_runtime:
                self._learned_runtime_paths.setdefault(ancestor_match, set()).add(
                    normalized_runtime
                )
            self._matched_app = ancestor_match
            return True
        return False


def process_is_allowed(
    process_name: str,
    allowed_apps: Iterable[str],
    executable_path: str = "",
    allowed_app_paths: dict[str, str] | None = None,
    process_id: int = 0,
) -> bool:
    """Convenience wrapper for one-off matching."""
    return ProcessMatcher(allowed_apps, allowed_app_paths).is_allowed(
        process_name,
        executable_path,
        process_id,
    )
