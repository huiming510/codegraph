"""TLD (Tag Library Descriptor) handler cross-file plugin.

Generates edges from TLD tag definitions to their handler classes.
"""

from pathlib import Path

from ...common.base import Edge
from ..base import CrossFilePlugin
from ..constants import is_external_package
from ..registry import register


class TldHandlerCrossFilePlugin(CrossFilePlugin):
    """Cross-file plugin for TLD tag definitions → Java handler bindings."""
    
    @property
    def name(self) -> str:
        return "tld_handler"
    
    @property
    def description(self) -> str:
        return "TLD tag definitions → Java handler class bindings"
    
    @property
    def supported_langs(self) -> list[str]:
        return ["java"]
    
    def can_produce(self, context, lang: str = None) -> bool:
        """Check if we have TLD data in the correct format."""
        # Check both old nested format (from JavaConfig) and new flat format
        tld_data = context.ui_data.get("tld", [])
        if tld_data:
            # Check if it's the new flat format
            if isinstance(tld_data[0], dict) and "name" in tld_data[0] and "handler_class" in tld_data[0]:
                return True
            # Check if it's the nested format from JavaConfig
            if isinstance(tld_data[0], dict) and "entries" in tld_data[0]:
                return True
        return False
    
    def produce(self, context, lang: str = None, elements: dict = None) -> list[dict]:
        """Generate TLD cross-file edges."""
        edges = []

        tld_data = (elements or {}).get("tld", [])

        # Support both formats:
        # 1. New flat format: [{name, handler_class, line, ...}]
        # 2. Nested format from JavaConfig: [{file, entries: [{name, class_name, ...}], ...}]

        if tld_data and "entries" in tld_data[0]:
            # Nested format from JavaConfig
            for entry in tld_data:
                if entry.get("error"):
                    continue

                tld_file = str(entry.get("file", ""))

                for tag_entry in entry.get("entries", []):
                    tag_name = tag_entry.get("name", "")
                    handler = tag_entry.get("class_name", "")  # class_name in JavaConfig format
                    line = tag_entry.get("line", 0)

                    if not tag_name:
                        continue

                    # Tag → TLD file
                    edges.append(Edge(
                        kind="defined_in",
                        from_qname=f"tag::{tag_name}",
                        to_qname=f"config::{tld_file}",
                        file=tld_file,
                        line=line,
                    ))

                    # Tag → Handler class
                    if handler:
                        to_qname = f"ext::{handler}" if is_external_package(handler) else handler

                        edges.append(Edge(
                            kind="bound_to",
                            from_qname=f"tag::{tag_name}",
                            to_qname=to_qname,
                            file=tld_file,
                            line=line,
                        ))
        else:
            # New flat format
            for entry in tld_data:
                if entry.get("error"):
                    continue

                tld_file = str(entry.get("file", ""))
                tag_name = entry.get("name", "")
                handler = entry.get("handler_class", "")
                line = entry.get("line", 0)

                if not tld_file or not tag_name:
                    continue

                # Tag → TLD file
                edges.append(Edge(
                    kind="defined_in",
                    from_qname=f"tag::{tag_name}",
                    to_qname=f"config::{tld_file}",
                    file=tld_file,
                    line=line,
                ))

                # Tag → Handler class
                if handler:
                    to_qname = f"ext::{handler}" if is_external_package(handler) else handler

                    edges.append(Edge(
                        kind="bound_to",
                        from_qname=f"tag::{tag_name}",
                        to_qname=to_qname,
                        file=tld_file,
                        line=line,
                    ))

        return [e.to_dict() for e in edges]


# Register the plugin
register(TldHandlerCrossFilePlugin)
