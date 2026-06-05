"""Web XML configuration plugin.

Parses web.xml to extract servlet definitions, filter definitions, and context parameters.
"""

import xml.etree.ElementTree as ET
from pathlib import Path

from . import register
from .base import JavaConfigEntry, JavaConfigPlugin, JavaConfigResult


class WebXmlPlugin(JavaConfigPlugin):
    """Plugin for parsing web.xml files."""

    @property
    def name(self) -> str:
        return "web_xml"

    @property
    def description(self) -> str:
        return "Java EE Web Application Descriptor (web.xml)"

    @property
    def config_type(self) -> str:
        return "web_xml"

    @property
    def file_patterns(self) -> list[str]:
        return ["web.xml"]

    @property
    def priority(self) -> int:
        return 100

    def parse(self, file_path: Path) -> JavaConfigResult:
        """Parse web.xml and extract servlet/filter definitions and mappings."""
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

        # Extract default namespace from root element
        ns = root.tag.split("}")[0].lstrip("{") if "}" in root.tag else ""

        def _tag(local: str) -> str:
            return f"{{{ns}}}{local}" if ns else local

        def _findtext(el: ET.Element, local: str) -> str:
            """Find direct child text, namespace-aware."""
            child = el.find(_tag(local))
            return (child.text or "").strip() if child is not None else ""

        for child in root:
            tn = child.tag

            # Servlet definitions
            if tn == _tag("servlet") or tn == "servlet":
                sname = _findtext(child, "servlet-name")
                sclass = _findtext(child, "servlet-class")
                if sname:
                    entries.append(JavaConfigEntry(
                        entry_type="servlet_def",
                        name=sname,
                        class_name=sclass,
                        file=str(file_path),
                        line=child.sourceline if hasattr(child, "sourceline") else 0,
                        attrs={"class": sclass},
                    ))

            # Filter definitions
            elif tn == _tag("filter") or tn == "filter":
                fname = _findtext(child, "filter-name")
                fclass = _findtext(child, "filter-class")
                if fname:
                    entries.append(JavaConfigEntry(
                        entry_type="filter_def",
                        name=fname,
                        class_name=fclass,
                        file=str(file_path),
                        line=child.sourceline if hasattr(child, "sourceline") else 0,
                        attrs={"class": fclass},
                    ))

            # Servlet mappings
            elif tn == _tag("servlet-mapping") or tn == "servlet-mapping":
                servlet_name = _findtext(child, "servlet-name")
                url_pattern = _findtext(child, "url-pattern")
                entries.append(JavaConfigEntry(
                    entry_type="servlet_mapping",
                    name=url_pattern,
                    file=str(file_path),
                    line=child.sourceline if hasattr(child, "sourceline") else 0,
                    attrs={"servlet_name": servlet_name, "url_pattern": url_pattern},
                ))

            # Filter mappings
            elif tn == _tag("filter-mapping") or tn == "filter-mapping":
                filter_name = _findtext(child, "filter-name")
                url_pattern = _findtext(child, "url-pattern")
                servlet_name = _findtext(child, "servlet-name")
                entries.append(JavaConfigEntry(
                    entry_type="filter_mapping",
                    name=filter_name,
                    file=str(file_path),
                    line=child.sourceline if hasattr(child, "sourceline") else 0,
                    attrs={
                        "filter_name": filter_name,
                        "url_pattern": url_pattern,
                        "servlet_name": servlet_name,
                    },
                ))

            # JSP config: jsp-property-group (include-prelude / include-coda)
            elif tn == _tag("jsp-config") or tn == "jsp-config":
                for jsp_group in child:
                    group_tn = jsp_group.tag
                    if group_tn != _tag("jsp-property-group") and group_tn != "jsp-property-group":
                        continue
                    url_pattern = _findtext(jsp_group, "url-pattern")
                    includes: list[str] = []
                    for prelude in jsp_group.findall(_tag("include-prelude")):
                        text = (prelude.text or "").strip()
                        if text:
                            includes.append(text)
                    for coda in jsp_group.findall(_tag("include-coda")):
                        text = (coda.text or "").strip()
                        if text:
                            includes.append(text)
                    if url_pattern and includes:
                        entries.append(JavaConfigEntry(
                            entry_type="jsp_property_group",
                            name=url_pattern,
                            file=str(file_path),
                            line=jsp_group.sourceline if hasattr(jsp_group, "sourceline") else 0,
                            attrs={"url_pattern": url_pattern, "includes": includes},
                        ))

            # Context parameters
            elif tn == _tag("context-param") or tn == "context-param":
                param_name = _findtext(child, "param-name")
                param_value = _findtext(child, "param-value")
                entries.append(JavaConfigEntry(
                    entry_type="context_param",
                    name=param_name,
                    file=str(file_path),
                    line=child.sourceline if hasattr(child, "sourceline") else 0,
                    attrs={"value": param_value},
                ))

        return JavaConfigResult(
            file=str(file_path),
            config_type=self.config_type,
            entries=entries,
            parse_error=False,
        )


# Register the plugin
register(WebXmlPlugin)
