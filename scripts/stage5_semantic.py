"""Stage 5: Semantic Enrichment — control flow summary, call graph, domain annotations."""

import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

try:
    from edge_quality import (
        prune_disconnected_components,
        report_disconnected_components,
    )
except ImportError:
    from .edge_quality import (
        prune_disconnected_components,
        report_disconnected_components,
    )


# ── Domain annotation patterns (Struts2 / SAStruts / Spring / JPA / JSP / Test) ──
_FRAMEWORK_ANNOTATIONS: dict[str, str] = {
    # Java
    "@Execute": "struts.action",
    "@ActionForm": "struts.form",
    "@Resource": "di.inject",
    "@Autowired": "spring.inject",
    "@Service": "spring.service",
    "@Repository": "spring.repository",
    "@Controller": "spring.controller",
    "@RestController": "spring.rest_controller",
    "@RequestMapping": "spring.mapping",
    "@GetMapping": "spring.get_mapping",
    "@PostMapping": "spring.post_mapping",
    "@PutMapping": "spring.put_mapping",
    "@DeleteMapping": "spring.delete_mapping",
    "@Entity": "jpa.entity",
    "@Table": "jpa.table",
    "@Column": "jpa.column",
    "@Id": "jpa.id",
    "@Test": "test.case",
    "@BeforeEach": "test.setup",
    "@AfterEach": "test.teardown",
    "@DataJpaTest": "test.integration",
    "@WebMvcTest": "test.web",
}

# JSP element kind → domain tag
_JSP_ELEMENT_TAGS = {
    "jsp_tag":      "jsp.tag",
    "jsp_form":     "jsp.form",
    "jsp_form_field": "jsp.form_field",
    "jsp_include":  "jsp.include",
    "jsp_directive": "jsp.directive",
    "jsp_expression": "jsp.expression",
    "jsp_struts_action": "jsp.struts_action",
    "jsp_forward":  "jsp.forward",
    "jsp_logic":    "jsp.logic",
    "jsp_bean":     "jsp.bean",
    "jsp_custom_tag": "jsp.custom_tag",
    "jsp_struts_tag": "struts.tag",
}

# Multi-language framework annotations (merged at runtime with plugin-specific ones)
_MULTILANG_ANNOTATIONS: dict[str, str] = {
    # Python
    "@app.route": "web.route",
    "@router.get": "web.route",
    "@router.post": "web.route",
    "@router.put": "web.route",
    "@router.delete": "web.route",
    "@get": "web.route",
    "@post": "web.route",
    "@put": "web.route",
    "@delete": "web.route",
    "@pytest.fixture": "test.fixture",
    "@pytest.mark.parametrize": "test.parametrized",
    "@unittest.mock.patch": "test.mock",
    "@dataclass": "data.class",
    "@property": "oo.property",
    "@abstractmethod": "oo.abstract",
    "@staticmethod": "oo.static",
    "@classmethod": "oo.classmethod",
    "@cached_property": "oo.cached_prop",
    "@lru_cache": "perf.cache",
    # JavaScript / TypeScript
    "@Route": "web.route",
    "@Routes": "web.routes",
    "@beforeEnter": "web.route",
    "@Component": "di.component",
    "@Module": "di.module",
    "@NgModule": "angular.module",
    "@Injectable": "di.inject",
    "@Inject": "di.inject",
    "@Input": "react.prop",
    "@Output": "react.event",
    "@Prop": "react.prop",
    "@State": "react.state",
    "@Watch": "react.hook",
    "useState": "react.hook",
    "useEffect": "react.hook",
    "useCallback": "react.hook",
    "useMemo": "react.hook",
    "export default": "react.component",
    # Go
    "//go:generate": "codegen.generate",
    "//go:build": "build.tag",
    "+build": "build.tag",
    "json:": "data.serialization",
    "validate:": "data.validation",
    "yaml:": "data.serialization",
    "env:": "config.env",
    "mapstructure:": "data.mapping",
}


@dataclass
class CallNode:
    qname: str
    kind: str
    domain_tags: list[str] = field(default_factory=list)
    callers: list[str] = field(default_factory=list)
    callees: list[str] = field(default_factory=list)


def _domain_tags(sym: dict, lang: str = "java") -> list[str]:
    # Build annotation → tag mapping with correct precedence:
    # generic < framework < language plugin < framework plugin
    all_anns: dict[str, str] = {}
    all_anns.update(_FRAMEWORK_ANNOTATIONS)
    all_anns.update(_MULTILANG_ANNOTATIONS)

    # Resolve plugins via absolute import (relative imports fail when
    # run_pipeline.py sets sys.path to scripts/ without parent package)
    import sys
    _scripts = Path(__file__).resolve().parent
    if str(_scripts) not in sys.path:
        sys.path.insert(0, str(_scripts))

    try:
        from .plugins.src_01_source.backend import LanguageRegistry
        plugin = LanguageRegistry.get(lang)
        all_anns.update(plugin.get_framework_annotations())
    except Exception:
        plugin = None
    try:
        from .plugins.cfg_03_config.framework import FrameworkRegistry
        framework_plugins = FrameworkRegistry.get_for_lang(lang)
        for fw_plugin in framework_plugins:
            all_anns.update(fw_plugin.get_annotation_tags())
    except Exception:
        pass

    tags = []
    for ann in sym.get("annotations", []):
        # Normalize: strip the decorator arguments so @router.get("/login")
        # and @router.get("") both match the key "@router.get"
        normalized = ann.split("(")[0]
        tag = all_anns.get(ann) or all_anns.get(normalized)
        if tag:
            tags.append(tag)
    return tags


def _build_call_graph(symbols: list[dict], edges: list[dict], lang: str = "java") -> dict[str, CallNode]:
    nodes: dict[str, CallNode] = {}
    for sym in symbols:
        if sym.get("kind") in ("method", "function"):
            nodes[sym["qualified_name"]] = CallNode(
                qname=sym["qualified_name"],
                kind=sym.get("kind", "method"),
                domain_tags=_domain_tags(sym, lang),
            )

    for edge in edges:
        if edge["kind"] == "call":
            fr = edge["from_qname"]
            to = edge["to_qname"]
            if fr in nodes:
                if to not in nodes[fr].callees:
                    nodes[fr].callees.append(to)
            if to in nodes:
                if fr not in nodes[to].callers:
                    nodes[to].callers.append(fr)

    return nodes


def _entry_points(nodes: dict[str, CallNode]) -> list[str]:
    """Methods with no callers in graph are potential entry points."""
    return [qn for qn, n in nodes.items() if not n.callers]


def _xml_config_nodes(xml_entry: dict) -> list[dict]:
    """Convert struts-config / web.xml parsed entries into graph nodes."""
    nodes = []
    xml_path = xml_entry.get("file", "")
    file_name = Path(xml_path).name if xml_path else ""

    if file_name == "struts-config.xml":
        for am in xml_entry.get("action_mappings", []):
            attrs = am.get("attrs", {})
            path = attrs.get("path", "")
            type_cls = attrs.get("type", "")
            if path:
                nodes.append({
                    "id": f"url::{path}",
                    "label": path,
                    "kind": "struts_route",
                    "file": xml_path,
                    "domain_tags": ["struts.route"],
                    "annotations": [],
                    "action_class": type_cls,
                })
            for fwd in am.get("forwards", []):
                fname = fwd.get("name", "")
                fpath = fwd.get("path", "")
                if fname:
                    nodes.append({
                        "id": f"forward::{fname}",
                        "label": fname,
                        "kind": "struts_forward",
                        "file": xml_path,
                        "domain_tags": ["struts.forward"],
                        "annotations": [],
                        "forward_path": fpath,
                    })
        for fb in xml_entry.get("form_beans", []):
            attrs = fb.get("attrs", {})
            name = attrs.get("name", "")
            cls = attrs.get("type", "")
            if name:
                nodes.append({
                    "id": f"formbean::{name}",
                    "label": name,
                    "kind": "struts_formbean",
                    "file": xml_path,
                    "domain_tags": ["struts.formbean"],
                    "annotations": [],
                    "form_class": cls,
                })
        for gfwd in xml_entry.get("global_forwards", []):
            attrs = gfwd.get("attrs", {})
            gname = attrs.get("name", "")
            gpath = attrs.get("path", "")
            if gname:
                nodes.append({
                    "id": f"forward::{gname}",
                    "label": gname,
                    "kind": "struts_global_forward",
                    "file": xml_path,
                    "domain_tags": ["struts.global_forward"],
                    "annotations": [],
                    "forward_path": gpath,
                })

    elif file_name == "web.xml":
        for sm in xml_entry.get("servlet_mappings", []):
            pattern = sm.get("url_pattern", "")
            servlet = sm.get("servlet_name", "")
            if pattern:
                nodes.append({
                    "id": f"pattern::{pattern}",
                    "label": pattern,
                    "kind": "servlet_pattern",
                    "file": xml_path,
                    "domain_tags": ["web.pattern"],
                    "annotations": [],
                    "servlet_name": servlet,
                })
            if servlet:
                nodes.append({
                    "id": f"servlet::{servlet}",
                    "label": servlet,
                    "kind": "servlet_def",
                    "file": xml_path,
                    "domain_tags": ["web.servlet"],
                    "annotations": [],
                })
        for fm in xml_entry.get("filter_mappings", []):
            fname = fm.get("filter_name", "")
            pattern = fm.get("url_pattern", "")
            if fname:
                nodes.append({
                    "id": f"filter::{fname}",
                    "label": fname,
                    "kind": "filter_def",
                    "file": xml_path,
                    "domain_tags": ["web.filter"],
                    "annotations": [],
                    "url_pattern": pattern,
                })
                # Also create pattern node for filter URL patterns (for filter_chain edge)
                if pattern:
                    nodes.append({
                        "id": f"pattern::{pattern}",
                        "label": pattern,
                        "kind": "servlet_pattern",
                        "file": xml_path,
                        "domain_tags": ["web.pattern"],
                        "annotations": [],
                        "servlet_name": "",
                    })
        for cp in xml_entry.get("context_params", []):
            pname = cp.get("param_name", "")
            if pname:
                nodes.append({
                    "id": f"ctxparam::{pname}",
                    "label": pname,
                    "kind": "context_param",
                    "file": xml_path,
                    "domain_tags": ["web.context_param"],
                    "annotations": [],
                    "param_value": cp.get("param_value", ""),
                })

    return nodes


def _annotate_classes(symbols: list[dict], lang: str = "java") -> list[dict]:
    enriched = []
    for sym in symbols:
        sym = dict(sym)
        # Annotate classes with domain tags from annotations
        if sym["kind"] in ("class", "interface", "enum", "struct"):
            sym["domain_tags"] = _domain_tags(sym, lang)
        # Also annotate functions/methods with domain tags from decorators
        # (e.g. @router.get → "web.route", @pytest.fixture → "test.fixture")
        if sym["kind"] in ("function", "method"):
            sym["domain_tags"] = _domain_tags(sym, lang)
        enriched.append(sym)
    return enriched


def _control_flow_summary(sym: dict, lang: str = "java") -> Optional[str]:
    # Build annotation → tag mapping with correct precedence:
    # generic < framework < language plugin < framework plugin
    all_anns: dict[str, str] = {}

    # Resolve plugins via absolute import (relative imports fail when
    # run_pipeline.py sets sys.path to scripts/ without parent package)
    import sys as _sys
    _scripts = Path(__file__).resolve().parent
    if str(_scripts) not in _sys.path:
        _sys.path.insert(0, str(_scripts))

    # 1. Generic framework annotations (Struts, Spring, etc.)
    all_anns.update(_FRAMEWORK_ANNOTATIONS)
    # 2. Generic multi-language annotations (web.route, test.fixture, etc.)
    all_anns.update(_MULTILANG_ANNOTATIONS)
    # 3. Language plugin annotations (Python, Java, etc.)
    try:
        from plugins.src_01_source.backend import LanguageRegistry
        plugin = LanguageRegistry.get(lang)
        all_anns.update(plugin.get_framework_annotations())
    except Exception:
        plugin = None
    # 4. Framework plugin annotations (FastAPI, Flask, Django, etc.) — last wins
        from plugins.cfg_03_config.framework import FrameworkRegistry
        framework_plugins = FrameworkRegistry.get_for_lang(lang)
        for fw_plugin in framework_plugins:
            all_anns.update(fw_plugin.get_annotation_tags())
    except Exception:
        pass

    # Normalize annotation: strip arguments so @router.get("/login") matches @router.get
    for ann in sym.get("annotations", []):
        normalized = ann.split("(")[0]
        tag = all_anns.get(ann) or all_anns.get(normalized)
        if not tag:
            continue

        # Determine control_flow from the tag
        if tag in ("web.route", "fastapi.route", "flask.route",
                   "flask.blueprint", "spring.get_mapping", "spring.post_mapping",
                   "spring.put_mapping", "spring.delete_mapping",
                   "spring.mapping", "spring.rest_controller",
                   "spring.controller", "struts.action"):
            return "web_action"
        if tag in ("test.case", "test.integration", "test.web",
                   "test.parametrized", "test.fixture", "test.pytest.fixture"):
            return "test_case"
        if "fixture" in tag:
            return "test_fixture"

    # Delegate language-specific heuristics to plugin
    if plugin is not None:
        result = plugin.get_control_flow_hints(sym)
        if result:
            return result

        entry_point_names = plugin.get_entry_point_names()
        sym_name = sym.get("name", "")
        if sym_name in entry_point_names:
            return "entry_point"

    return None


def _generate_config_nodes(ui_data: dict) -> list[dict]:
    """Generate nodes from config files using ConfigRegistry.

    Creates config_file nodes for visibility in the graph, along with
    format-specific nodes (e.g., env_var nodes) via plugin delegation.
    """
    nodes = []
    seen_ids: set[str] = set()

    try:
        from .plugins.cfg_03_config.app_config import ConfigRegistry
        from .plugins.cfg_03_config.app_config.base import ConfigSchema, ConfigEntry, ConfigRef
    except ImportError:
        from plugins.cfg_03_config.app_config import ConfigRegistry
        from plugins.cfg_03_config.app_config.base import ConfigSchema, ConfigEntry, ConfigRef

    config_formats = ConfigRegistry.available_formats()

    for fmt in config_formats:
        plugin = ConfigRegistry.get(fmt)
        if plugin is None:
            continue

        for config_result in ui_data.get(fmt, []):
            if config_result.get("parse_error"):
                continue

            file_path = config_result.get("file", "")
            if not file_path or file_path in seen_ids:
                continue

            node_id = f"config::{file_path}"
            if node_id in seen_ids:
                continue
            seen_ids.add(node_id)

            file_name = Path(file_path).name
            entries = config_result.get("entries", [])
            refs = config_result.get("refs", [])

            # Determine domain tags based on file and content
            domain_tags = [f"config.{fmt}"]

            # Detect project type
            if file_name == "pyproject.toml":
                domain_tags.append("python.project")
            elif file_name == "package.json":
                domain_tags.append("javascript.project")
            elif file_name == ".env" or file_name.endswith(".env"):
                domain_tags.append("config.env")

            # Count significant entries
            entry_count = len(entries)
            ref_count = len(refs)

            # Detect if it contains secrets
            has_secrets = any(
                "SECRET" in str(e.get("key", "")) or
                "TOKEN" in str(e.get("key", "")) or
                "KEY" in str(e.get("key", ""))
                for e in entries
            )

            nodes.append({
                "id": node_id,
                "qualified_name": node_id,
                "label": file_name,
                "kind": "config_file",
                "file": file_path,
                "domain_tags": domain_tags,
                "annotations": [],
                "config_format": fmt,
                "entry_count": entry_count,
                "ref_count": ref_count,
                "has_secrets": has_secrets,
            })

            # Delegate format-specific node generation to plugin
            schema = ConfigSchema(
                file=file_path,
                format=fmt,
                entries=[],
                refs=[],
                parse_error=False,
            )
            for e in entries:
                if isinstance(e, dict):
                    schema.entries.append(ConfigEntry(**{k: v for k, v in e.items() if k in ConfigEntry.__dataclass_fields__}))
                else:
                    schema.entries.append(e)
            for r in refs:
                if isinstance(r, dict):
                    schema.refs.append(ConfigRef(**{k: v for k, v in r.items() if k in ConfigRef.__dataclass_fields__}))
                else:
                    schema.refs.append(r)

            extra_nodes = plugin.produce_nodes(schema)
            for extra_node in extra_nodes:
                extra_id = extra_node.get("id", extra_node.get("qualified_name", ""))
                if extra_id and extra_id not in seen_ids:
                    seen_ids.add(extra_id)
                    nodes.append(extra_node)

    return nodes


def semantic_enrichment(
    refs_data: dict,
    ui_data: dict | None = None,
    lang: str = "java",
    *,
    skip_prune: bool = False,
) -> dict:
    symbols = refs_data["symbols"]
    edges = refs_data["edges"]

    symbols = _annotate_classes(symbols, lang)

    for sym in symbols:
        if sym.get("kind") in ("method", "function"):
            cf = _control_flow_summary(sym, lang)
            if cf:
                sym["control_flow"] = cf

    call_graph = _build_call_graph(symbols, edges, lang)
    entry_pts = _entry_points(call_graph)

    # ── Minimalist UI nodes from UI data ────────────────────────────────────
    # Principles:
    #   • jsp_element nodes → embedded in jsp_page.tag_usage
    #   • jsp_tag_def (JSTL/std) → not nodes; project-custom → tag::* nodes
    #   • servlet_def / servlet_pattern → merged into filter_def.url_pattern
    ui_nodes: list[dict] = []
    if ui_data:
        # Collect project-custom tag names (prefixes used in this project)
        project_tag_prefixes = ("r2", "jj", "base", "r2logic")
        defined_tag_names: set[str] = set()
        for entry in ui_data.get("tld", []):
            if "error" in entry:
                continue
            name = entry.get("name", "")
            if name.startswith(project_tag_prefixes) or any(
                name.startswith(p + ":") for p in project_tag_prefixes
            ):
                defined_tag_names.add(name)

        # JSP file nodes: embed element summary, skip jsp_element sub-nodes
        # Use relative path from webapp root to match execute_return edge format
        webapp_root: Optional[Path] = None
        for jsp_entry in ui_data.get("jsp", []):
            if jsp_entry.get("parse_error"):
                continue
            jsp_path = Path(jsp_entry["file"])
            parts = jsp_path.parts
            for i, part in enumerate(parts):
                if part == "webapp":
                    webapp_root = Path(*parts[:i])
                    break
            if webapp_root:
                break
        if webapp_root is None:
            for jsp_entry in ui_data.get("jsp", []):
                if not jsp_entry.get("parse_error"):
                    webapp_root = Path(jsp_entry["file"]).parent.parent
                    break

        for jsp_entry in ui_data.get("jsp", []):
            if jsp_entry.get("parse_error"):
                continue
            jsp_path = jsp_entry["file"]
            jsp_path_obj = Path(jsp_path)
            # Convert to relative path from webapp root for matching execute_return edges
            if webapp_root and str(jsp_path_obj).startswith(str(webapp_root)):
                rel_path = str(jsp_path_obj.relative_to(webapp_root)).replace("\\", "/")
            else:
                rel_path = jsp_path_obj.name
            # Build concise tag usage: (tag_name, kind, first_line)
            tag_usage = [
                {
                    "tag": elem["tag_name"],
                    "kind": elem["kind"].replace("jsp_", ""),
                    "line": elem["line"],
                    "attrs": elem.get("attrs", {}),
                }
                for elem in jsp_entry.get("elements", [])
            ]
            # Extract unique custom tags used in this file
            custom_tags = sorted(set(
                t["tag"] for t in tag_usage
                if t["tag"].startswith(project_tag_prefixes) or
                   any(t["tag"].startswith(p + ":") for p in project_tag_prefixes)
            ))
            ui_nodes.append({
                "id": f"file::{jsp_path}",
                "qualified_name": f"file::{jsp_path}",
                "label": jsp_path_obj.name,
                "kind": "jsp_page",
                "file": jsp_path,
                "domain_tags": ["jsp.page"],
                "annotations": [],
                "tag_usage": tag_usage,      # all elements embedded
                "custom_tags": custom_tags,  # project tags only
            })

        # Project-custom tag nodes only (r2*, jj*, base*, r2logic*)
        seen_tag_ids: set[str] = set()
        for tld_entry in ui_data.get("tld", []):
            if "error" in tld_entry:
                continue
            name = tld_entry.get("name", "")
            tag_id = f"tag::{name}"
            if tag_id in seen_tag_ids:
                continue  # skip duplicate definitions from multiple TLD files
            seen_tag_ids.add(tag_id)
            if not (
                name.startswith(project_tag_prefixes) or
                any(name.startswith(p + ":") for p in project_tag_prefixes)
            ):
                continue  # skip JSTL/std tags — no node needed
            ui_nodes.append({
                "id": f"tag::{name}",
                "label": name,
                "kind": "jsp_tag_def",
                "file": tld_entry.get("file", ""),
                "domain_tags": ["jsp.tag_def"],
                "annotations": [],
                "handler": tld_entry.get("handler_class", ""),
                "body_content": tld_entry.get("body_content", ""),
            })

        # filter_def nodes: merge servlet info + url_pattern (no separate servlet/pattern nodes)
        for xml_entry in ui_data.get("xml", []):
            if not xml_entry or xml_entry.get("parse_error"):
                continue
            if "filter_mappings" not in xml_entry:
                continue
            xml_path = xml_entry["file"]
            for fm in xml_entry.get("filter_mappings", []):
                fname = fm.get("filter_name", "")
                pattern = fm.get("url_pattern", "")
                if not fname:
                    continue
                ui_nodes.append({
                    "id": f"filter::{fname}",
                    "label": fname,
                    "kind": "filter_def",
                    "file": xml_path,
                    "domain_tags": ["web.filter"],
                    "annotations": [],
                    "url_pattern": pattern,
                })
            # servlet_bound: embed in servlet_def node (compact — only one per web.xml)
            for sm in xml_entry.get("servlet_mappings", []):
                servlet = sm.get("servlet_name", "")
                pattern = sm.get("url_pattern", "")
                if servlet:
                    ui_nodes.append({
                        "id": f"servlet::{servlet}",
                        "label": servlet,
                        "kind": "servlet_def",
                        "file": xml_path,
                        "domain_tags": ["web.servlet"],
                        "annotations": [],
                        "url_pattern": pattern,
                    })

        # Build name→class lookup from servlet_defs / filter_defs (added in stage1b)
        impl_by_servlet: dict[str, str] = {}
        impl_by_filter: dict[str, str] = {}
        for xml_entry in ui_data.get("xml", []):
            if not xml_entry or xml_entry.get("parse_error"):
                continue
            for sd in xml_entry.get("servlet_defs", []):
                if sd.get("class"):
                    impl_by_servlet[sd["name"]] = sd["class"]
            for fd in xml_entry.get("filter_defs", []):
                if fd.get("class"):
                    impl_by_filter[fd["name"]] = fd["class"]

    # Normalize: use "qualified_name" so _write_jsonl can write them
    for node in ui_nodes:
        node["qualified_name"] = node.pop("id")
        node.setdefault("scope", "")

    # Mark orphan jsp_pages as entry points (legitimate leaf pages with no incoming edges)
    targets_in_edges = {e["to_qname"] for e in edges}
    for node in ui_nodes:
        if node["kind"] == "jsp_page" and node["qualified_name"] not in targets_in_edges:
            node["is_entry"] = True

    # ── Cross-reference: servlet_def / filter_def → implementation class ──────
    # Runs after normalization so node identifiers are `qualified_name`
    for node in ui_nodes:
        impl = ""
        if node["kind"] == "servlet_def":
            name = node["qualified_name"].replace("servlet::", "")
            impl = impl_by_servlet.get(name, "")
        elif node["kind"] == "filter_def":
            name = node["qualified_name"].replace("filter::", "")
            impl = impl_by_filter.get(name, "")

        if impl:
            # Trim method-level suffix if present (e.g. "pkg.Class.method" → "pkg.Class")
            parts = impl.split(".")
            impl_cls = ".".join(parts[:-1]) if parts[-1][0].islower() else impl
            if impl_cls:
                edges.append({
                    "kind": "servlet_bound",
                    "from_qname": node["qualified_name"],
                    "to_qname": impl_cls,
                    "file": node.get("file", ""),
                    "line": 0,
                })

    # ── Filter chain: connect filter_def nodes by URL pattern overlap ────────────
    # Collect filter_def qnames in declaration order
    filter_qnames: list[str] = []
    filter_patterns: dict[str, str] = {}
    for node in ui_nodes:
        if node["kind"] == "filter_def":
            qn = node["qualified_name"]
            filter_qnames.append(qn)
            filter_patterns[qn] = node.get("url_pattern", "")

    if filter_qnames:
        # ── Build filter chain: group by URL pattern, chain within each group ─────────
        # J2EE filter order: filters matching /* run for ALL requests before servlet;
        # *.do-specific filters run before /* filters on *.do requests;
        # *.jsp-specific filters run before /* filters on *.jsp requests.
        # We build a linear chain per pattern group, then the /* group links to servlet.
        pattern_groups: dict[str, list[str]] = {}
        for qn in filter_qnames:
            pat = filter_patterns.get(qn, "")
            pattern_groups.setdefault(pat, []).append(qn)

        chain_added: set[tuple[str, str]] = set()

        # Chain filters within each pattern group (in declaration order)
        for pat, group in pattern_groups.items():
            for i in range(len(group)):
                from_qn = group[i]
                to_qn = group[i + 1] if i + 1 < len(group) else None
                if to_qn:
                    edges.append({
                        "kind": "filter_chain",
                        "from_qname": from_qn,
                        "to_qname": to_qn,
                        "file": "",
                        "line": 0,
                    })
                    chain_added.add((from_qn, to_qn))

        # The /* group is the last stage — last /* filter in chain → servlet
        star_group = pattern_groups.get("/*", [])
        if star_group:
            last_star = star_group[-1]
            if (last_star, "servlet::action") not in chain_added:
                edges.append({
                    "kind": "filter_chain",
                    "from_qname": last_star,
                    "to_qname": "servlet::action",
                    "file": "",
                    "line": 0,
                })
                chain_added.add((last_star, "servlet::action"))

        # *.do filters: last *.do filter → last /* filter
        do_group = pattern_groups.get("*.do", [])
        if do_group and star_group:
            last_do = do_group[-1]
            last_star = star_group[-1]
            if (last_do, last_star) not in chain_added:
                edges.append({
                    "kind": "filter_chain",
                    "from_qname": last_do,
                    "to_qname": last_star,
                    "file": "",
                    "line": 0,
                })
                chain_added.add((last_do, last_star))

        # *.jsp filters: last *.jsp filter → last /* filter
        jsp_group = pattern_groups.get("*.jsp", [])
        if jsp_group and star_group:
            last_jsp = jsp_group[-1]
            last_star = star_group[-1]
            if (last_jsp, last_star) not in chain_added:
                edges.append({
                    "kind": "filter_chain",
                    "from_qname": last_jsp,
                    "to_qname": last_star,
                    "file": "",
                    "line": 0,
                })
                chain_added.add((last_jsp, last_star))

    # ── Tag def → DI component: connect tag_def nodes to their DI-bound implementation class ─
    # The defined_in edges (tag → handler) are already created in stage4.
    # Here we add di_bound edges: tag → dicon component (for DI tracing).
    tag_di_bound_added: set[tuple[str, str]] = set()
    for node in ui_nodes:
        if node["kind"] == "jsp_tag_def":
            tag_qn = node["qualified_name"]
            handler = node.get("handler", "")
            if not handler:
                continue
            di_bound_key = None
            for e in edges:
                if e.get("kind") == "di_component" and e.get("to_qname", "").endswith(handler):
                    di_bound_key = (tag_qn, e.get("from_qname", ""))
                    break
            if di_bound_key is not None and di_bound_key not in tag_di_bound_added:
                tag_di_bound_added.add(di_bound_key)
                edges.append({
                    "kind": "di_bound",
                    "from_qname": tag_qn,
                    "to_qname": di_bound_key[1],
                    "file": node.get("file", ""),
                    "line": 0,
                })

    # ── Unconnected servlet_def → servlet: bridge s2container and others ───────────
    servlet_to_action_added: set[str] = set()
    for node in ui_nodes:
        if node["kind"] == "servlet_def" and node["qualified_name"] != "servlet::action":
            qn = node["qualified_name"]
            if qn not in servlet_to_action_added:
                edges.append({
                    "kind": "servlet_bound",
                    "from_qname": qn,
                    "to_qname": "servlet::action",
                    "file": node.get("file", ""),
                    "line": 0,
                })
                servlet_to_action_added.add(qn)

    # ── Orphan jsp_page → Action: connect leaf pages to the Action that renders them ───
    # Step 1: Build a map from JSP filename → Action method (from execute_return edges)
    # Keys use filename (not full path) to match jsp_filename_to_norm keys.
    jsp_to_action: dict[str, str] = {}
    for e in edges:
        if e.get("kind") == "execute_return" and e.get("to_qname", "").startswith("file::"):
            jsp_ref = e["to_qname"][5:]  # strip "file::"
            jsp_filename = Path(jsp_ref).name
            action_method = e.get("from_qname", "")
            if action_method and jsp_filename:
                jsp_to_action[jsp_filename] = action_method

    # Step 2: For orphan JSP pages (no incoming edges), connect to their rendering Action
    jsp_entry_added: set[str] = set()
    for node in ui_nodes:
        if node["kind"] == "jsp_page":
            qn = node["qualified_name"]
            jsp_filename = Path(qn[5:]).name  # strip "file::", get filename
            has_incoming = any(e["to_qname"] == qn for e in edges)

            if not has_incoming and qn not in jsp_entry_added:
                target_action = None

                # Option 1: Look up from execute_return edges (by filename)
                if jsp_filename in jsp_to_action:
                    target_action = jsp_to_action[jsp_filename]

                # Option 2: Infer from JSP filename (e.g., JJ901ABTEST00101.jsp → JJ901Action)
                if not target_action:
                    jsp_name = Path(qn[5:]).stem
                    parent_dir = Path(qn[5:]).parent.name
                    if jsp_name.startswith(parent_dir):
                        inferred_action_name = parent_dir + "Action"
                        for e in edges:
                            if e.get("kind") == "defined_in":
                                cls = e.get("from_qname", "")
                                if cls.endswith("." + inferred_action_name) or cls.endswith("." + parent_dir + "Action"):
                                    for e2 in edges:
                                        if e2.get("kind") == "execute_return" and e2.get("from_qname", "").startswith(cls):
                                            target_action = e2.get("from_qname")
                                            break
                                    if target_action:
                                        break

                if target_action:
                    edges.append({
                        "kind": "jsp_entry",
                        "from_qname": qn,
                        "to_qname": target_action,
                        "file": node.get("file", ""),
                        "line": 0,
                    })
                    jsp_entry_added.add(qn)

    # ── JSP form action → Action method: connect JSP form submissions to target methods ─
    # JSP files declare <html:form action="methodName"> which routes to an Action method.
    # We build: JSP_page --jsp_form_submit--> ActionClass.methodName
    #
    # Resolution strategy (3 passes, most specific first):
    #   1. Use existing jsp_entry edges: same JSP → same Action class (form submit often
    #      targets the SAME Action as the page entry, but with a different method).
    #   2. Fall back to Action class inference from JSP filename (e.g. JJ901SQL00101.jsp →
    #      JJ901SQL001Action), then look for the named method in symbols.
    #   3. Skip if neither can be resolved (action="/" or absolute path — handled by server config).
    if ui_data:
        action_class_by_jsp: dict[str, str] = {}
        for e in edges:
            if e.get("kind") == "jsp_entry":
                jsp_ref = e.get("from_qname", "")
                target_method = e.get("to_qname", "")
                if jsp_ref.startswith("file::") and "." in target_method:
                    jsp_file = Path(jsp_ref[5:]).name
                    action_class_by_jsp[jsp_file] = target_method.rsplit(".", 1)[0]

        # Also use execute_return edges as fallback (Action → JSP direction)
        for e in edges:
            if e.get("kind") == "execute_return":
                jsp_ref = e.get("to_qname", "")
                target_method = e.get("from_qname", "")
                jsp_file = Path(jsp_ref[5:]).name if jsp_ref.startswith("file::") else ""
                if jsp_file and "." in target_method:
                    if jsp_file not in action_class_by_jsp:
                        action_class_by_jsp[jsp_file] = target_method.rsplit(".", 1)[0]

        # Build method qname lookup: class.qname → full qname (handles overloaded/overridden)
        method_qnames: dict[tuple[str, str], str] = {}
        for sym in symbols:
            if sym.get("kind") == "method" and sym.get("qualified_name"):
                parts = sym["qualified_name"].rsplit(".", 1)
                if len(parts) == 2:
                    method_qnames[(parts[0], parts[1])] = sym["qualified_name"]

        # Build JSP page qname lookup (file path → node qname)
        jsp_page_qnames: dict[str, str] = {}
        for node in ui_nodes:
            if node.get("kind") == "jsp_page":
                fpath = node.get("qualified_name", "")
                if fpath.startswith("file::"):
                    jsp_page_qnames[Path(fpath[5:]).name] = fpath

        form_submit_added: set[tuple[str, str]] = set()
        for jsp_entry in ui_data.get("jsp", []):
            if jsp_entry.get("parse_error"):
                continue
            jsp_file = Path(jsp_entry["file"]).name
            jsp_page_qname = jsp_page_qnames.get(jsp_file, f"file::{jsp_entry['file']}")

            for elem in jsp_entry.get("elements", []):
                if elem.get("kind") != "jsp_struts_action":
                    continue
                action_name = elem.get("target", "")
                if not action_name:
                    continue

                # Skip absolute paths, fragment refs, or empty targets
                if action_name in ("", "#") or action_name.startswith("/") or action_name.startswith("http"):
                    continue

                # Resolve Action class
                action_class = action_class_by_jsp.get(jsp_file, "")
                if not action_class:
                    # Try: infer from parent dir + Action suffix
                    parent_dir = Path(jsp_entry["file"]).parent.name
                    candidates = [
                        f"jp.co.rct.jj.action.{parent_dir}Action",
                        f"jp.co.rct.jj.action.{parent_dir.upper()}Action",
                    ]
                    for cand in candidates:
                        if cand in {v[0] for v in method_qnames}:
                            action_class = cand
                            break

                if not action_class:
                    continue

                target_qname = method_qnames.get((action_class, action_name), "")
                if not target_qname:
                    continue

                edge_key = (jsp_page_qname, target_qname)
                if edge_key in form_submit_added:
                    continue

                form_submit_added.add(edge_key)
                edges.append({
                    "kind": "jsp_form_submit",
                    "from_qname": jsp_page_qname,
                    "to_qname": target_qname,
                    "file": jsp_entry["file"],
                    "line": elem.get("line", 0),
                })

    # ── Normalize file:: references: replace short filenames with full paths ──
    # Some edges (execute_return, includes, etc.) use just the filename as to_qname/from_qname,
    # but jsp_page nodes use the full path. Normalize all edges to use full paths.
    # Build: filename → full-path qname mapping
    jsp_by_filename: dict[str, str] = {}  # filename → full-path qname
    for node in ui_nodes:
        if node["kind"] == "jsp_page":
            qn = node["qualified_name"]  # already normalized to id
            if qn.startswith("file::"):
                fname = Path(qn[5:]).name
                if fname not in jsp_by_filename:
                    jsp_by_filename[fname] = qn

    # Normalize edge to_qname and from_qname: short filename → full path
    normalized_count = 0
    for edge in edges:
        for key in ("to_qname", "from_qname"):
            qname = edge.get(key, "")
            if qname.startswith("file::") and not qname.startswith("file::D:\\") and not qname.startswith("file::C:\\") and not qname.startswith("file::/"):
                fname = qname[5:]  # strip "file::"
                # Only normalize if this is a short filename (contains extension, no directory separators)
                if "." in fname and "\\" not in fname and "/" not in fname and fname in jsp_by_filename:
                    full_qname = jsp_by_filename[fname]
                    edge[key] = full_qname
                    normalized_count += 1

    if normalized_count > 0:
        print(f"  normalized {normalized_count} short filename references to full paths")

    # ── Append UI nodes to symbols list so they appear in nodes.jsonl
    symbols = symbols + ui_nodes

    # ── Config file nodes (YAML, TOML, JSON, ENV) ──────────────────────────────
    # Add config files as nodes for graph visibility
    if ui_data:
        config_nodes = _generate_config_nodes(ui_data)
        symbols = symbols + config_nodes
        # Add contains edges: config_file -> env_var / other config children
        # env_var nodes have a "file" attribute pointing to their source config file.
        # We use that to find the parent config_file id.
        config_file_by_path: dict[str, str] = {}
        for cn in config_nodes:
            if cn.get("kind") == "config_file":
                config_file_by_path[cn.get("file", "")] = cn["id"]
        for cn in config_nodes:
            if cn.get("kind") != "config_file":
                file_path = cn.get("file", "")
                parent_id = config_file_by_path.get(file_path)
                if parent_id:
                    edges.append({
                        "kind": "contains",
                        "from_qname": parent_id,
                        "to_qname": cn["id"],
                        "file": file_path,
                        "line": 0,
                    })

    # ── Phase 2: Reachability pruning — remove disconnected components ─────────
    # Only keep nodes and edges reachable from entry points (web actions, test cases,
    # UI-referenced symbols). This eliminates isolated clusters that have no connection
    # to the main code graph. Skipped when --full is set.
    original_symbol_count = len(symbols)
    original_edge_count = len(edges)
    if skip_prune:
        print(f"  [full mode] skipped reachability pruning ({len(symbols)} symbols, {len(edges)} edges)")
    else:
        kept_symbols, kept_edges, _ = prune_disconnected_components(
            symbols, edges, verbose=True
        )
        symbols = kept_symbols
        edges = kept_edges
        if original_symbol_count > len(symbols):
            removed = original_symbol_count - len(symbols)
            print(f"  disconnected components pruned: {removed} nodes removed from graph")

    return {
        "symbols": symbols,
        "edges": edges,
        "call_graph": {qn: n.__dict__ for qn, n in call_graph.items()},
        "entry_points": entry_pts,
        "stats": {
            "files": len({s["file"] for s in symbols}),
            "symbols": len(symbols),
            "edges": len(edges),
            "call_graph_nodes": len(call_graph),
            "entry_points": len(entry_pts),
        },
    }


if __name__ == "__main__":
    import sys
    refs_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("output/stage4_refs.json")
    out = Path("output/stage5_graph.json")
    data = json.loads(refs_path.read_text(encoding="utf-8"))
    result = semantic_enrichment(data)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    stats = result["stats"]
    print(
        f"Stage 5 complete → {out}\n"
        f"  files={stats['files']}  symbols={stats['symbols']}  "
        f"edges={stats['edges']}  call_graph={stats['call_graph_nodes']}  "
        f"entry_points={stats['entry_points']}"
    )
