"""Struts framework plugin.

Parses struts-config.xml and generates framework-specific edges from Struts configuration.

This plugin handles:
- struts-config.xml action mappings and forwards
- form-beans from struts-config.xml
- @Execute and @ActionForm annotation recognition

Cross-domain edges (JSP → Java, template → code, etc.) are handled
by CrossEdgePlugins instead.
"""

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional

from ....cross_file.constants import is_external_package
from . import register
from .base import JavaConfigEntry, JavaConfigPlugin, JavaConfigResult


class StrutsConfigPlugin(JavaConfigPlugin):
    """Plugin for parsing struts-config.xml files."""

    @property
    def name(self) -> str:
        return "struts_config"

    @property
    def description(self) -> str:
        return "Apache Struts configuration (struts-config.xml)"

    @property
    def config_type(self) -> str:
        return "struts_config"

    @property
    def file_patterns(self) -> list[str]:
        return ["struts-config.xml"]

    @property
    def priority(self) -> int:
        return 100

    def parse(self, file_path: Path) -> JavaConfigResult:
        """Parse struts-config.xml and extract action mappings, form beans, and forwards."""
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
        forward_map: dict[str, dict] = {}

        # Extract action mappings
        for action in root.iter():
            if action.tag.endswith("}action") or action.tag == "action":
                attrs = {k: (v or "") for k, v in action.attrib.items()}
                forwards = []
                for fwd in action:
                    fn = fwd.tag
                    if fn.endswith("}forward") or fn == "forward":
                        fwd_attrs = {k: (v or "") for k, v in fwd.attrib.items()}
                        forwards.append(fwd_attrs)
                        fwd_name = fwd_attrs.get("name", "")
                        fwd_path = fwd_attrs.get("path", "")
                        if fwd_name:
                            forward_map[fwd_name] = fwd_attrs

                action_name = attrs.get("name", "")
                action_path = attrs.get("path", "")
                entries.append(JavaConfigEntry(
                    entry_type="action_mapping",
                    name=action_name or action_path,
                    file=str(file_path),
                    line=action.sourceline if hasattr(action, "sourceline") else 0,
                    attrs=attrs,
                    forwards=forwards,
                ))

        # Extract form beans
        for fb in root.iter():
            if fb.tag.endswith("}form-bean") or fb.tag == "form-bean":
                attrs = {k: (v or "") for k, v in fb.attrib.items()}
                entries.append(JavaConfigEntry(
                    entry_type="form_bean",
                    name=attrs.get("name", ""),
                    class_name=attrs.get("type", ""),
                    file=str(file_path),
                    line=fb.sourceline if hasattr(fb, "sourceline") else 0,
                    attrs=attrs,
                ))

        # Extract global forwards
        for gf in root.iter():
            if gf.tag.endswith("}global-forwards") or gf.tag == "global-forwards":
                for fwd in gf:
                    if fwd.tag.endswith("}forward") or fwd.tag == "forward":
                        attrs = {k: (v or "") for k, v in fwd.attrib.items()}
                        entries.append(JavaConfigEntry(
                            entry_type="global_forward",
                            name=attrs.get("name", ""),
                            file=str(file_path),
                            line=fwd.sourceline if hasattr(fwd, "sourceline") else 0,
                            attrs=attrs,
                        ))
                        gname = attrs.get("name", "")
                        if gname:
                            forward_map[gname] = attrs

        return JavaConfigResult(
            file=str(file_path),
            config_type=self.config_type,
            entries=entries,
            parse_error=False,
            metadata={"_forward_map": forward_map},
        )


# ── Framework-specific edges ─────────────────────────────────────────────────────

class StrutsFrameworkEdges:
    """Generate framework-specific edges from Struts configuration.
    
    This is separated from the config plugin to allow different edge
    generation strategies while sharing the same config parsing.
    """

    @staticmethod
    def get_annotation_tags() -> dict[str, str]:
        """Framework annotation → domain tag mappings."""
        return {
            "@Execute": "struts.action",
            "@ActionForm": "struts.form",
        }

    @staticmethod
    def resolve_edges(
        xml_entries: list[dict],
        ui_data: Optional[dict] = None,
        ast_data: Optional[list[dict]] = None,
    ) -> list[dict]:
        """Generate framework-specific edges from struts-config.xml.
        
        Args:
            xml_entries: Parsed struts-config.xml entries
            ui_data: UI data dict for JSP filename mapping
            ast_data: AST data for @Execute return statement analysis
            
        Returns:
            List of edge dicts
        """
        edges = []

        for xml_entry in xml_entries:
            xml_path = str(xml_entry.get("file", ""))

            # Action routes and forwards
            for action_map in xml_entry.get("action_mappings", []):
                attrs = action_map.get("attrs", {})
                path = attrs.get("path", "")
                type_cls = attrs.get("type", "")

                if path and type_cls:
                    # Skip external packages
                    if not is_external_package(type_cls):
                        edges.append({
                            "kind": "action_route",
                            "from_qname": type_cls,
                            "to_qname": f"url::{path}",
                            "file": xml_path,
                            "line": action_map.get("line", 0),
                        })

                    # Forward routes
                    for fwd in action_map.get("forwards", []):
                        fwd_path = fwd.get("path", "")
                        if fwd_path:
                            if fwd_path.endswith(".jsp"):
                                fwd_path = fwd_path.lstrip("/")
                                to_qname = f"file::{fwd_path}"
                            else:
                                to_qname = f"url::{fwd_path}"

                            edges.append({
                                "kind": "forward_route",
                                "from_qname": type_cls,
                                "to_qname": to_qname,
                                "file": xml_path,
                                "line": action_map.get("line", 0),
                            })

            # Global forwards
            for gfwd in xml_entry.get("global_forwards", []):
                attrs = gfwd.get("attrs", {})
                gname = attrs.get("name", "")
                gpath = attrs.get("path", "")
                if gname and gpath:
                    if gpath.endswith(".jsp"):
                        gpath = gpath.lstrip("/")
                        to_qname = f"file::{gpath}"
                    else:
                        to_qname = f"url::{gpath}"

                    edges.append({
                        "kind": "forward_route",
                        "from_qname": f"forward::{gname}",
                        "to_qname": to_qname,
                        "file": xml_path,
                        "line": gfwd.get("line", 0),
                    })

            # Form beans from struts-config.xml
            for fb in xml_entry.get("form_beans", []):
                attrs = fb.get("attrs", {})
                fname = attrs.get("name", "")
                fcls = attrs.get("type", "")
                if fname and fcls and not is_external_package(fcls):
                    edges.append({
                        "kind": "form_bound",
                        "from_qname": f"formbean::{fname}",
                        "to_qname": fcls,
                        "file": xml_path,
                        "line": fb.get("line", 0),
                    })

        return edges


# Register the config plugin
register(StrutsConfigPlugin)
