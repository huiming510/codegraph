"""YAML configuration plugin — parses YAML files for config extraction."""

import re
from pathlib import Path
from typing import Any, Optional

import yaml  # type: ignore

from .._common import ConfigEntry, ConfigPlugin, ConfigRef, ConfigSchema
from .registry import register


# Patterns for detecting config references to code elements
CLASS_NAME_PATTERN = re.compile(r'^[A-Z][a-zA-Z0-9]*$')
PACKAGE_PATTERN = re.compile(r'^[a-z][a-z0-9]*(\.[a-z][a-z0-9]*)+$')
BEAN_NAME_PATTERN = re.compile(r'^[a-z][a-z0-9]*(-[a-z0-9]+)*$')


class YamlConfigPlugin(ConfigPlugin):
    """Plugin for YAML configuration files.

    Handles:
    - application.yml / application.yaml
    - Spring Boot configurations
    - Kubernetes manifests (partial)
    - Docker Compose files
    - Ansible playbooks

    Extracts:
    - Hierarchical config structure with dot-notation paths
    - References to beans, classes, services
    - Environment variable bindings
    - Profile-specific configurations
    """

    name = "yaml"
    description = "YAML configuration files (.yaml, .yml)"

    @property
    def supported_langs(self) -> list[str]:
        return ["java", "python", "javascript", "go", "kotlin"]

    @property
    def file_patterns(self) -> list[str]:
        return self.get_config_file_patterns()

    def get_config_file_patterns(self) -> list[str]:
        return [
            "*.yaml",
            "*.yml",
            "**/*.yaml",
            "**/*.yml",
            "application.yml",
            "application.yaml",
            "**/application.yml",
            "**/application.yaml",
        ]

    def parse_config(self, file_path: Path, content: str) -> ConfigSchema:
        """Parse YAML file and extract config entries."""
        entries: list[ConfigEntry] = []
        refs: list[ConfigRef] = []
        file_str = str(file_path)

        try:
            data = yaml.safe_load(content)
            if data is None:
                return ConfigSchema(
                    file=file_str,
                    format="yaml",
                    parse_error=True,
                    error_msg="Empty or invalid YAML file",
                )
        except yaml.YAMLError as e:
            return ConfigSchema(
                file=file_str,
                format="yaml",
                parse_error=True,
                error_msg=str(e),
            )

        # Flatten and extract entries
        self._flatten_dict(data, "", entries, file_str)

        # Detect references
        refs = self._detect_references(entries, file_str)

        return ConfigSchema(
            file=file_str,
            format="yaml",
            entries=entries,
            refs=refs,
        )

    def _flatten_dict(
        self,
        data: Any,
        prefix: str,
        entries: list[ConfigEntry],
        file_str: str,
        line_offset: int = 0,
    ) -> None:
        """Recursively flatten nested dict/list structure into entries."""
        if isinstance(data, dict):
            for key, value in data.items():
                path = f"{prefix}.{key}" if prefix else key
                entry_type = self._get_value_type(value)
                raw_value = self._get_raw_value(value)

                entry = ConfigEntry(
                    key=key,
                    value=self._get_string_value(value),
                    entry_type=entry_type,
                    path=path,
                    line=line_offset,
                    file=file_str,
                    raw_value=raw_value,
                    metadata={"source": "yaml"},
                )
                entries.append(entry)

                # Recurse for nested structures
                if isinstance(value, dict):
                    self._flatten_dict(value, path, entries, file_str, line_offset)
                elif isinstance(value, list):
                    self._flatten_list(value, path, entries, file_str, line_offset)

        elif isinstance(data, list):
            self._flatten_list(data, prefix, entries, file_str, line_offset)

    def _flatten_list(
        self,
        data: list,
        prefix: str,
        entries: list[ConfigEntry],
        file_str: str,
        line_offset: int,
    ) -> None:
        """Handle list values in flattened structure."""
        for i, item in enumerate(data):
            path = f"{prefix}[{i}]"
            entry_type = self._get_value_type(item)
            raw_value = self._get_raw_value(item)

            entry = ConfigEntry(
                key=str(i),
                value=self._get_string_value(item),
                entry_type=entry_type,
                path=path,
                line=line_offset,
                file=file_str,
                raw_value=raw_value,
                metadata={"source": "yaml", "is_array_item": True},
            )
            entries.append(entry)

            # Recurse for nested structures
            if isinstance(item, dict):
                self._flatten_dict(item, path, entries, file_str, line_offset)

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
    ) -> list[ConfigRef]:
        """Detect config references to code elements."""
        refs = []

        for entry in entries:
            if not entry.raw_value:
                continue

            value = entry.raw_value

            # Spring Boot bean references (spring.main.banner-mode, etc.)
            if self._is_spring_bean_ref(value):
                refs.append(ConfigRef(
                    config_path=entry.path,
                    target=value,
                    target_type="bean",
                    file=file_str,
                    line=entry.line,
                    confidence="high",
                    metadata={"format": "spring_bean"},
                ))

            # Class name references (main class, config classes)
            elif self._is_class_ref(entry.path, value):
                refs.append(ConfigRef(
                    config_path=entry.path,
                    target=value,
                    target_type="class",
                    file=file_str,
                    line=entry.line,
                    confidence="medium",
                    metadata={"format": "class_ref"},
                ))

            # Package path references
            elif self._is_package_ref(value):
                refs.append(ConfigRef(
                    config_path=entry.path,
                    target=value,
                    target_type="package",
                    file=file_str,
                    line=entry.line,
                    confidence="high",
                    metadata={"format": "package_path"},
                ))

            # URL references
            elif self._is_url_ref(value):
                refs.append(ConfigRef(
                    config_path=entry.path,
                    target=value,
                    target_type="url",
                    file=file_str,
                    line=entry.line,
                    confidence="high",
                    metadata={"format": "url"},
                ))

            # Environment variable references
            elif self._is_env_var_ref(value):
                refs.append(ConfigRef(
                    config_path=entry.path,
                    target=value,
                    target_type="env_var",
                    file=file_str,
                    line=entry.line,
                    confidence="high",
                    metadata={"format": "env_ref"},
                ))

        return refs

    def _is_spring_bean_ref(self, value: str) -> bool:
        """Check if value looks like a Spring bean reference."""
        # Spring bean names: kebab-case, camelCase, or class names
        return (
            BEAN_NAME_PATTERN.match(value) or
            (value and value[0].isupper() and '.' in value)  # Fully qualified class name
        )

    def _is_class_ref(self, path: str, value: str) -> bool:
        """Check if config path and value suggest a class reference."""
        class_indicator_paths = [
            "main-class",
            "sources.main.java",
            "main-class-name",
            "banner.image.image-chars",
        ]
        class_indicator_paths_lower = [p.lower() for p in class_indicator_paths]

        path_lower = path.lower()
        if any(ind in path_lower for ind in class_indicator_paths_lower):
            return True

        # Value looks like a class name
        if CLASS_NAME_PATTERN.match(value) and len(value) > 3:
            return True

        return False

    def _is_package_ref(self, value: str) -> bool:
        """Check if value looks like a package path."""
        return bool(PACKAGE_PATTERN.match(value))

    def _is_url_ref(self, value: str) -> bool:
        """Check if value looks like a URL."""
        url_patterns = (
            value.startswith("http://") or
            value.startswith("https://") or
            value.startswith("jdbc:") or
            value.startswith("file://") or
            value.startswith("classpath:")
        )
        return url_patterns

    def _is_env_var_ref(self, value: str) -> bool:
        """Check if value references an environment variable."""
        return (
            value.startswith("${") and value.endswith("}") or
            value.startswith("$") or
            (value.upper() == value and "_" in value)
        )

    def get_config_schema_hints(self) -> dict[str, str]:
        """Return common Spring Boot config hints."""
        return {
            "server.port": "integer",
            "server.address": "string",
            "spring.datasource.url": "string",
            "spring.datasource.username": "string",
            "spring.datasource.password": "string",
            "spring.datasource.driver-class-name": "string",
            "spring.jpa.hibernate.ddl-auto": "string",
            "spring.jpa.show-sql": "boolean",
            "logging.level.root": "string",
            "logging.level": "string",
            "spring.main.banner-mode": "string",
            "spring.main.allow-bean-definition-overriding": "boolean",
        }

    def parse(self, file_path: Path) -> "ConfigParseResult":
        """Parse a YAML file (required by ConfigPlugin interface)."""
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

    def detect_references(
        self,
        schema: ConfigSchema,
        symbols: list[dict],
    ) -> list[ConfigRef]:
        """Enhanced reference detection with symbol table lookup."""
        refs = list(schema.refs)

        # Try to match config values to symbols
        for entry in schema.entries:
            if not entry.raw_value:
                continue

            value = entry.raw_value

            # Match against symbol names
            for sym in symbols:
                sym_name = sym.get("name", "")
                sym_qname = sym.get("qualified_name", sym_name)

                # Direct class name match
                if value == sym_name or value == sym_qname:
                    # Avoid duplicates
                    if not any(r.target == value and r.config_path == entry.path for r in refs):
                        refs.append(ConfigRef(
                            config_path=entry.path,
                            target=sym_qname,
                            target_type="class",
                            file=entry.file,
                            line=entry.line,
                            confidence="high",
                            metadata={"matched_symbol": sym_qname},
                        ))

        return refs


register(YamlConfigPlugin)
