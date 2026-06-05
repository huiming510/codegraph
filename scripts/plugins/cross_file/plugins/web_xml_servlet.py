"""Web.xml servlet configuration cross-file plugin.

Generates edges from web.xml servlet and filter definitions to Java classes,
and from JSP files to common JSPs via jsp-property-group include-prelude/coda.
"""

import fnmatch
from pathlib import Path

from ...common.base import Edge
from ..base import CrossFilePlugin
from ..constants import is_external_package, EXTERNAL_PACKAGES
from ..registry import register


def _jsp_url_matches_pattern(file_path: str, pattern: str) -> bool:
    """Check if a JSP file path matches a URL pattern like '*.jsp'."""
    if not pattern:
        return False
    # Convert URL pattern to glob pattern: *.jsp -> *.jsp
    # Strip leading slash if present
    glob_pattern = pattern.lstrip("/")
    # Use fnmatch for simple patterns like *.jsp
    filename = Path(file_path).name
    return fnmatch.fnmatch(filename, glob_pattern)


class WebXmlServletCrossFilePlugin(CrossFilePlugin):
    """Cross-file plugin for web.xml servlet/filter definitions → Java classes."""

    @property
    def name(self) -> str:
        return "web_xml_servlet"

    @property
    def description(self) -> str:
        return "web.xml servlet/filter definitions → Java class bindings"

    @property
    def supported_langs(self) -> list[str]:
        return ["java"]

    def can_produce(self, context, lang: str = None) -> bool:
        """Check if we have web.xml data.

        Note: context.ui_data may be empty in the unified pipeline.
        Always return True and let produce() handle missing data.
        """
        return True

    def produce(self, context, lang: str = None, elements: dict = None) -> list[dict]:
        """Generate web.xml cross-file edges."""
        edges = []

        # Build lookup for servlet definitions
        servlet_defs = {}  # name -> class_name
        filter_defs = {}  # name -> class_name
        servlet_mappings = []  # (servlet_name, url_pattern)
        filter_mappings = []  # (filter_name, url_pattern, servlet_name)
        jsp_property_groups = []  # (url_pattern, [include_paths], file)

        # Find web.xml entries
        if elements is None:
            return []
        for entry in (elements or {}).get("xml", []):
            if entry.get("config_type") != "web_xml":
                continue
            if entry.get("parse_error"):
                continue

            for e in entry.get("entries", []):
                entry_type = e.get("entry_type", "")
                attrs = e.get("attrs", {})

                if entry_type == "servlet_def":
                    servlet_defs[e.get("name", "")] = e.get("class_name", "")

                elif entry_type == "filter_def":
                    filter_defs[e.get("name", "")] = e.get("class_name", "")

                elif entry_type == "servlet_mapping":
                    servlet_mappings.append((
                        attrs.get("servlet_name", ""),
                        attrs.get("url_pattern", "")
                    ))

                elif entry_type == "filter_mapping":
                    filter_mappings.append((
                        attrs.get("filter_name", ""),
                        attrs.get("url_pattern", ""),
                        attrs.get("servlet_name", "")
                    ))

                elif entry_type == "jsp_property_group":
                    jsp_property_groups.append((
                        attrs.get("url_pattern", ""),
                        attrs.get("includes", []),
                        entry.get("file", ""),
                    ))

        # Generate edges from servlet definitions
        for servlet_name, servlet_class in servlet_defs.items():
            if not servlet_class:
                continue

            # servlet_def → servlet class
            to_qname = f"ext::{servlet_class}" if is_external_package(servlet_class) else servlet_class
            edges.append(Edge(
                kind="servlet_def",
                from_qname=f"servlet::{servlet_name}",
                to_qname=to_qname,
                file=entry.get("file", ""),
                line=0,
            ))

            # Find URL patterns for this servlet
            for servlet_name_in_mapping, url_pattern in servlet_mappings:
                if servlet_name_in_mapping == servlet_name and url_pattern:
                    edges.append(Edge(
                        kind="servlet_bound",
                        from_qname=f"servlet::{servlet_name}",
                        to_qname=f"url::{url_pattern}",
                        file=entry.get("file", ""),
                        line=0,
                    ))

        # Generate edges from filter definitions
        for filter_name, filter_class in filter_defs.items():
            if not filter_class:
                continue

            # filter_def → filter class
            to_qname = f"ext::{filter_class}" if is_external_package(filter_class) else filter_class
            edges.append(Edge(
                kind="filter_def",
                from_qname=f"filter::{filter_name}",
                to_qname=to_qname,
                file=entry.get("file", ""),
                line=0,
            ))

            # Find mappings for this filter
            for filter_name_in_mapping, url_pattern, servlet_name in filter_mappings:
                if filter_name_in_mapping == filter_name:
                    if url_pattern:
                        edges.append(Edge(
                            kind="filter_chain",
                            from_qname=f"filter::{filter_name}",
                            to_qname=f"url::{url_pattern}",
                            file=entry.get("file", ""),
                            line=0,
                        ))
                    if servlet_name:
                        edges.append(Edge(
                            kind="filter_chain",
                            from_qname=f"filter::{filter_name}",
                            to_qname=f"servlet::{servlet_name}",
                            file=entry.get("file", ""),
                            line=0,
                        ))

        # ── JSP property groups: include-prelude / include-coda → includes edges ──
        # JSP files are in elements["templates"], NOT in context.symbols (which is Java-only).
        # Build lookup from templates.
        jsp_files: dict[str, str] = {}  # absolute_lower_path -> qname (template::{abs_path})
        for template in (elements or {}).get("templates", []):
            tfile = template.get("file", "")
            if tfile.lower().endswith((".jsp", ".jspf", ".jspx")):
                jsp_files[tfile.lower()] = f"template::{tfile}"

        # Find web.xml path to resolve relative include paths
        web_xml_path: str | None = None
        for entry in (elements or {}).get("xml", []):
            if entry.get("config_type") == "web_xml":
                web_xml_path = entry.get("file", "")
                break

        if not web_xml_path or not jsp_files:
            return [e.to_dict() for e in edges]

        web_xml_dir = Path(web_xml_path).parent  # WEB-INF/
        webapp_dir = web_xml_dir.parent  # webapp/

        for url_pattern, includes, _ in jsp_property_groups:
            if not includes:
                continue
            for lower_path, jsp_qname in jsp_files.items():
                if _jsp_url_matches_pattern(lower_path, url_pattern):
                    for include_rel in includes:
                        # Resolve include path relative to webapp root
                        inc_path = str((webapp_dir / include_rel.lstrip("/")).resolve())
                        inc_qname = f"template::{inc_path}"
                        edges.append(Edge(
                            kind="includes",
                            from_qname=jsp_qname,
                            to_qname=inc_qname,
                            file=web_xml_path,
                            line=0,
                        ))

        return [e.to_dict() for e in edges]


# Register the plugin
register(WebXmlServletCrossFilePlugin)
