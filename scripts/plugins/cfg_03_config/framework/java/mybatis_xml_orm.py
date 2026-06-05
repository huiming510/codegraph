"""MyBatis XML Mapper plugin.

Parses MyBatis XML Mapper files (*Mapper.xml) and extracts:
- <resultMap> definitions: property → column mappings for a Java entity type
- <select>/<insert>/<update>/<delete> SQL statements

The parsed result_map entries flow to MyBatisOrmCrossFilePlugin for cross-domain
sql_mapping edge generation (field → db::table.column).
"""

import xml.etree.ElementTree as ET
from pathlib import Path

from . import register
from .base import JavaConfigEntry, JavaConfigPlugin, JavaConfigResult


class MyBatisXmlOrmPlugin(JavaConfigPlugin):
    """Plugin for parsing MyBatis XML Mapper files."""

    @property
    def name(self) -> str:
        return "mybatis_xml_orm"

    @property
    def description(self) -> str:
        return "MyBatis XML Mapper files (*Mapper.xml)"

    @property
    def config_type(self) -> str:
        return "mybatis_xml"

    @property
    def file_patterns(self) -> list[str]:
        return ["*.xml"]

    @property
    def priority(self) -> int:
        return 50  # lower than web_xml (100) but we need to match .xml in mapper/ dirs

    def supports_file(self, file_path: Path) -> bool:
        if not file_path.match("*.xml"):
            return False
        fp = str(file_path).lower()
        return (
            "/mapper/" in fp
            or "\\mapper\\" in fp
            or fp.endswith("mapper.xml")
            or "_mapper.xml" in fp
            or "-mapper.xml" in fp
        )

    def parse(self, file_path: Path) -> JavaConfigResult:
        """Parse a MyBatis XML Mapper file."""
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

        ns = root.tag.split("}")[0].lstrip("{") if "}" in root.tag else ""

        def tag(local: str) -> str:
            return f"{{{ns}}}{local}" if ns else local

        mapper_namespace = root.attrib.get("namespace", "")

        for child in root:
            tn = child.tag

            if tn == tag("resultMap") or tn == "resultMap":
                entries.extend(self._parse_result_map(child, mapper_namespace, file_path))

            elif tn in (tag("select"), tag("insert"), tag("insert"),
                       tag("update"), tag("delete"),
                       "select", "insert", "update", "delete"):
                stmt_id = child.attrib.get("id", "")
                if stmt_id:
                    entries.append(JavaConfigEntry(
                        entry_type="sql_statement",
                        name=stmt_id,
                        class_name=mapper_namespace,
                        file=str(file_path),
                        line=child.sourceline if hasattr(child, "sourceline") else 0,
                        attrs={
                            "statement_type": tn,
                            "namespace": mapper_namespace,
                            "result_map_id": child.attrib.get("resultMap", ""),
                        },
                    ))

        return JavaConfigResult(
            file=str(file_path),
            config_type=self.config_type,
            entries=entries,
            parse_error=False,
        )

    def _parse_result_map(
        self, result_map_el: ET.Element, namespace: str, file_path: Path
    ) -> list[JavaConfigEntry]:
        """Extract all property→column mappings from a <resultMap> element."""
        entries = []
        result_map_id = result_map_el.attrib.get("id", "")
        java_type = result_map_el.attrib.get("type", "")

        line = result_map_el.sourceline if hasattr(result_map_el, "sourceline") else 0

        if not java_type:
            return entries

        for child in result_map_el:
            tn = child.tag
            if tn not in ("id", "result", "association", "collection"):
                continue
            if tn == "association" or tn == "collection":
                nested_type = child.attrib.get("javaType", child.attrib.get("ofType", ""))
                entries.append(JavaConfigEntry(
                    entry_type="result_map",
                    name=result_map_id,
                    class_name=java_type,
                    file=str(file_path),
                    line=line,
                    attrs={
                        "property": child.attrib.get("property", ""),
                        "column": child.attrib.get("column", ""),
                        "nested_type": nested_type,
                        "mapping_type": tn,
                    },
                ))
                nested_entries = self._parse_association(child, file_path)
                entries.extend(nested_entries)
                continue

            property_name = child.attrib.get("property", "")
            column_name = child.attrib.get("column", "")

            if not property_name:
                continue

            entries.append(JavaConfigEntry(
                entry_type="result_map",
                name=result_map_id,
                class_name=java_type,
                file=str(file_path),
                line=line,
                attrs={
                    "property": property_name,
                    "column": column_name,
                    "mapping_type": tn,
                    "namespace": namespace,
                },
            ))

        return entries

    def _parse_association(
        self, assoc_el: ET.Element, file_path: Path
    ) -> list[JavaConfigEntry]:
        """Recursively parse nested association/collection elements."""
        entries = []
        for child in assoc_el:
            tn = child.tag
            if tn not in ("id", "result"):
                continue
            property_name = child.attrib.get("property", "")
            column_name = child.attrib.get("column", "")
            if not property_name:
                continue
            entries.append(JavaConfigEntry(
                entry_type="result_map",
                name="nested",
                class_name=assoc_el.attrib.get("javaType", assoc_el.attrib.get("ofType", "")),
                file=str(file_path),
                line=child.sourceline if hasattr(child, "sourceline") else 0,
                attrs={
                    "property": property_name,
                    "column": column_name,
                    "mapping_type": tn,
                },
            ))
        return entries


register(MyBatisXmlOrmPlugin)
