"""Filesystem Outbound Adapter implementing SourceProviderPort."""

from __future__ import annotations

from pathlib import Path

from pattern_detector.ports.outbound import SourceProviderPort


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
            return {str(target): content}
        except (OSError, UnicodeDecodeError):
            return {}

    def _scan_directory(self, target: Path, valid_exts: set[str]) -> dict[str, str]:
        sources: dict[str, str] = {}
        for file_path in target.rglob("*"):
            if file_path.is_file() and file_path.suffix in valid_exts and not self._is_ignored_path(file_path, target):
                content = self._safe_read_file(file_path)
                if content is not None:
                    sources[str(file_path)] = content
        return sources

    def _safe_read_file(self, file_path: Path) -> str | None:
        try:
            return file_path.read_text(encoding="utf-8", errors="replace")
        except (OSError, UnicodeDecodeError):
            return None

    def _is_ignored_path(self, file_path: Path, target: Path) -> bool:
        ignored_dirs = {
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
        }
        try:
            rel_parts = file_path.relative_to(target).parts
        except ValueError:
            rel_parts = file_path.parts

        has_hidden = any(part.startswith(".") and part not in (".", "..") for part in rel_parts)
        has_ignored = any(part in ignored_dirs for part in rel_parts)
        return has_hidden or has_ignored
