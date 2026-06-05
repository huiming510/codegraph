"""JSP Java cross-file plugin.

Generates cross-file edges from JSP/UI elements to Java code symbols.

This plugin handles:
- JSP form → Java Form class binding
- Action → JSP rendering convention (by directory name)
- JSP → Action entry point (execute_return)
- JSP include → target file
- JSP action route → URL
- Custom tag usage → tag handler

All edges generated here are cross-file (UI ↔ Code).
"""

from pathlib import Path
from typing import Optional

from ...common.base import Edge
from ..base import CrossFilePlugin
from ..constants import EXTERNAL_PACKAGES
from ..registry import register


class JspJavaCrossFilePlugin(CrossFilePlugin):
    """Cross-file plugin for JSP UI elements → Java code bindings."""
    
    @property
    def name(self) -> str:
        return "jsp_java"
    
    @property
    def description(self) -> str:
        return "JSP UI elements → Java code cross-file edges"
    
    @property
    def supported_langs(self) -> list[str]:
        return ["java"]
    
    def can_produce(self, context, lang: str = None) -> bool:
        """Check if we have JSP elements and Java classes.

        Note: context.ui_data may be empty in the unified pipeline.
        Always return True and let produce() handle missing data.
        """
        return True
    
    def produce(self, context, lang: str = None, elements: dict = None) -> list[dict]:
        """Generate all JSP UI cross-file edges."""
        edges = []

        # Precompute lookups
        form_classes = self._find_form_classes(context)
        action_classes = self._find_action_classes(context)
        defined_tags = self._find_defined_tags(elements)

        # Build JSP filename caches
        jsp_entries = self._collect_jsp_entries(elements)
        jsp_to_action = self._build_jsp_to_action_map(context)

        # Process each JSP entry
        for jsp_entry in jsp_entries:
            jsp_path = jsp_entry.get("file", "")
            jsp_filename = Path(jsp_path).name

            # 1. Action → JSP rendering convention
            self._add_renders_edges(edges, jsp_path, jsp_filename, action_classes)

            # 2. JSP element edges
            for elem in jsp_entry.get("elements", []):
                elem_kind = elem.get("kind", "")
                elem_attrs = elem.get("attrs", {})
                elem_line = elem.get("line", 1)

                if elem_kind == "jsp_form":
                    self._add_form_binding_edges(
                        edges, jsp_path, elem_attrs, elem_line, form_classes
                    )

                elif elem_kind == "jsp_include":
                    target = elem.get("target") or elem_attrs.get("file", "")
                    if target:
                        edges.append(Edge(
                            kind="includes",
                            from_qname=f"template::{jsp_path}",
                            to_qname=f"template::{target}",
                            file=jsp_path,
                            line=elem_line,
                        ))

                elif elem_kind == "jsp_struts_action":
                    action_url = elem_attrs.get("action", "")
                    if action_url:
                        edges.append(Edge(
                            kind="action_route",
                            from_qname=f"template::{jsp_path}",
                            to_qname=f"url::{action_url}",
                            file=jsp_path,
                            line=elem_line,
                        ))

                elif elem_kind == "jsp_custom_tag":
                    tag_name = elem.get("tag_name", "")
                    bare = tag_name.split(":", 1)[-1] if ":" in tag_name else tag_name
                    if tag_name in defined_tags or bare in defined_tags:
                        edges.append(Edge(
                            kind="uses_tag",
                            from_qname=f"template::{jsp_path}",
                            to_qname=f"tag::{tag_name}",
                            file=jsp_path,
                            line=elem_line,
                        ))

            # 3. JSP → Action entry point
            action_method = jsp_to_action.get(jsp_filename)
            if action_method:
                edges.append(Edge(
                    kind="jsp_entry",
                    from_qname=f"template::{jsp_path}",
                    to_qname=action_method,
                    file=jsp_path,
                    line=1,
                ))

        return [e.to_dict() for e in edges]
    
    def _find_form_classes(self, context) -> set[str]:
        """Find all Java class names that are likely Form classes."""
        form_classes = set()
        
        for cls in context.get_symbols_by_kind("class"):
            qname = cls.get("qualified_name", "")
            name = cls.get("name", "")
            
            if not name:
                continue
            
            # Exclude external packages
            if any(qname.startswith(p) for p in EXTERNAL_PACKAGES):
                continue
            
            is_form = False
            
            # Match by naming convention: name must END with one of the known suffixes
            form_suffixes = ("Form", "Dto", "VO", "ViewModel")
            if any(name.endswith(suffix) for suffix in form_suffixes):
                is_form = True
            
            # Match by annotation (precise matching)
            annotations = cls.get("annotations", [])
            if any(a in annotations for a in ("@ActionForm", "@ModelAttribute")):
                is_form = True
            
            # Exclude framework-internal or generic classes that might have these names
            if name in ("Form", "Dto", "VO", "ViewModel", "BaseForm", "AbstractForm",
                        "GenericForm", "ActionForm", "ModelForm", "BaseDto", "AbstractDto",
                        "BaseVO", "BaseViewModel"):
                is_form = False
            
            if is_form:
                form_classes.add(qname)
        
        return form_classes
    
    def _find_action_classes(self, context) -> set[str]:
        """Find all Java class names that are likely Action classes."""
        action_classes = set()
        
        for cls in context.get_symbols_by_kind("class"):
            qname = cls.get("qualified_name", "")
            name = cls.get("name", "")
            
            if not name:
                continue
            
            # Exclude external packages first
            if any(qname.startswith(p) for p in EXTERNAL_PACKAGES):
                continue
            
            # Match by annotation (most reliable)
            annotations = cls.get("annotations", [])
            if any("@Execute" in a for a in annotations):
                action_classes.add(qname)
                continue
            
            # Match by class name convention: must END with "Action" as the suffix
            # and NOT be a framework class name (ActionResult, ActionContext, etc.)
            if name.endswith("Action") and not any(
                name.endswith(suffix) for suffix in (
                    "ActionResult", "ActionError", "ActionContext",
                    "ActionSupport", "ActionProxy", "ActionEvent",
                    "ActionListener", "ActionHandler", "ActionMapper",
                    "IAction", "BaseAction", "AbstractAction", "ActionBase",
                )
            ):
                action_classes.add(qname)
        
        return action_classes
    
    def _find_defined_tags(self, elements) -> set[str]:
        """Find all defined custom tag names from TLD data."""
        tags = set()
        if elements is None:
            return tags

        for entry in elements.get("tld", []):
            if entry.get("error") or entry.get("parse_error"):
                continue

            # Support both formats:
            # 1. Flat format: [{name, handler_class, ...}]
            # 2. Nested format: [{file, entries: [{name, class_name, ...}]}]

            if "entries" in entry:
                # Nested format
                for tag_entry in entry.get("entries", []):
                    if tag_entry.get("entry_type") == "tld_tag":
                        name = tag_entry.get("name", "")
                        if name:
                            tags.add(name)
            else:
                # Flat format
                name = entry.get("name", "")
                if name:
                    tags.add(name)

        return tags
    
    def _collect_jsp_entries(self, elements) -> list[dict]:
        """Collect all JSP entries from elements."""
        entries = []
        if elements is None:
            return entries

        # Check new templates key
        for template_result in elements.get("templates", []):
            file_path = template_result.get("file", "")
            if file_path.lower().endswith((".jsp", ".jspf", ".jspx")):
                entries.append(template_result)
        
        # Check legacy jsp key for backward compatibility
        for jsp_entry in elements.get("jsp", []):
            if jsp_entry.get("parse_error"):
                continue
            # Avoid duplicates
            file_path = jsp_entry.get("file", "")
            if file_path and not any(e.get("file") == file_path for e in entries):
                entries.append(jsp_entry)
        
        return entries
    
    def _build_jsp_to_action_map(self, context) -> dict[str, str]:
        """Build JSP filename → Action method mapping from AST data."""
        jsp_to_action = {}
        
        ast_by_file = {e.get("file"): e.get("ast") for e in context.ast_data}
        
        for sym in context.symbols:
            if sym.get("kind") != "method":
                continue
            
            annotations = sym.get("annotations", [])
            if not any("@Execute" in a for a in annotations):
                continue
            
            ast = ast_by_file.get(sym.get("file", ""))
            if ast is None:
                continue
            
            # Find return statements that reference JSP files
            jsp_files = self._find_jsp_returns(ast, sym)
            for jsp_file in jsp_files:
                jsp_to_action[jsp_file] = sym.get("qualified_name", "")
        
        return jsp_to_action
    
    def _find_jsp_returns(self, ast: dict, sym: dict) -> list[str]:
        """Find JSP filenames referenced in return statements."""
        jsp_files = []
        
        def find_return_stmts(node: dict) -> list[dict]:
            results = []
            def search(n):
                if n.get("type") == "return_statement":
                    results.append(n)
                for c in n.get("children", []):
                    search(c)
            search(node)
            return results
        
        def get_text(node: dict) -> str:
            if "text" in node:
                return node["text"]
            return "".join(get_text(c) for c in node.get("children", []))
        
        for ret in find_return_stmts(ast):
            children = ret.get("children", [])
            expr_parts = []
            started = False
            
            for c in children:
                t = c["type"]
                if t == "return":
                    started = True
                    continue
                if not started:
                    continue
                if t in (";", "comment", "block_comment", "line_comment"):
                    break
                expr_parts.append(get_text(c))
            
            raw = "".join(expr_parts).strip()
            if raw.startswith('"') and raw.endswith('"'):
                raw = raw[1:-1]
            
            if not raw or raw.lower() in ("null", "true", "false", "success", "input", "error"):
                continue
            
            raw = raw.split("?")[0].split("#")[0].strip()
            if not raw:
                continue
            
            base = raw.lstrip("/") if raw.startswith("/") else raw
            if base.endswith(".jsp"):
                jsp_files.append(base)
            else:
                jsp_files.append(base + ".jsp")
        
        return jsp_files
    
    def _add_renders_edges(self, edges: list, jsp_path: str, jsp_filename: str,
                          action_classes: set[str]) -> None:
        """Add Action → JSP rendering edges based on naming convention."""
        parent_dir = Path(jsp_path).parent.name
        if not jsp_filename.startswith(parent_dir):
            return

        inferred_action = parent_dir + "Action"
        for action_cls in action_classes:
            if action_cls.endswith(f".{inferred_action}") or action_cls.endswith(f".{parent_dir}Action"):
                edges.append(Edge(
                    kind="renders",
                    from_qname=action_cls,
                    to_qname=f"template::{jsp_path}",
                    file=jsp_path,
                    line=1,
                ))
                break
    
    def _add_form_binding_edges(self, edges: list, jsp_path: str, 
                               elem_attrs: dict, elem_line: int,
                               form_classes: set[str]) -> None:
        """Add JSP form → Java Form class binding edges."""
        form_prop = elem_attrs.get("property", "")
        if not form_prop:
            return
        
        matched = False
        for form_cls in form_classes:
            # Extract the class name without package prefix
            cls_name = form_cls.rsplit(".", 1)[-1] if "." in form_cls else form_cls
            
            # Match: Form class ends with Form/Dto/VO/ViewModel and the base name matches the property.
            # e.g. "UserForm" matches property "user" (case-insensitive, base name stripped)
            # e.g. "SearchConditionDto" matches property "searchCondition" 
            matched_suffix = False
            base_name = cls_name
            for suffix in ("Form", "Dto", "VO", "ViewModel"):
                if cls_name.lower().endswith(suffix.lower()):
                    base_name = cls_name[:-len(suffix)]
                    matched_suffix = True
                    break
            
            if not matched_suffix:
                continue
            
            # Property must match the base name (with optional singular/plural variation)
            prop_lower = form_prop.lower()
            base_lower = base_name.lower()
            
            # Direct match
            is_match = base_lower == prop_lower
            # Singular/plural: base ends with 's', property is base without 's'
            if not is_match and base_lower.endswith("s") and base_lower[:-1] == prop_lower:
                is_match = True
            # Property ends with 's', base is property without 's'
            if not is_match and prop_lower.endswith("s") and base_lower == prop_lower[:-1]:
                is_match = True
            
            if is_match:
                edges.append(Edge(
                    kind="form_bound",
                    from_qname=f"template::{jsp_path}",
                    to_qname=form_cls,
                    file=jsp_path,
                    line=elem_line,
                ))
                matched = True
                break
        
        if not matched:
            edges.append(Edge(
                kind="form_bound",
                from_qname=f"template::{jsp_path}",
                to_qname=f"ext::Form[{form_prop}]",
                file=jsp_path,
                line=elem_line,
            ))


# Register the plugin
register(JspJavaCrossFilePlugin)
