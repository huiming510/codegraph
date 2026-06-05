"""Environment variable configuration plugin — parses .env files."""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .._common import ConfigEntry, ConfigPlugin, ConfigRef, ConfigSchema
from .registry import register


# Pattern for parsing .env lines
ENV_LINE_PATTERN = re.compile(
    r'''
    ^
    (?:
        (?:\#.*)$  # Comment line
        |
        (?:\s*$)  # Empty line
        |
        (?P<key>[A-Za-z_][A-Za-z0-9_]*)  # Variable name
        (?:
            =(?:(?P<value>[^#\n]*))?  # Value (everything before # or newline)
        )?
    )
    $
    ''',
    re.VERBOSE | re.MULTILINE,
)

# Pattern for quoted values
QUOTED_VALUE_PATTERN = re.compile(r'^["\'](.*)["\']$')

# Common environment variable prefixes that map to frameworks/services
FRAMEWORK_PREFIXES = {
    "SPRING_": "spring",
    "DATASOURCE_": "database",
    "DB_": "database",
    "POSTGRES_": "database",
    "MYSQL_": "database",
    "REDIS_": "cache",
    "CACHE_": "cache",
    "KAFKA_": "messaging",
    "RABBITMQ_": "messaging",
    "AWS_": "cloud",
    "AZURE_": "cloud",
    "GCP_": "cloud",
    "SECRET_": "security",
    "JWT_": "security",
    "OAUTH_": "security",
    "LOG_": "logging",
    "LOGGING_": "logging",
    "SERVER_": "server",
    "APP_": "application",
    "NODE_": "node",
    "NEXT_PUBLIC_": "nextjs",
    "REACT_APP_": "react",
    "VUE_APP_": "vue",
    "DJANGO_": "django",
    "FLASK_": "flask",
    "GO_": "golang",
}


@dataclass
class EnvParseResult:
    """Result of parsing a single .env line."""
    entry: ConfigEntry
    ref: Optional[ConfigRef] = None


class EnvConfigPlugin(ConfigPlugin):
    """Plugin for environment variable configuration files (.env).

    Handles:
    - .env files (standard)
    - .env.local, .env.development, .env.production (environment-specific)
    - .env.*.local, .env.* (arbitrary environment suffixes)
    - .flaskenv, .node-cli.json (framework-specific env files)

    Extracts:
    - Environment variable names and values
    - Framework/service classification based on variable prefixes
    - Variable interpolation references (${VAR_NAME})
    - Default values

    Note: .env files are typically NOT imported directly in code, but they
    define runtime environment. This plugin captures the config structure
    for analysis purposes.
    """

    name = "env"
    description = "Environment variable files (.env)"

    @property
    def supported_langs(self) -> list[str]:
        # Env files are used with virtually all languages
        return ["java", "python", "javascript", "typescript", "go", "kotlin", "rust"]

    @property
    def file_patterns(self) -> list[str]:
        return self.get_config_file_patterns()

    def get_config_file_patterns(self) -> list[str]:
        return [
            ".env",
            ".env.local",
            ".env.development",
            ".env.production",
            ".env.test",
            ".env.staging",
            ".env.*",
            ".flaskenv",
            ".node-cli.json",
            "**/.env",
            "**/.env.local",
            "**/.env.*",
            "**/.flaskenv",
        ]

    def parse_config(self, file_path: Path, content: str) -> ConfigSchema:
        """Parse .env file and extract config entries."""
        entries: list[ConfigEntry] = []
        refs: list[ConfigRef] = []
        file_str = str(file_path)

        for line_num, line in enumerate(content.splitlines(), start=1):
            line = line.rstrip()  # Keep leading whitespace for parsing

            # Skip empty lines and comments
            if not line.strip() or line.strip().startswith('#'):
                continue

            # Parse the line
            parsed = self._parse_env_line(line, line_num, file_str)
            if parsed:
                entries.append(parsed.entry)

                # Detect reference if present
                if parsed.ref:
                    refs.append(parsed.ref)

        return ConfigSchema(
            file=file_str,
            format="env",
            entries=entries,
            refs=refs,
        )

    def _parse_env_line(
        self,
        line: str,
        line_num: int,
        file_str: str,
    ) -> Optional[EnvParseResult]:
        """Parse a single .env line."""
        # Find the separator (=)
        if '=' not in line:
            return None

        key, _, raw_value = line.partition('=')
        key = key.strip()
        value = raw_value.strip()

        # Skip invalid keys
        if not key or not key.isidentifier():
            return None

        # Remove quotes from value
        value_cleaned, had_quotes = self._unquote_value(value)

        # Remove inline comments (only if not quoted)
        if not had_quotes:
            value_cleaned = value_cleaned.split('#')[0].strip()

        # Determine type
        entry_type = self._get_value_type(value_cleaned)

        entry = ConfigEntry(
            key=key,
            value=value_cleaned,
            entry_type=entry_type,
            path=key,  # Env vars are flat, path == key
            line=line_num,
            file=file_str,
            raw_value=value_cleaned,
            metadata={
                "source": "env",
                "had_quotes": had_quotes,
                "framework": self._get_framework_prefix(key),
            },
        )

        # Detect reference
        ref = self._detect_ref(entry, file_str)

        return EnvParseResult(entry=entry, ref=ref)

    def _unquote_value(self, value: str) -> tuple[str, bool]:
        """Remove quotes from value and return (unquoted, had_quotes)."""
        if not value:
            return value, False

        # Check for matching quotes
        if len(value) >= 2:
            if (value[0] == '"' and value[-1] == '"') or (value[0] == "'" and value[-1] == "'"):
                return value[1:-1], True

        return value, False

    def _get_value_type(self, value: str) -> str:
        """Determine the type of an environment variable value."""
        if not value:
            return "string"

        # Boolean-like values
        if value.lower() in ('true', 'false', 'yes', 'no', '1', '0', 'on', 'off'):
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

        # URL
        if value.startswith('http://') or value.startswith('https://'):
            return "url"

        # Path
        if value.startswith('./') or value.startswith('/') or value.startswith('.'):
            return "path"

        return "string"

    def _get_framework_prefix(self, key: str) -> Optional[str]:
        """Get framework/service classification based on variable prefix."""
        for prefix, framework in FRAMEWORK_PREFIXES.items():
            if key.startswith(prefix):
                return framework
        return None

    def _detect_ref(self, entry: ConfigEntry, file_str: str) -> Optional[ConfigRef]:
        """Detect references from environment variable values."""
        if not entry.raw_value:
            return None

        value = entry.raw_value

        # Variable interpolation: ${VAR_NAME} or $VAR_NAME
        if '${' in value and '}' in value:
            # Extract referenced variable
            var_match = re.search(r'\$\{([A-Za-z_][A-Za-z0-9_]*)\}', value)
            if var_match:
                ref_var = var_match.group(1)
                return ConfigRef(
                    config_path=entry.path,
                    target=ref_var,
                    target_type="env_var",
                    file=file_str,
                    line=entry.line,
                    confidence="high",
                    metadata={
                        "format": "env_interpolation",
                        "original_value": value,
                    },
                )

        # URL reference
        if value.startswith('http://') or value.startswith('https://'):
            return ConfigRef(
                config_path=entry.path,
                target=value,
                target_type="url",
                file=file_str,
                line=entry.line,
                confidence="high",
                metadata={"format": "url"},
            )

        # Path reference
        if value.startswith('./') or value.startswith('/') or value.startswith('$'):
            return ConfigRef(
                config_path=entry.path,
                target=value,
                target_type="path",
                file=file_str,
                line=entry.line,
                confidence="medium",
                metadata={"format": "path"},
            )

        # Secret/token reference
        if 'SECRET' in entry.key.upper() or 'TOKEN' in entry.key.upper() or 'PASSWORD' in entry.key.upper():
            return ConfigRef(
                config_path=entry.path,
                target=entry.key,
                target_type="secret",
                file=file_str,
                line=entry.line,
                confidence="high",
                metadata={"format": "secret"},
            )

        return None

    def parse(self, file_path: Path) -> "ConfigParseResult":
        """Parse a .env file (required by ConfigPlugin interface)."""
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

    def resolve_config_edges(
        self,
        schema: "ConfigSchema",
        symbols: list[dict],
    ) -> list["ConfigEdge"]:
        """Generate edges for ENV config with ENV-specific patterns.

        Handles:
        - Connection strings (postgres://, mysql://, etc.) → config.env.connection
        - Secret/token variables → config.env.secret
        """
        from .._common import ConfigEdge

        edges = []

        for entry in schema.entries:
            if not entry.raw_value:
                continue

            value = entry.raw_value

            # Connection strings
            if value.startswith(("http://", "https://", "postgres://", "mysql://", "sqlite://", "mongodb://", "redis://")):
                edges.append(ConfigEdge(
                    kind="config.env.connection",
                    from_qname=f"env:{entry.path}",
                    to_qname=value,
                    file=entry.file,
                    line=entry.line,
                ))

            # Secret variables
            elif "SECRET" in entry.key.upper() or "KEY" in entry.key.upper() or "TOKEN" in entry.key.upper() or "PASSWORD" in entry.key.upper():
                edges.append(ConfigEdge(
                    kind="config.env.secret",
                    from_qname=f"env:{entry.path}",
                    to_qname="[SECRET]",
                    file=entry.file,
                    line=entry.line,
                ))

        # Also add edges for detected refs
        for ref in schema.refs:
            edges.append(ConfigEdge(
                kind=f"config.{ref.target_type}",
                from_qname=f"env:{ref.config_path}" if ref.target_type != "env_var" else f"env:{ref.config_path}",
                to_qname=ref.target,
                file=ref.file,
                line=ref.line,
                metadata={"target_type": ref.target_type, "confidence": ref.confidence},
            ))

        return edges

    def get_config_schema_hints(self) -> dict[str, str]:
        """Return common environment variable hints."""
        return {
            "PORT": "integer",
            "HOST": "string",
            "DATABASE_URL": "string",
            "REDIS_URL": "string",
            "LOG_LEVEL": "string",
            "NODE_ENV": "string",
            "SECRET_KEY": "string",
        }

    def produce_nodes(self, schema: "ConfigSchema") -> list[dict]:
        """Generate env_var nodes from .env entries."""
        nodes = []
        seen_ids: set[str] = set()

        for entry in schema.entries:
            key = entry.key
            value = getattr(entry, 'value', '') or ''
            if not key:
                continue

            var_id = f"env:{key}"
            if var_id in seen_ids:
                continue
            seen_ids.add(var_id)

            # Determine variable type
            var_type = "string"
            if "URL" in key or "HOST" in key or "PORT" in key:
                var_type = "url"
            elif "SECRET" in key or "TOKEN" in key or "KEY" in key or "PASSWORD" in key:
                var_type = "secret"
            elif "ENABLED" in key or "DEBUG" in key:
                var_type = "boolean"

            # Mask sensitive values
            display_value = value
            if var_type == "secret" and value:
                display_value = "***"

            nodes.append({
                "id": var_id,
                "qualified_name": var_id,
                "label": key,
                "kind": "env_var",
                "file": entry.file,
                "domain_tags": ["config.env"],
                "annotations": [],
                "var_type": var_type,
                "value": display_value,
            })

        return nodes


register(EnvConfigPlugin)
