"""MyBatis ORM SQL Mapping Plugin.

Generates cross-file edges from Java entity fields to database columns
by parsing MyBatis mapper annotations (@Result, @Results) and XML mapper files.

Supported mapping patterns:
  - @Result(column="user_id", property="userId")
  - @Select("SELECT F.user_id AS followUserId ...")
  - MyBatis XML <result property="userId" column="user_id"/>

Edge: Java field -> DB column (kind="sql_mapping")
"""

import re
from pathlib import Path
from typing import Optional

from ...common.base import Edge
from ..base import CrossFilePlugin
from ..constants import EXTERNAL_PACKAGES
from ..registry import register


def _db_col(table: str, column: str) -> str:
    return f"db::{table}.{column}"


def _java_field(class_qname: str, field_name: str) -> str:
    return f"{class_qname}.{field_name}"


def _get_text(node: dict) -> str:
    if "text" in node:
        return node["text"]
    return "".join(_get_text(c) for c in node.get("children", []))


def _get_annotation_name(ann_node: dict) -> str:
    """Extract annotation name from AST node."""
    parts = []
    for c in ann_node.get("children", []):
        ct = c.get("type", "")
        if ct in ("identifier", "type_identifier", "scoped_identifier"):
            parts.append(c.get("text", ""))
    return "".join(parts)


def _get_annotation_arg(ann_node: dict, key: str) -> Optional[str]:
    """Extract @Annotation(key = "value") argument by key.

    Tree-sitter structure for element_value_pair:
        [identifier("column"), "=", string_literal("user_id")]
    So the value is at index 2 (not 1, which is the '=' sign).
    """
    for c in ann_node.get("children", []):
        if c.get("type") != "annotation_argument_list":
            continue
        for arg in c.get("children", []):
            at = arg.get("type", "")
            if at not in ("element_value_pair",):
                continue
            kv = arg.get("children", [])
            if len(kv) < 3:
                continue
            k_text = _get_text(kv[0]).strip()
            if k_text != key:
                continue
            # Value is at index 2 (index 1 is the '=' sign)
            v_node = kv[2]
            if v_node.get("type") == "string_literal":
                frags = [fc.get("text", "") for fc in v_node.get("children", [])
                          if fc.get("type") in ("string_fragment", "Text", "string_literal")]
                return "".join(frags).strip('"')
            return _get_text(v_node).strip().strip('"')
    return None


def _parse_result_annotation(ann_node: dict) -> Optional[dict]:
    col = _get_annotation_arg(ann_node, "column") or ""
    prop = _get_annotation_arg(ann_node, "property") or ""
    table = _get_annotation_arg(ann_node, "table") or ""
    if col and prop:
        line = ann_node.get("start", [1])[0] if ann_node.get("start") else 1
        return {"column": col, "property": prop, "table": table, "line": line}
    return None


class MyBatisOrmPlugin(CrossFilePlugin):

    @property
    def name(self) -> str:
        return "mybatis_orm"

    @property
    def description(self) -> str:
        return "MyBatis @Result / XML mapper -> Java entity field -> SQL column mapping"

    @property
    def supported_langs(self) -> list[str]:
        return ["java"]

    def can_produce(self, context, lang: str = None) -> bool:
        if lang and lang != "java":
            return False
        return True

    def produce(self, context, lang: str = None, elements: dict = None) -> list[dict]:
        edges = []

        # Load AST data if not in context (--all pipeline doesn't pass it)
        ast_by_file = {e["file"]: e["ast"] for e in context.ast_data}
        if not ast_by_file:
            ast_by_file = self._load_ast_from_files(context)

        entity_classes = self._find_entity_classes(context)
        class_fields = self._build_class_field_map(context, entity_classes)
        mapper_files = self._find_mapper_interfaces(context)

        # ── Java annotation-based mapper edges ──────────────────────────────────
        for mapper_fp, mapper_qname in mapper_files.items():
            ast = ast_by_file.get(mapper_fp)
            if not ast:
                continue

            method_mappings = self._parse_mapper_ast(ast)
            for m in method_mappings:
                results = m.get("results", [])
                sql_text = m.get("sql_text", "")

                if not results and sql_text:
                    results = self._extract_aliases_from_sql(sql_text)

                for r in results:
                    col = r.get("column", "")
                    prop = r.get("property", "")
                    if not col or not prop:
                        continue

                    java_fqname = self._resolve_property_to_field(
                        prop, entity_classes, class_fields, context
                    )
                    if not java_fqname:
                        continue

                    table_hint = r.get("table", "")
                    db_col_qname = self._resolve_column(col, table_hint, sql_text)

                    edge = Edge(
                        kind="sql_mapping",
                        from_qname=java_fqname,
                        to_qname=db_col_qname,
                        file=mapper_fp,
                        line=r.get("line", m.get("line", 1)),
                    )
                    edges.append(edge)

        # ── XML mapper edges (from mybatis_xml_orm plugin) ───────────────────────
        # Add XML resultMap java types to entity_classes BEFORE building class_fields
        entity_classes = self._add_xml_entity_types(elements, entity_classes)
        # Rebuild class_fields after adding XML types so their fields are included
        class_fields = self._build_class_field_map(context, entity_classes)
        xml_edges = self._process_xml_mappers(context, elements, entity_classes, class_fields)
        edges.extend(xml_edges)

        return [e.to_dict() for e in edges]

    def _add_xml_entity_types(self, elements: dict, entity_classes: dict) -> dict:
        """Add Java entity types from XML <resultMap type="..."> to entity_classes."""
        if not elements:
            return entity_classes
        result_maps_list = elements.get("result_maps", [])
        for rm_group in result_maps_list:
            for entry in rm_group.get("entries", []):
                if entry.get("entry_type") != "result_map":
                    continue
                attrs = entry.get("attrs", {})
                nested_attrs = attrs.get("attrs", {})
                java_type = entry.get("java_type", "") or attrs.get("class_name", "")
                if not java_type:
                    continue
                if java_type not in entity_classes:
                    entity_classes[java_type] = java_type
        return entity_classes

    def _process_xml_mappers(
        self, context, elements: dict, entity_classes: dict, class_fields: dict
    ) -> list[Edge]:
        """Generate sql_mapping edges from XML Mapper result_map entries."""
        edges = []
        if not elements:
            return edges

        result_maps_list = elements.get("result_maps", [])
        if not result_maps_list:
            return edges

        for rm_group in result_maps_list:
            for entry in rm_group.get("entries", []):
                if entry.get("entry_type") != "result_map":
                    continue

                attrs = entry.get("attrs", {})
                # attrs has nested structure: { class_name, file, attrs: { property, column, ... } }
                nested_attrs = attrs.get("attrs", {})

                prop = nested_attrs.get("property", "")
                col = nested_attrs.get("column", "")
                if not prop or not col:
                    continue

                java_type = entry.get("java_type", "")
                if not java_type:
                    java_type = attrs.get("class_name", "")

                java_fqname = self._resolve_property_to_field(
                    prop, entity_classes, class_fields, context
                )
                if not java_fqname:
                    continue

                # Use the file from the outer attrs (original entry)
                entry_file = attrs.get("file", entry.get("file", ""))

                db_col_qname = self._resolve_column(col, "", "")

                edge = Edge(
                    kind="sql_mapping",
                    from_qname=java_fqname,
                    to_qname=db_col_qname,
                    file=entry_file,
                    line=entry.get("line", 1),
                )
                edges.append(edge)

        return edges

    # ── Discovery ───────────────────────────────────────────────────────────────

    def _find_entity_classes(self, context) -> dict[str, str]:
        """Find entity classes by resolving mapper method return types.

        Strategy:
        1. Find all mapper methods (@Select/@Results/etc.) in @Mapper interfaces
        2. Get their type_hint (e.g., 'Article', 'ArticleFavorite', 'Set<Tag>')
        3. Resolve simple names to fully qualified names via class index
        4. Include domain data classes (ArticleData, UserData, etc.) directly
        """
        entities: dict[str, str] = {}

        # Index all classes by simple name and by qualified name
        all_classes: dict[str, dict] = {}
        all_simple: dict[str, dict] = {}
        for sym in context.symbols:
            if sym.get("kind") not in ("class", "interface"):
                continue
            qname = sym.get("qualified_name", "")
            if not qname or any(qname.startswith(p) for p in EXTERNAL_PACKAGES):
                continue
            all_classes[qname] = sym
            simple = sym.get("name", "")
            if simple:
                all_simple[simple] = sym

        # Find mapper methods and resolve their return types
        mapper_method_types: set[str] = set()
        for sym in context.symbols:
            if sym.get("kind") != "method":
                continue
            qname = sym.get("qualified_name", "")
            if not qname or any(qname.startswith(p) for p in EXTERNAL_PACKAGES):
                continue
            annotations = sym.get("annotations", [])
            is_mapper = any(a in annotations for a in (
                "@Select", "@Insert", "@Update", "@Delete", "@Results", "@Result"
            ))
            if not is_mapper:
                continue

            # Get return type hint
            type_hint = sym.get("type_hint", "")
            if not type_hint:
                continue

            # Handle generic types like Set<Tag> -> Tag, List<Article> -> Article
            clean_type = self._unwrap_generic(type_hint)

            # Try to resolve as qualified name first
            if clean_type in all_classes:
                entities[clean_type] = clean_type
                mapper_method_types.add(clean_type)
            elif clean_type in all_simple:
                fqname = all_simple[clean_type].get("qualified_name", "")
                if fqname:
                    entities[fqname] = fqname
                    mapper_method_types.add(fqname)

        return entities

    def _unwrap_generic(self, type_hint: str) -> str:
        """Strip generic parameters: 'Set<Tag>' -> 'Tag', 'List<Article>' -> 'Article'."""
        m = re.match(r"([A-Za-z_]\w*)", type_hint)
        if m:
            return m.group(1)
        return type_hint.split("<")[0]

    def _find_mapper_interfaces(self, context) -> dict[str, str]:
        """Find @Mapper interface files."""
        mappers: dict[str, str] = {}
        for sym in context.symbols:
            if sym.get("kind") != "interface":
                continue
            qname = sym.get("qualified_name", "")
            if not qname or any(qname.startswith(p) for p in EXTERNAL_PACKAGES):
                continue
            if "@Mapper" in sym.get("annotations", []):
                fp = sym.get("file", "")
                if fp:
                    mappers[fp] = qname
        return mappers

    def _build_class_field_map(
        self, context, entity_classes: dict[str, str]
    ) -> dict[str, set[str]]:
        """Build {fqname: {field_name, ...}} from field symbols.

        Two strategies:
        1. Standard: match by scope field (set by language plugins)
        2. Fallback: extract class name from field's qualified_name (e.g.
           "pkg.Article.id" → class="pkg.Article", field="id")
        """
        class_fields: dict[str, set[str]] = {}

        for sym in context.symbols:
            if sym.get("kind") != "field":
                continue

            scope = sym.get("scope", "")
            qname = sym.get("qualified_name", "")
            name = sym.get("name", "")

            matched_cls: Optional[str] = None

            if scope:
                matched_cls = self._match_scope_to_entity(scope, entity_classes)
            else:
                matched_cls = self._match_qname_to_entity(qname, name, entity_classes)

            if matched_cls:
                class_fields.setdefault(matched_cls, set()).add(name)

        return class_fields

    def _match_qname_to_entity(
        self, qname: str, field_name: str, entity_classes: dict[str, str]
    ) -> Optional[str]:
        """Match a field's qualified_name to an entity class.

        Field qname format: "pkg.Class.fieldName"
        We strip the last segment and check if it matches an entity class.
        """
        if not qname:
            return None
        parts = qname.rsplit(".", 1)
        if len(parts) != 2:
            return None
        class_part = parts[0]
        if class_part in entity_classes:
            return class_part
        return None

    def _match_scope_to_entity(
        self, scope: str, entity_classes: dict[str, str]
    ) -> Optional[str]:
        """Match a field's scope to an entity class qname."""
        if scope in entity_classes:
            return scope

        # Try progressively shorter scopes (for nested classes)
        # e.g., scope = "pkg.Outer.Inner", entities = {"pkg.Outer": ...}
        parts = scope.split(".")
        for i in range(len(parts) - 1, 0, -1):
            shorter = ".".join(parts[:i])
            if shorter in entity_classes:
                return shorter

        # Try by simple class name
        simple = scope.split(".")[-1]
        for eqname in entity_classes:
            if eqname.split(".")[-1] == simple:
                return eqname

        return None

    # ── AST Parsing ────────────────────────────────────────────────────────

    def _parse_mapper_ast(self, ast: dict) -> list[dict]:
        """Parse a mapper interface AST for @Results/@Result and SQL."""
        mappings: list[dict] = []

        def walk(node: dict) -> None:
            if node.get("type") == "method_declaration":
                self._parse_method_annotations(node, mappings)
            for c in node.get("children", []):
                walk(c)

        walk(ast)
        return mappings

    def _parse_method_annotations(
        self, method_node: dict, mappings: list[dict]
    ) -> None:
        """Extract @Results/@Result and @Select from a method's annotations.

        Annotations in interface methods are stored in the 'modifiers' child node.
        """
        line = method_node.get("start", [1])[0] if method_node.get("start") else 1
        method_name = ""
        for mc in method_node.get("children", []):
            if mc.get("type") == "identifier":
                method_name = mc.get("text", "")
                break

        results: list[dict] = []
        sql_text = ""

        # Collect annotations: may be direct children OR inside 'modifiers' node
        all_annotations: list[dict] = []
        for c in method_node.get("children", []):
            t = c.get("type", "")
            if t == "annotation":
                all_annotations.append(c)
            elif t == "modifiers":
                # Annotations are inside the modifiers node
                for mc in c.get("children", []):
                    if mc.get("type") == "annotation":
                        all_annotations.append(mc)

        for ann in all_annotations:
            ann_name = _get_annotation_name(ann)

            if ann_name == "Results":
                results.extend(self._parse_results_nested(ann))
            elif ann_name == "Result":
                r = _parse_result_annotation(ann)
                if r:
                    results.append(r)
            elif ann_name in ("Select", "Insert", "Update", "Delete"):
                sql_text = _get_annotation_arg(ann, "value") or ""

        if results or sql_text:
            mappings.append({
                "name": method_name,
                "line": line,
                "results": results,
                "sql_text": sql_text,
            })

    def _parse_results_nested(self, ann_node: dict) -> list[dict]:
        """Parse @Results(value={@Result, @Result}) — nested pattern."""
        results = []
        for c in ann_node.get("children", []):
            if c.get("type") != "annotation_argument_list":
                continue
            for arg in c.get("children", []):
                at = arg.get("type", "")
                if at == "element_value_pair":
                    kv = arg.get("children", [])
                    if len(kv) < 3:
                        continue
                    k_text = _get_text(kv[0]).strip()
                    if k_text == "value":
                        # value is at kv[2] (kv[1] is '=')
                        v_node = kv[2]
                        # May be element_value_array_initializer or annotation
                        for child in v_node.get("children", []):
                            if child.get("type") == "annotation":
                                r = _parse_result_annotation(child)
                                if r:
                                    results.append(r)
                elif at == "annotation":
                    r = _parse_result_annotation(arg)
                    if r:
                        results.append(r)
        return results

    def _extract_aliases_from_sql(self, sql: str) -> list[dict]:
        """Extract 'col AS alias' patterns."""
        results = []
        for m in re.finditer(r"\b([\w]+)\s+AS\s+([A-Za-z_][\w]*)\b", sql, re.IGNORECASE):
            col, alias = m.group(1), m.group(2)
            if self._is_sql_keyword(col):
                continue
            results.append({"column": col, "property": alias, "table": "", "line": 1})
        return results

    def _is_sql_keyword(self, word: str) -> bool:
        kw = {
            "SELECT", "FROM", "WHERE", "AND", "OR", "NOT", "IN", "IS", "NULL",
            "AS", "JOIN", "LEFT", "RIGHT", "INNER", "OUTER", "ON", "GROUP",
            "BY", "ORDER", "HAVING", "LIMIT", "OFFSET", "INSERT", "UPDATE",
            "DELETE", "SET", "VALUES", "INTO", "CREATE", "ALTER", "DROP",
            "TABLE", "INDEX", "VIEW", "UNION", "ALL", "DISTINCT", "EXISTS",
            "BETWEEN", "LIKE", "CASE", "WHEN", "THEN", "ELSE", "END",
            "COUNT", "SUM", "AVG", "MAX", "MIN", "ASC", "DESC",
        }
        return word.upper() in kw

    # ── Resolution ────────────────────────────────────────────────────────────

    def _resolve_property_to_field(
        self, prop: str, entity_classes: dict[str, str],
        class_fields: dict[str, set[str]], context
    ) -> Optional[str]:
        """Resolve a Java property name to a fully qualified field qname."""
        # 1. Direct match
        for cls_qname in entity_classes:
            if cls_qname in class_fields and prop in class_fields[cls_qname]:
                return _java_field(cls_qname, prop)

        # 2. camelCase <-> snake_case
        prop_snake = self._camel_to_snake(prop)
        prop_camel = self._snake_to_camel(prop)
        for cls_qname in entity_classes:
            if cls_qname not in class_fields:
                continue
            for field in class_fields[cls_qname]:
                if field in (prop, prop_snake, prop_camel):
                    return _java_field(cls_qname, field)
                if self._camel_to_snake(field) == prop_snake:
                    return _java_field(cls_qname, field)

        return None

    def _load_ast_from_files(self, context) -> dict[str, dict]:
        """Load AST data from source Java files using tree-sitter.

        Called when context.ast_data is empty (--all pipeline).
        We parse the source files directly to get @Result/@Results annotations.
        """
        import json
        import pathlib
        ast_by_file: dict[str, dict] = {}

        # Collect unique Java file paths from symbols
        java_files: list[str] = []
        project_root = None
        for sym in context.symbols:
            fp = sym.get("file", "")
            if fp and fp.endswith(".java"):
                java_files.append(fp)
                if project_root is None:
                    # Infer project root from file path.
                    # File paths are relative to the current working directory.
                    # e.g. "test-realworld/app-article/src/main/java/..." -> "test-realworld"
                    parts = pathlib.Path(fp).parts
                    for i, part in enumerate(parts):
                        if part in ("src", "app"):
                            project_root = str(pathlib.Path(*parts[:i]))
                            break

        if not java_files:
            return ast_by_file

        if project_root is None:
            # Fallback: use first two path segments as root
            fp0 = java_files[0]
            parts = pathlib.Path(fp0).parts
            if len(parts) >= 2:
                project_root = str(pathlib.Path(parts[0], parts[1]))

        from stage1_syntax import _build_node, _node_to_dict

        # Parse all Java files directly with tree-sitter
        errors = []
        try:
            from tree_sitter import Parser
            import tree_sitter_java as tsjava
            from tree_sitter import Language
            _LANG = Language(tsjava.language())
            _PARSER = Parser(_LANG)

            parsed_count = 0
            for fp in java_files:
                try:
                    src_path = pathlib.Path(fp)
                    if src_path.exists():
                        src_text = src_path.read_bytes()
                        tree = _PARSER.parse(src_text)
                        if tree and tree.root_node:
                            ast_by_file[fp] = _node_to_dict(_build_node(tree.root_node, src_text))
                            parsed_count += 1
                    else:
                        if project_root:
                            src_path2 = pathlib.Path(project_root) / fp
                            if src_path2.exists():
                                src_text = src_path2.read_bytes()
                                tree = _PARSER.parse(src_text)
                                if tree and tree.root_node:
                                    ast_by_file[fp] = _node_to_dict(_build_node(tree.root_node, src_text))
                                    parsed_count += 1
                except Exception as ex:
                    errors.append(f"{fp}: {ex}")
            if errors and parsed_count == 0:
                print(f"[mybatis_orm] AST parse errors: {errors[:3]}")
        except ImportError:
            print("[mybatis_orm] tree-sitter import failed")
            pass

        return ast_by_file

    def _resolve_column(self, col: str, table_hint: str, sql_text: str) -> str:
        if table_hint:
            return _db_col(table_hint, col)
        if sql_text:
            m = re.search(r"\bFROM\s+([\w]+)", sql_text, re.IGNORECASE)
            if m:
                return _db_col(m.group(1).strip(), col)
        return f"db::{col}"

    def _camel_to_snake(self, name: str) -> str:
        return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()

    def _snake_to_camel(self, name: str) -> str:
        parts = name.split("_")
        return parts[0] + "".join(p.title() for p in parts[1:])


register(MyBatisOrmPlugin)
