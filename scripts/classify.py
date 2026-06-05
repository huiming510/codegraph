"""Stage 0: Project File Classification — maps files to role architecture layers.

This stage categorizes source files according to 角色架构.md into the following layers:
- 01_source: Source code (backend, frontend, mobile, embedded)
- 02_template: Template files (JSP, React, Vue, etc.)
- 03_config: Configuration files (framework configs, app configs, build configs)
- 04_build: Build artifacts (Docker, CI, package manifests)
- 05_script: Scripts (deploy, DB, tool)
- 06_resource: Static resources (i18n, images, fonts, static assets)
- 07_doc: Documentation (API docs, internal docs, specs)

For --all mode: classifies all files into their respective role architecture categories.
For --singlefile mode: only determines the role for the specified file type.
"""

from pathlib import Path
from typing import Optional


# ── Extension → (layer, subcategory) mapping ───────────────────────────────────

_EXT_TO_ROLE: dict[str, tuple[str, str]] = {
    # 01_source / backend
    ".java": ("01_source", "backend"),
    ".py": ("01_source", "backend"),
    ".pyi": ("01_source", "backend"),
    ".go": ("01_source", "backend"),
    ".rs": ("01_source", "backend"),
    ".rb": ("01_source", "backend"),
    ".cs": ("01_source", "backend"),
    ".php": ("01_source", "backend"),
    ".c": ("01_source", "embedded"),
    ".cpp": ("01_source", "embedded"),
    ".cc": ("01_source", "embedded"),
    ".cxx": ("01_source", "embedded"),
    ".h": ("01_source", "embedded"),
    ".hpp": ("01_source", "embedded"),
    # 01_source / frontend
    ".js": ("01_source", "frontend"),
    ".jsx": ("01_source", "frontend"),
    ".ts": ("01_source", "frontend"),
    ".tsx": ("01_source", "frontend"),
    ".mjs": ("01_source", "frontend"),
    ".cjs": ("01_source", "frontend"),
    ".vue": ("01_source", "frontend"),
    ".svelte": ("01_source", "frontend"),
    # 01_source / mobile
    ".swift": ("01_source", "mobile"),
    ".kt": ("01_source", "mobile"),
    # 02_template / web_pages
    ".jsp": ("02_template", "web_pages"),
    ".jspf": ("02_template", "web_pages"),
    ".jspx": ("02_template", "web_pages"),
    ".tag": ("02_template", "web_pages"),
    ".tagx": ("02_template", "web_pages"),
    ".ftl": ("02_template", "web_pages"),
    ".th": ("02_template", "web_pages"),
    ".vm": ("02_template", "web_pages"),
    # 02_template / email_tpl
    ".eml": ("02_template", "email_tpl"),
    ".mjml": ("02_template", "email_tpl"),
    # 02_template / pdf_tpl
    ".xml": ("03_config", "framework"),  # XML config files (struts-config.xml, etc.)
    ".html": ("02_template", "web_pages"),
    ".htm": ("02_template", "web_pages"),
    # 03_config / app_config
    ".yml": ("03_config", "app_config"),
    ".yaml": ("03_config", "app_config"),
    ".properties": ("03_config", "app_config"),
    ".toml": ("03_config", "app_config"),
    ".ini": ("03_config", "app_config"),
    ".cfg": ("03_config", "app_config"),
    ".conf": ("03_config", "app_config"),
    ".env": ("03_config", "app_config"),
    ".json": ("03_config", "app_config"),
    # 03_config / build
    ".xml": ("03_config", "framework"),  # Maven pom.xml goes to framework/java
}


# ── Directory path → (layer, subcategory) mapping ─────────────────────────────

_DIR_TO_ROLE: list[tuple[list[str], str, str]] = [
    # More specific paths first (checked in order)
    # 03_config / framework / java
    (["WEB-INF"], "03_config", "framework/java"),
    (["webapp", "WEB-INF"], "03_config", "framework/java"),
    (["src", "main", "webapp", "WEB-INF"], "03_config", "framework/java"),
    (["src", "main", "resources"], "03_config", "app_config"),
    # src/template is an alternative resources location (e.g., Seasar2 projects)
    (["src", "template", "resources"], "03_config", "app_config"),
    # JSP files in webapp directories
    (["webapp"], "02_template", "web_pages"),
    (["src", "main", "webapp"], "02_template", "web_pages"),
    (["src", "main", "java"], "01_source", "backend"),
    (["src", "test", "java"], "01_source", "backend"),
    (["src"], "01_source", "backend"),
    # 01_source / orm — MyBatis XML Mapper files (must be BEFORE app_config to take priority)
    (["src", "main", "resources", "mapper"], "01_source", "orm"),
    (["resources", "mapper"], "01_source", "orm"),
    (["mapper"], "01_source", "orm"),
    (["app", "src"], "01_source", "frontend"),
    (["frontend", "src"], "01_source", "frontend"),
    (["public"], "01_source", "frontend"),
    (["src", "main", "kotlin"], "01_source", "mobile"),
    (["src", "main", "swift"], "01_source", "mobile"),
    # 05_script
    (["scripts", "deploy"], "05_script", "deploy"),
    (["scripts", "db"], "05_script", "db"),
    (["db", "migrations"], "05_script", "db"),
    (["scripts", "tool"], "05_script", "tool"),
    (["scripts"], "05_script", "tool"),
    # 06_resource
    (["i18n"], "06_resource", "i18n"),
    (["locales"], "06_resource", "i18n"),
    (["resources", "i18n"], "06_resource", "i18n"),
    (["static"], "06_resource", "static"),
    (["public", "images"], "06_resource", "image"),
    (["assets"], "06_resource", "static"),
    # 07_doc
    (["api"], "07_doc", "api_doc"),
    (["docs", "api"], "07_doc", "api_doc"),
    (["openapi"], "07_doc", "api_doc"),
]


# ── Filename → layer mapping ──────────────────────────────────────────────────

_FILENAME_TO_ROLE: dict[str, tuple[str, str]] = {
    # MyBatis XML Mapper files (ORM source) — must be BEFORE the .xml extension rule
    # so mapper XML files are routed to 01_source/orm instead of 03_config/framework.
    # Supports: *Mapper.xml, *Service.xml, *Repository.xml, *Query.xml, etc.
    "*mapper.xml": ("01_source", "orm"),
    "*Mapper.xml": ("01_source", "orm"),
    "*service.xml": ("01_source", "orm"),
    "*Service.xml": ("01_source", "orm"),
    "*repository.xml": ("01_source", "orm"),
    "*Repository.xml": ("01_source", "orm"),
    "*query.xml": ("01_source", "orm"),
    "*Query.xml": ("01_source", "orm"),
    "*readservice.xml": ("01_source", "orm"),
    "*ReadService.xml": ("01_source", "orm"),
    "*data.xml": ("01_source", "orm"),
    "*Data.xml": ("01_source", "orm"),
    "pom.xml": ("03_config", "framework/java"),
    "struts-config.xml": ("03_config", "framework/java"),
    "web.xml": ("03_config", "framework/java"),
    "application.properties": ("03_config", "app_config"),
    "application.yml": ("03_config", "app_config"),
    "application.yaml": ("03_config", "app_config"),
    "applicationContext.xml": ("03_config", "framework/java"),
    "spring-context.xml": ("03_config", "framework/java"),
    "package.json": ("03_config", "app_config"),
    "package-lock.json": ("03_config", "app_config"),
    "requirements.txt": ("03_config", "app_config"),
    "go.mod": ("03_config", "app_config"),
    "go.sum": ("03_config", "app_config"),
    ".env": ("03_config", "app_config"),
    ".env.local": ("03_config", "app_config"),
    ".env.development": ("03_config", "app_config"),
    ".env.production": ("03_config", "app_config"),
}


# ── File type code → (layer, subcategory) mapping for --singlefile ─────────────

FILE_TYPE_CODE_MAP: dict[str, tuple[str, str]] = {
    "java": ("01_source", "backend"),
    "python": ("01_source", "backend"),
    "javascript": ("01_source", "frontend"),
    "typescript": ("01_source", "frontend"),
    "go": ("01_source", "backend"),
    "cpp": ("01_source", "embedded"),
    "rust": ("01_source", "backend"),
    "swift": ("01_source", "mobile"),
    "kotlin": ("01_source", "mobile"),
    "jsp": ("02_template", "web_pages"),
    "html": ("02_template", "web_pages"),
    "vue": ("01_source", "frontend"),
    "xml": ("03_config", "framework"),
    "yaml": ("03_config", "app_config"),
    "yml": ("03_config", "app_config"),
    "json": ("03_config", "app_config"),
    "properties": ("03_config", "app_config"),
}


# ── Layer metadata ─────────────────────────────────────────────────────────────

LAYER_METADATA: dict[str, dict] = {
    "01_source": {"name": "源代码层", "name_en": "Source Code Layer", "index": 1},
    "02_template": {"name": "模板层", "name_en": "Template Layer", "index": 2},
    "03_config": {"name": "配置层", "name_en": "Config Layer", "index": 3},
    "05_script": {"name": "脚本层", "name_en": "Script Layer", "index": 4},
    "06_resource": {"name": "资源层", "name_en": "Resource Layer", "index": 5},
    "07_doc": {"name": "文档层", "name_en": "Documentation Layer", "index": 6},
}


# ── Helpers ──────────────────────────────────────────────────────────────────────


def _is_mapper_xml_path(path_parts: tuple) -> bool:
    """Check if path parts indicate a MyBatis XML Mapper directory."""
    lower = [p.lower() for p in path_parts]
    return "mapper" in lower


def classify_file(file_path: Path) -> tuple[str, str]:
    """Classify a single file into (layer, subcategory) based on path and extension.

    Args:
        file_path: Path to the file

    Returns:
        Tuple of (layer, subcategory), e.g. ("01_source", "backend")
    """
    path_parts = file_path.parts
    name = file_path.name
    stem = file_path.stem.lower()
    ext = file_path.suffix.lower()

    # Check filename first (most specific) — includes wildcard patterns like "*Mapper.xml"
    if name in _FILENAME_TO_ROLE:
        return _FILENAME_TO_ROLE[name]
    if stem in _FILENAME_TO_ROLE:
        return _FILENAME_TO_ROLE[stem]
    for pattern, (layer, subcat) in _FILENAME_TO_ROLE.items():
        if pattern.startswith("*") and name.lower().endswith(pattern[1:].lower()):
            return (layer, subcat)

    # Extension check — these file types should always respect extension over
    # generic directory matches like ["src"] (which would incorrectly route
    # JSON/HTML/Config files to 01_source/backend).
    if ext in _EXT_TO_ROLE:
        # MyBatis XML Mapper files in mapper/ directories take priority over generic .xml rule
        if ext == ".xml" and _is_mapper_xml_path(path_parts):
            return ("01_source", "orm")
        return _EXT_TO_ROLE[ext]

    # Check directory path patterns - find MOST SPECIFIC match (longest path)
    best_match: tuple[str, str] | None = None
    best_match_len = 0
    for path_pattern, layer, subcat in _DIR_TO_ROLE:
        if all(part in path_parts for part in path_pattern):
            # Select the match with the longest path pattern (most specific)
            if len(path_pattern) > best_match_len:
                best_match = (layer, subcat)
                best_match_len = len(path_pattern)
    if best_match:
        return best_match

    # Default: source/backend
    return ("01_source", "backend")


def classify_project_files(src_root: Path) -> dict[str, list[Path]]:
    """Classify all files in a project directory into role architecture categories.

    Args:
        src_root: Root directory of the project to classify

    Returns:
        Dictionary mapping role category string (e.g. "01_source/backend") to
        a list of file paths belonging to that category.
    """
    result: dict[str, list[Path]] = {}

    # Walk all files
    for f in src_root.rglob("*"):
        if not f.is_file():
            continue
        # Skip common non-source files
        name = f.name.lower()
        if name.startswith(".") and name not in (".env",):
            continue
        if name in ("thumbs.db", ".ds_store", "desktop.ini"):
            continue

        layer, subcat = classify_file(f)
        category = f"{layer}/{subcat}"
        result.setdefault(category, []).append(f)

    return result


def get_role_for_file_type(type_code: str) -> Optional[tuple[str, str]]:
    """Get the role (layer, subcategory) for a file type code.

    Args:
        type_code: File type code like "java", "jsp", "yaml"

    Returns:
        Tuple of (layer, subcategory) or None if unknown
    """
    return FILE_TYPE_CODE_MAP.get(type_code.lower())


def build_output_structure(out_dir: Path) -> dict[str, Path]:
    """Build the output directory structure (flat, type-based).

    Creates the root output directory. Subdirectories (one per file type)
    are created dynamically by each handler's write_jsonl.

    Args:
        out_dir: Root output directory

    Returns:
        Dictionary mapping type name to Path (empty dict — kept for API compat)
    """
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    return {}


def classify_to_output_dir(file_path: Path, out_dir: Path) -> Path:
    """Classify a file and return its output subdirectory path.

    Args:
        file_path: Source file to classify
        out_dir: Root output directory

    Returns:
        Path to the appropriate subdirectory within out_dir
    """
    layer, subcat = classify_file(file_path)
    return out_dir / layer / subcat


def print_classification_summary(classification: dict[str, list[Path]]) -> None:
    """Print a human-readable summary of the classification."""
    print(f"\nRole Architecture Classification ({len(classification)} categories):")
    print("-" * 60)

    for category in sorted(classification.keys()):
        files = classification[category]
        layer, subcat = category.split("/", 1)
        meta = LAYER_METADATA.get(layer, {})
        name = meta.get("name_en", layer)
        print(f"  {layer} {name} / {subcat}: {len(files)} files")

    total = sum(len(f) for f in classification.values())
    print(f"\nTotal: {total} files across {len(classification)} categories")
