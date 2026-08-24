"""Filesystem Outbound Adapter implementing SourceProviderPort."""

from __future__ import annotations

import os
from pathlib import Path

from pattern_detector.ports.outbound import SourceProviderPort


_IGNORED_DIR_NAMES = frozenset(
    {
        "build",
        "dist",
        ".git",
        "node_modules",
        ".venv",
        "venv",
        "env",
        "__pycache__",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".tox",
        ".idea",
        ".vscode",
    }
)


class FileSourceProvider(SourceProviderPort):
    """Fetches source code files from the local filesystem."""

    def get_sources(
        self,
        path: str,
        extensions: list[str] | None = None,
        exclude_dirs: list[str] | None = None,
    ) -> dict[str, str]:
        target = Path(path).resolve()
        valid_exts = set(extensions) if extensions else {".py", ".pyi"}
        user_excludes = {ex.strip("/\\") for ex in (exclude_dirs or []) if ex.strip("/\\")}

        if not target.exists():
            return {}

        if target.is_file():
            return self._read_single_file(target)

        return self._scan_directory(target, valid_exts, user_excludes)

    def _read_single_file(self, target: Path) -> dict[str, str]:
        try:
            content = target.read_text(encoding="utf-8", errors="replace")
            return {str(target.resolve()): content}
        except (OSError, UnicodeDecodeError):
            return {}

    def _scan_directory(
        self,
        target: Path,
        valid_exts: set[str],
        user_excludes: set[str],
    ) -> dict[str, str]:
        sources: dict[str, str] = {}

        for root, dirs, files in os.walk(str(target)):
            dirs[:] = [
                d
                for d in dirs
                if not d.startswith(".")
                and d not in _IGNORED_DIR_NAMES
                and d not in user_excludes
                and not any(ex == d or ex in f"{root}/{d}".split(os.sep) for ex in user_excludes)
            ]

            try:
                rel_parts = set(Path(root).resolve().relative_to(target).parts)
                if any(ex in rel_parts for ex in user_excludes):
                    continue
            except ValueError:
                pass

            for file_name in files:
                if file_name.startswith("."):
                    continue
                _, ext = os.path.splitext(file_name)
                if ext in valid_exts:
                    file_path = os.path.join(root, file_name)
                    content = self._safe_read_file(file_path)
                    if content is not None:
                        sources[file_path] = content
        return sources

    def _safe_read_file(self, file_path: str) -> str | None:
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                return f.read()
        except (OSError, UnicodeDecodeError):
            return None
