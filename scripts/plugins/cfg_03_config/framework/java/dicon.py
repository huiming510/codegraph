"""S2Container Dicon plugin.

Parses .dicon files (SAStruts/S2Framework dependency injection configuration).
"""

import xml.etree.ElementTree as ET
from pathlib import Path

from . import register
from .base import JavaConfigEntry, JavaConfigPlugin, JavaConfigResult


class DiconPlugin(JavaConfigPlugin):
    """Plugin for parsing .dicon (S2Container) dependency injection configuration files."""

    @property
    def name(self) -> str:
        return "dicon"

    @property
    def description(self) -> str:
        return "S2Container DI configuration (.dicon files)"

    @property
    def config_type(self) -> str:
        return "dicon"

    @property
    def file_patterns(self) -> list[str]:
        return ["*.dicon"]

    @property
    def priority(self) -> int:
        return 100

    def parse(self, file_path: Path) -> JavaConfigResult:
        """Parse .dicon files and extract component definitions."""
        try:
            raw = file_path.read_text(encoding="utf-8", errors="replace")
            root = ET.fromstring(raw)
        except Exception as e:
            return JavaConfigResult(
                file=str(file_path),
                config_type=self.config_type,
                parse_error=True,
                error_msg=str(e),
            )

        entries = []

        for comp in root.iter():
            tn = comp.tag

            # Component definitions
            if tn == "component" or (tn.endswith("}component")):
                cls = ""
                instance = ""
                for k, v in comp.attrib.items():
                    if k.endswith("}class") or k == "class":
                        cls = v or ""
                    elif k.endswith("}instance") or k == "instance":
                        instance = v or ""

                # Get child init-prop values
                props = {}
                for child in comp:
                    ctn = child.tag
                    if ctn == "property" or ctn.endswith("}property"):
                        pname = child.get("name") or child.get("property") or ""
                        pval = (child.text or "").strip() if child.text else ""
                        if pname:
                            props[pname] = pval

                if cls:
                    entries.append(JavaConfigEntry(
                        entry_type="dicon_component",
                        name=instance or cls,
                        class_name=cls,
                        file=str(file_path),
                        line=comp.sourceline if hasattr(comp, "sourceline") else 0,
                        attrs={"instance": instance},
                        properties=props,
                    ))

            # Include directives
            elif tn == "include" or (tn.endswith("}include")):
                incl = comp.get("path") or ""
                entries.append(JavaConfigEntry(
                    entry_type="dicon_include",
                    name=incl,
                    file=str(file_path),
                    line=comp.sourceline if hasattr(comp, "sourceline") else 0,
                    attrs={"path": incl},
                ))

        return JavaConfigResult(
            file=str(file_path),
            config_type=self.config_type,
            entries=entries,
            parse_error=False,
        )


# Register the plugin
register(DiconPlugin)
