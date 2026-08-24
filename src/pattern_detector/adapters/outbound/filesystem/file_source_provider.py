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

    def get_sources(self, path: str, extensions: list[str] | None = None) -> dict[str, str]:
        target = Path(path)
        valid_exts = set(extensions) if extensions else {".py", ".pyi"}

        if not target.exists():
            return {}

        if target.is_file():
            return self._read_single_file(target)

        return self._scan_directory(target, valid_exts)

    def _read_single_file(self, target: Path) -> dict[str, str]:
        try:
            content = target.read_text(encoding="utf-8", errors="replace")
            return {str(target.resolve()): content}
        except (OSError, UnicodeDecodeError):
            return {}

    def _scan_directory(self, target: Path, valid_exts: set[str]) -> dict[str, str]:
        sources: dict[str, str] = {}
        target_str = str(target.resolve())

        for root, dirs, files in os.walk(target_str):
            # In-place directory pruning to avoid traversing ignored subtrees
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in _IGNORED_DIR_NAMES]
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
