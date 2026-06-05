"""JSON configuration plugin — parses JSON files for config extraction."""

import json
import re
from pathlib import Path
from typing import Any, Optional

from .._common import ConfigEntry, ConfigPlugin, ConfigRef, ConfigSchema
from .registry import register


CLASS_NAME_PATTERN = re.compile(r'^[A-Z][a-zA-Z0-9]*$')
PACKAGE_PATTERN = re.compile(r'^[a-z][a-z0-9]*(\.[a-z][a-z0-9]*)+$')
URL_PATTERN = re.compile(r'^https?://')
PACKAGE_JSON_PATTERN = re.compile(r'^@?[a-z][a-z0-9_-]*(/[a-z][a-z0-9_-]*)?$')


class JsonConfigPlugin(ConfigPlugin):
    """Plugin for JSON configuration files.

    Handles:
    - package.json (Node.js/npm)
    - tsconfig.json (TypeScript)
    - webpack.config.js (Webpack - parsed as JSON5 or stripped comments)
    - jest.config.js (Jest - parsed as JSON5 or stripped comments)
    - .eslintrc.json (ESLint)
    - settings.json (VSCode, etc.)
    - Any generic .json configuration

    Extracts:
    - Hierarchical config structure with dot-notation paths
    - npm package dependencies
    - TypeScript project references
    - Build tool configurations
    """

    name = "json"
    description = "JSON configuration files (.json)"

    @property
    def supported_langs(self) -> list[str]:
        return ["javascript", "typescript", "python", "java", "go"]

    @property
    def file_patterns(self) -> list[str]:
        return self.get_config_file_patterns()

    def get_config_file_patterns(self) -> list[str]:
        return [
            "*.json",
            "package.json",
            "tsconfig.json",
            "jsconfig.json",
            "**/tsconfig.json",
            "**/jsconfig.json",
            ".eslintrc.json",
            ".prettierrc",
            ".prettierrc.json",
            "jest.config.json",
            "webpack.config.json",
            "vite.config.json",
            "next.config.json",
            "**/package.json",
            "**/.eslintrc.json",
            "**/.prettierrc*",
            "**/jest.config.json",
            "**/webpack.config.json",
            "settings.json",
            "**/settings.json",
        ]

    def parse_config(self, file_path: Path, content: str) -> ConfigSchema:
        """Parse JSON file and extract config entries."""
        entries: list[ConfigEntry] = []
        refs: list[ConfigRef] = []
        file_str = str(file_path)

        try:
            # Handle potential trailing commas (common in JSON config files)
            clean_content = self._clean_json_content(content)
            data = json.loads(clean_content)
        except json.JSONDecodeError as e:
            return ConfigSchema(
                file=file_str,
                format="json",
                parse_error=True,
                error_msg=str(e),
            )

        if data is None:
            return ConfigSchema(
                file=file_str,
                format="json",
                parse_error=True,
                error_msg="Empty JSON file",
            )

        # Flatten and extract entries
        self._flatten_dict(data, "", entries, file_str)

        # Detect references
        refs = self._detect_references(entries, file_str, file_path)

        return ConfigSchema(
            file=file_str,
            format="json",
            entries=entries,
            refs=refs,
        )

    def _clean_json_content(self, content: str) -> str:
        """Clean JSON content for parsing (handle trailing commas, comments)."""
        # Remove trailing commas before ] or }
        content = re.sub(r',(\s*[}\]])', r'\1', content)
        # Remove single-line comments (// style) - for .eslintrc, tsconfig with comments
        content = re.sub(r'//.*$', '', content, flags=re.MULTILINE)
        # Remove multi-line comments (/* */ style)
        content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
        return content

    def _flatten_dict(
        self,
        data: Any,
        prefix: str,
        entries: list[ConfigEntry],
        file_str: str,
    ) -> None:
        """Recursively flatten nested dict/list structure into entries."""
        if isinstance(data, dict):
            for key, value in data.items():
                path = f"{prefix}.{key}" if prefix else key

                entry = ConfigEntry(
                    key=key,
                    value=self._get_string_value(value),
                    entry_type=self._get_value_type(value),
                    path=path,
                    line=0,  # JSON doesn't provide line numbers without extra parsing
                    file=file_str,
                    raw_value=self._get_raw_value(value),
                    metadata={"source": "json"},
                )
                entries.append(entry)

                # Recurse for nested structures
                if isinstance(value, dict):
                    self._flatten_dict(value, path, entries, file_str)
                elif isinstance(value, list):
                    self._flatten_list(value, path, entries, file_str)

        elif isinstance(data, list):
            self._flatten_list(data, prefix, entries, file_str)

    def _flatten_list(
        self,
        data: list,
        prefix: str,
        entries: list[ConfigEntry],
        file_str: str,
    ) -> None:
        """Handle list values in flattened structure."""
        for i, item in enumerate(data):
            path = f"{prefix}[{i}]"

            entry = ConfigEntry(
                key=str(i),
                value=self._get_string_value(item),
                entry_type=self._get_value_type(item),
                path=path,
                line=0,
                file=file_str,
                raw_value=self._get_raw_value(item),
                metadata={"source": "json", "is_array_item": True},
            )
            entries.append(entry)

            # Recurse for nested structures
            if isinstance(item, dict):
                self._flatten_dict(item, path, entries, file_str)

    def _get_value_type(self, value: Any) -> str:
        """Determine the type of a config value."""
        if value is None:
            return "null"
        elif isinstance(value, bool):
            return "boolean"
        elif isinstance(value, int):
            return "integer"
        elif isinstance(value, float):
            return "float"
        elif isinstance(value, str):
            return "string"
        elif isinstance(value, list):
            return "array"
        elif isinstance(value, dict):
            return "object"
        return "unknown"

    def _get_string_value(self, value: Any) -> Optional[str]:
        """Get string representation of a value."""
        if value is None:
            return None
        elif isinstance(value, bool):
            return str(value).lower()
        elif isinstance(value, (int, float)):
            return str(value)
        elif isinstance(value, str):
            return value
        elif isinstance(value, list):
            return ", ".join(str(v) for v in value)
        elif isinstance(value, dict):
            return str(value)
        return str(value)

    def _get_raw_value(self, value: Any) -> Optional[str]:
        """Get raw string value for reference detection."""
        if isinstance(value, str):
            return value
        return None

    def _detect_references(
        self,
        entries: list[ConfigEntry],
        file_str: str,
        file_path: Path,
    ) -> list[ConfigRef]:
        """Detect config references to code elements."""
        refs = []
        file_name = file_path.name.lower()

        for entry in entries:
            if not entry.raw_value:
                continue

            value = entry.raw_value

            # package.json dependencies
            if self._is_npm_package_ref(entry.path, value):
                refs.append(ConfigRef(
                    config_path=entry.path,
                    target=value,
                    target_type="package",
                    file=file_str,
                    line=entry.line,
                    confidence="high",
                    metadata={"format": "npm_package"},
                ))

            # URL references
            elif URL_PATTERN.match(value):
                refs.append(ConfigRef(
                    config_path=entry.path,
                    target=value,
                    target_type="url",
                    file=file_str,
                    line=entry.line,
                    confidence="high",
                    metadata={"format": "url"},
                ))

            # Path references (file paths in config)
            elif self._is_path_ref(entry.path, value):
                refs.append(ConfigRef(
                    config_path=entry.path,
                    target=value,
                    target_type="path",
                    file=file_str,
                    line=entry.line,
                    confidence="medium",
                    metadata={"format": "file_path"},
                ))

            # GitHub/GitLab references
            elif self._is_git_ref(value):
                refs.append(ConfigRef(
                    config_path=entry.path,
                    target=value,
                    target_type="repo",
                    file=file_str,
                    line=entry.line,
                    confidence="high",
                    metadata={"format": "git_ref"},
                ))

        return refs

    def _is_npm_package_ref(self, path: str, value: str) -> bool:
        """Check if this is an npm package reference."""
        dependency_paths = [
            "dependencies",
            "devDependencies",
            "peerDependencies",
            "optionalDependencies",
        ]

        path_lower = path.lower()
        is_dep_path = any(p in path_lower for p in dependency_paths)

        if is_dep_path and PACKAGE_JSON_PATTERN.match(value):
            return True

        return False

    def _is_path_ref(self, path: str, value: str) -> bool:
        """Check if value is a file path reference."""
        path_indicators = [
            "include",
            "exclude",
            "files",
            "entry",
            "output",
            "root",
            "src",
            "dist",
        ]

        path_lower = path.lower()
        is_path_path = any(ind in path_lower for ind in path_indicators)

        if is_path_path and (value.startswith('./') or value.startswith('/') or value.startswith('src/') or value.startswith('dist/')):
            return True

        return False

    def _is_git_ref(self, value: str) -> bool:
        """Check if value is a git repository reference."""
        git_patterns = [
            r'^https://github\.com/',
            r'^https://gitlab\.com/',
            r'^git@github\.com:',
            r'^git@gitlab\.com:',
            r'^http://gitlab\.',
        ]
        return any(re.match(p, value) for p in git_patterns)

    def get_config_schema_hints(self) -> dict[str, str]:
        """Return common package.json config hints."""
        return {
            "name": "string",
            "version": "string",
            "main": "string",
            "scripts": "object",
            "dependencies": "object",
            "devDependencies": "object",
            "engines": "object",
        }

    def parse(self, file_path: Path) -> "ConfigParseResult":
        """Parse a JSON file (required by ConfigPlugin interface)."""
        from .._common import ConfigParseResult
        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()
            schema = self.parse_config(file_path, content)
            return ConfigParseResult(
                file=str(file_path),
                entries=schema.entries if hasattr(schema, 'entries') else [],
                parse_error=schema.parse_error if hasattr(schema, 'parse_error') else False,
                error_msg=schema.error_msg if hasattr(schema, 'error_msg') else None,
            )
        except Exception as e:
            return ConfigParseResult(
                file=str(file_path),
                parse_error=True,
                error_msg=str(e),
            )


register(JsonConfigPlugin)
