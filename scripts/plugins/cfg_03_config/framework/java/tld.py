"""TLD (Tag Library Descriptor) plugin.

Parses .tld files to extract custom tag definitions.
"""

import xml.etree.ElementTree as ET
from pathlib import Path

from . import register
from .base import JavaConfigEntry, JavaConfigPlugin, JavaConfigResult


class TldPlugin(JavaConfigPlugin):
    """Plugin for parsing TLD (Tag Library Descriptor) files."""

    @property
    def name(self) -> str:
        return "tld"

    @property
    def description(self) -> str:
        return "TLD (Tag Library Descriptor) files for custom JSP tags"

    @property
    def config_type(self) -> str:
        return "tld"

    @property
    def file_patterns(self) -> list[str]:
        return ["*.tld"]

    @property
    def priority(self) -> int:
        return 100

    def parse(self, file_path: Path) -> JavaConfigResult:
        """Parse a .tld file and extract tag entries."""
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

        # Read short-name and uri from TLD header for correct prefix
        short_name = ""
        uri = ""
        for child in root:
            tn = child.tag
            if tn.endswith("}short-name") or tn == "short-name":
                short_name = (child.text or "").strip()
            elif tn.endswith("}uri") or tn == "uri":
                uri = (child.text or "").strip()

        entries = []
        for tag in root.iter():
            if tag.tag in ("tag", "tag-file") or (tag.tag.endswith("}tag")):
                name = ""
                cls = ""
                body = "empty"
                for child in tag:
                    tn = child.tag
                    if tn in ("name", "tag-name") or tn.endswith("}name"):
                        name = (child.text or "").strip()
                    elif tn in ("tagclass", "tag-class", "teiclass") or tn.endswith("}tagclass") or tn.endswith("}tag-class"):
                        cls = (child.text or "").strip()
                    elif tn in ("body-content", "bodycontent") or tn.endswith("}body-content"):
                        body = (child.text or "").strip().lower()
                        if not body:
                            body = "empty"

                if name and cls:
                    # Use short-name from TLD header as prefix (authoritative)
                    full_name = f"{short_name}:{name}" if short_name else name
                    entries.append(JavaConfigEntry(
                        entry_type="tld_tag",
                        name=full_name,
                        class_name=cls,
                        file=str(file_path),
                        line=tag.sourceline if hasattr(tag, "sourceline") else 0,
                        attrs={"uri": uri, "short_name": short_name},
                        body_content=body,
                    ))

        return JavaConfigResult(
            file=str(file_path),
            config_type=self.config_type,
            entries=entries,
            parse_error=False,
            metadata={"uri": uri, "short_name": short_name},
        )


# Register the plugin
register(TldPlugin)
