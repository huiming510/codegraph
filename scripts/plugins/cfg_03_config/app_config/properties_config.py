"""Properties configuration plugin — parses Java properties files."""

import re
from pathlib import Path
from typing import Optional

from .._common import ConfigPlugin
from .registry import register


class PropertiesConfigPlugin(ConfigPlugin):
    """Plugin for Java properties files.

    Handles:
    - .properties files (standard Java properties format)
    - i18n/resource bundle files (messages_*.properties)
    - Application-specific property files

    Note: Does NOT handle XML property files (those are handled by XML config).
    """

    name = "properties"
    description = "Java properties files (.properties)"

    @property
    def supported_langs(self) -> list[str]:
        return ["java", "kotlin"]

    @property
    def file_patterns(self) -> list[str]:
        return self.get_config_file_patterns()

    def get_config_file_patterns(self) -> list[str]:
        return [
            "*.properties",
            "**/*.properties",
            "messages*.properties",
            "**/messages*.properties",
            "application.properties",
            "**/application.properties",
        ]

    def parse(self, file_path: Path) -> "ConfigParseResult":
        """Parse a properties file and return ConfigParseResult."""
        try:
            with open(file_path, encoding="utf-8", errors="replace") as f:
                content = f.read()
            entries = self._parse_content(content, str(file_path))
            return ConfigParseResult(
                file=str(file_path),
                entries=entries,
                parse_error=False,
            )
        except Exception as e:
            return ConfigParseResult(
                file=str(file_path),
                entries=[],
                parse_error=True,
                error_msg=str(e),
            )

    def _parse_content(self, content: str, file_str: str) -> list[dict]:
        """Parse properties file content and return list of entry dicts."""
        entries = []
        for line_num, line in enumerate(content.splitlines(), start=1):
            line = line.strip()

            # Skip empty lines and comments
            if not line or line.startswith('#') or line.startswith('!'):
                continue

            # Parse key-value pair
            entry = self._parse_line(line, line_num, file_str)
            if entry:
                entries.append(entry)

        return entries

    def _parse_line(self, line: str, line_num: int, file_str: str) -> Optional[dict]:
        """Parse a single properties line and return entry dict."""
        # Find the separator (first : or =)
        separator_idx = -1
        for i, char in enumerate(line):
            if char in ('=', ':'):
                separator_idx = i
                break

        if separator_idx == -1:
            return None

        key = line[:separator_idx].strip()
        value = line[separator_idx + 1:].strip()

        # Determine value type
        value_type = self._get_value_type(value)

        # Build entry dict
        entry = {
            "key": key,
            "value": value,
            "name": key,  # Use key as name for display
            "entry_type": value_type,
            "path": key,
            "line": line_num,
            "file": file_str,
            "raw_value": value,
            "metadata": {
                "source": "properties",
            },
        }

        # Detect and add reference info
        ref_info = self._detect_ref(key, value, file_str, line_num)
        if ref_info:
            entry["metadata"]["ref"] = ref_info

        return entry

    def _get_value_type(self, value: str) -> str:
        """Determine the type of a config value."""
        # Boolean
        if value.lower() in ('true', 'false'):
            return "boolean"

        # Number
        try:
            int(value)
            return "integer"
        except ValueError:
            pass

        try:
            float(value)
            return "float"
        except ValueError:
            pass

        # String
        return "string"

    def _detect_ref(self, key: str, value: str, file_str: str, line_num: int) -> Optional[dict]:
        """Detect config references and return as dict."""
        if not value:
            return None

        # Environment variable reference: ${VAR_NAME}
        if value.startswith('${') and value.endswith('}'):
            var_name = value[2:-1]
            # Remove default value: ${VAR_NAME:default}
            if ':' in var_name:
                var_name = var_name.split(':')[0]
            return {
                "path": key,
                "target": var_name,
                "target_type": "env_var",
                "file": file_str,
                "line": line_num,
                "confidence": "high",
                "format": "property_expansion",
            }

        # Password/secret reference: keys ending with _PASS, _PASSWORD, _SECRET, _KEY, _TOKEN
        if key.upper().endswith(('_PASS', '_PASSWORD', '_SECRET', '_KEY', '_TOKEN', '_CREDENTIAL', '_AUTH')):
            return {
                "path": key,
                "target": value,
                "target_type": "credential",
                "file": file_str,
                "line": line_num,
                "confidence": "high",
                "format": "credential_ref",
            }

        # JDBC URL reference
        if value.startswith('jdbc:'):
            return {
                "path": key,
                "target": value,
                "target_type": "jdbc_url",
                "file": file_str,
                "line": line_num,
                "confidence": "high",
                "format": "jdbc_connection",
            }

        # URL reference
        if value.startswith('http://') or value.startswith('https://'):
            return {
                "path": key,
                "target": value,
                "target_type": "url",
                "file": file_str,
                "line": line_num,
                "confidence": "high",
                "format": "url",
            }

        # File path reference (values ending with common file extensions)
        if any(value.endswith(ext) for ext in ('.xml', '.properties', '.dicon', '.tld')):
            return {
                "path": key,
                "target": value,
                "target_type": "file_ref",
                "file": file_str,
                "line": line_num,
                "confidence": "medium",
                "format": "file_path",
            }

        return None

    def get_config_schema_hints(self) -> dict[str, str]:
        """Return common Java properties config hints."""
        return {
            "server.port": "integer",
            "spring.datasource.url": "string",
            "spring.datasource.username": "string",
            "spring.datasource.password": "string",
            "spring.jpa.hibernate.ddl-auto": "string",
        }


from .._common import ConfigParseResult
register(PropertiesConfigPlugin)
