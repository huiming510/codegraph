"""Dicon (Dependency Injection Configuration) component cross-file plugin.

Generates edges from .dicon dependency injection configuration to Java components.
"""

from pathlib import Path

from ...common.base import Edge
from ..base import CrossFilePlugin
from ..constants import is_external_package
from ..registry import register


class DiconComponentCrossFilePlugin(CrossFilePlugin):
    """Cross-file plugin for .dicon DI configurations → Java components."""

    @property
    def name(self) -> str:
        return "dicon_component"

    @property
    def description(self) -> str:
        return ".dicon DI configuration → Java component bindings"

    @property
    def supported_langs(self) -> list[str]:
        return ["java"]

    def can_produce(self, context, lang: str = None) -> bool:
        """Check if we have dicon data."""
        return len(context.ui_data.get("dicon", [])) > 0

    def produce(self, context, lang: str = None, elements: dict = None) -> list[dict]:
        """Generate dicon cross-file edges."""
        edges = []

        for dicon_entry in (elements or {}).get("dicon", []):
            if dicon_entry.get("parse_error"):
                continue

            dicon_file = dicon_entry.get("file", "")
            dicon_name = Path(dicon_file).name

            # Support both formats:
            # 1. Flat format: [{components: [...]}]
            # 2. Nested format: [{entries: [{entry_type, class_name, ...}]}]

            components = dicon_entry.get("components", [])
            if components:
                # Flat format
                for comp in components:
                    # Support both 'class' and 'class_name' field names
                    cls = comp.get("class") or comp.get("class_name") or ""
                    if not cls:
                        continue

                    # Skip external packages and Creator classes
                    if "Creator" in cls or is_external_package(cls):
                        continue

                    edges.append(Edge(
                        kind="di_component",
                        from_qname=f"config::{dicon_file}",
                        to_qname=cls,
                        file=dicon_file,
                        line=comp.get("line", 0),
                    ))
            else:
                # Nested format from JavaConfig: entries with entry_type
                entries = dicon_entry.get("entries", [])
                for entry in entries:
                    if entry.get("entry_type") != "dicon_component":
                        continue

                    cls = entry.get("class_name", "")
                    if not cls:
                        continue

                    # Skip external packages and Creator classes
                    if "Creator" in cls or is_external_package(cls):
                        continue

                    edges.append(Edge(
                        kind="di_component",
                        from_qname=f"config::{dicon_file}",
                        to_qname=cls,
                        file=dicon_file,
                        line=entry.get("line", 0),
                    ))

        return [e.to_dict() for e in edges]


# Register the plugin
register(DiconComponentCrossFilePlugin)
