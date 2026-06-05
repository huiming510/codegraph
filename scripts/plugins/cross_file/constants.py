"""Shared constants for the plugins system.

This module contains constants that are used across multiple plugin types,
avoiding duplication of common values like external package prefixes.

Note: Only mark truly external/third-party packages as external.
Project-specific packages (even external-sounding ones like jp.co.rct., jp.co.ctc.)
should NOT be marked as external so that their classes can be included in the graph.
"""

# Packages considered "external" (not part of the analyzed project)
# Only include well-known third-party library packages here
EXTERNAL_PACKAGES = (
    "java.",
    "javax.",
    "org.apache.",          # Apache Commons, Struts, etc.
    "org.springframework.",  # Spring Framework
    "org.seasar.",          # Seasar2 (S2Container)
    "org.hibernate.",        # Hibernate ORM
    "org.hibernate.",
    "javax.persistence.",    # JPA
    "org.junit.",           # JUnit
    "org.mockito.",         # Mockito
    "org.hamcrest.",        # Hamcrest
    "org.slf4j.",           # SLF4J
    "ch.qos.",              # Logback
    "com.sun.",             # JDK internal
    "sun.",
    "org.omg.",             # CORBA
    "org.w3c.",             # XML DOM
    "org.xml.",             # XML APIs
    "junit.",               # JUnit 3/4
)

# Framework-specific package prefixes
# These are frameworks used BY the project, not the project itself
FRAMEWORK_PACKAGES = (
    "r2framework.",  # R2Framework (internal framework)
    "r2.",           # R2Framework short prefix
)


def is_external_package(package_or_class: str) -> bool:
    """Check if a package or class belongs to an external library.

    Note: Project-specific packages (like jp.co.rct., jp.co.ctc.) are NOT
    considered external so that their classes appear in the graph.
    """
    # Check framework packages first
    if any(package_or_class.startswith(p) for p in FRAMEWORK_PACKAGES):
        return True
    # Then check external packages
    return any(package_or_class.startswith(p) for p in EXTERNAL_PACKAGES)


# ── Cross-file edge type definitions ───────────────────────────────────────────


class CrossFileEdgeCategory:
    """Categories for cross-file edge types based on two dimensions:
    
    1. Layer Relation: intra_layer (same layer) / cross_layer (different layers)
    2. Type Relation: intra_type (same file type) / cross_type (different file types)
    
    Edge categories:
    - Intra-Type: Same file type edges (e.g., Java→Java extends, JSP→JSP includes)
    - Cross-Type: Same layer, different file types (e.g., Java→XML in source layer)
    - Cross-Layer: Different layers (always cross-type, e.g., Java→JSP)
    """
    # Layer relation
    INTRA_LAYER = "intra_layer"
    CROSS_LAYER = "cross_layer"
    
    # Type relation
    INTRA_TYPE = "intra_type"
    CROSS_TYPE = "cross_type"
    
    # Edge categories (combination of layer and type relations)
    INTRA_TYPE_EDGE = "intra_type"      # Same file type (layer doesn't matter)
    CROSS_TYPE_EDGE = "cross_type"      # Different file types, same layer
    CROSS_LAYER_EDGE = "cross_layer"    # Different layers (always cross-type)


# All cross-file edge types with descriptions
# Organized by category: intra_type, cross_type, cross_layer
CROSS_FILE_EDGE_TYPES: dict[str, str] = {
    # ── Intra-Type: Same file type (跨文件但同类型) ──────────────────────────────
    "jsp_include":             "JSP include → target JSP",
    "java_extends":           "Java class extends → parent class",
    "java_implements":        "Java class implements → interface",
    "java_import":            "Java import → target class/resource",
    "ts_import":              "TypeScript import → target module",
    "js_import":              "JavaScript import → target module",
    "py_import":              "Python import → target module",
    "go_import":              "Go import → target package",
    "cpp_include":          "C++ #include → header file",
    "c_include":            "C #include → header file",

    # ── Cross-Type: Same layer, different file types ────────────────────────────
    "jsp_java_render":        "Java Action → JSP (by naming convention)",
    "jsp_java_form":          "JSP form → Java Form class",
    "jsp_java_action":        "JSP action route → URL pattern",
    "react_ts_interface":     "React component → TypeScript interface",
    "vue_ts_component":       "Vue SFC → TypeScript component",

    # ── Cross-Layer: Different layers (跨层) ────────────────────────────────────
    # Template → Source
    "renders":                "Action renders → Template file",
    "form_bound":             "JSP form bound → Java Form class",
    "template_to_code":       "Template → Source code binding",

    # Config → Source
    "webxml_to_servlet":      "web.xml servlet-class → Servlet implementation",
    "webxml_to_filter":      "web.xml filter-class → Filter implementation",
    "struts_action_forward":  "struts-config.xml action → JSP forward",
    "struts_form_bean":       "struts-config.xml form-bean → Form class",
    "tld_tag_handler":        "TLD tag → Tag handler class",
    "dicon_component":        ".dicon component → Component class",
    "config_to_component":     "Config → DI component",
    "config_to_route":         "Config → Route/action",
    "config_to_service":       "Config → Service bean",
    "config_bean":             "Config → Spring/Seasar bean",

    # JavaScript/TypeScript cross-type
    "react_ts_interface":     "React component → TypeScript interface",
    "js_java_api":           "JavaScript fetch/axios → Java REST endpoint",
    "js_jsp_render":         "JSP <script src> → JavaScript file",

    # Other
    "jsp_custom_tag":         "JSP custom tag usage → Tag handler class",
    "jsp_taglib":             "JSP taglib directive → TLD descriptor",
}


# ── File type extraction helpers ───────────────────────────────────────────────


def get_file_type(file_path: str) -> str:
    """Extract file type (extension without dot) from file path.
    
    Examples:
        "path/to/file.java" → "java"
        "path/to/main.js" → "js"
        "path/to/test.tsx" → "tsx"
    """
    if not file_path:
        return ""
    import os
    _, ext = os.path.splitext(file_path)
    return ext.lstrip(".").lower()


def get_layer_from_path(file_path: str) -> str:
    """Get the layer from a file path based on the role architecture.

    Returns the layer part like "01_source", "02_template", "03_config", etc.
    If the path doesn't contain a layer directory, infers from file path patterns:
    - webapp/*.jsp → 02_template/web_pages
    - src/main/java, src/main/kotlin → 01_source/backend
    - WEB-INF/*.xml → 03_config/framework/java
    """
    if not file_path:
        return ""

    # First, try to find explicit layer directory in path
    parts = file_path.split(os.sep) if os.sep in file_path else file_path.replace("\\", "/").split("/")
    for part in parts:
        if part in ("01_source", "02_template", "03_config", "04_build", "05_script", "06_resource", "07_doc"):
            return part

    # Infer layer from path patterns
    lower_path = file_path.lower().replace("\\", "/")

    # Template patterns (JSP, Vue, React)
    if "/webapp/" in lower_path or "/webapp\\" in lower_path:
        if ".jsp" in lower_path or ".jspf" in lower_path or ".jspx" in lower_path:
            return "02_template"
        if ".html" in lower_path or ".htm" in lower_path:
            return "02_template"
    if "/frontend/" in lower_path or "/frontend\\" in lower_path:
        if ".vue" in lower_path or ".jsx" in lower_path or ".tsx" in lower_path:
            return "02_template"
        if "/src/" in lower_path and ("/views/" in lower_path or "/components/" in lower_path or "/api/" in lower_path):
            return "02_template"

    # Source patterns (Python backend)
    if "/src/server/" in lower_path or "/src/server\\" in lower_path:
        if "/server/" in lower_path:
            return "01_source"
    if "/src/index/" in lower_path or "/src/index\\" in lower_path:
        return "01_source"
    if "/src/storage/" in lower_path or "/src/storage\\" in lower_path:
        return "01_source"
    if "/src/preprocess/" in lower_path or "/src/preprocess\\" in lower_path:
        return "01_source"
    if "/src/llm/" in lower_path or "/src/llm\\" in lower_path:
        return "01_source"
    if "/src/memory/" in lower_path or "/src/memory\\" in lower_path:
        return "01_source"
    if "/src/prompts/" in lower_path or "/src/prompts\\" in lower_path:
        return "01_source"
    if "/src/workflow/" in lower_path or "/src/workflow\\" in lower_path:
        return "01_source"
    if "/src/raptor/" in lower_path or "/src/raptor\\" in lower_path:
        return "01_source"
    if "/src/backend/" in lower_path or "/src/backend\\" in lower_path:
        return "01_source"
    if "/src/web/" in lower_path or "/src/web\\" in lower_path:
        return "01_source"
    if "/src/backend/" in lower_path and "/llm/" in lower_path:
        return "01_source"
    if "/src/main/java/" in lower_path or "/src/main/kotlin/" in lower_path:
        return "01_source"
    if "/src/" in lower_path and "/java/" in lower_path:
        return "01_source"

    # Config patterns
    if "/web-inf/" in lower_path or "/web-inf\\" in lower_path:
        if ".tld" in lower_path or ".xml" in lower_path:
            return "03_config"
    if "/src/main/resources/" in lower_path:
        return "03_config"
    if "/src/config.yml" in lower_path or "/config.yml" in lower_path:
        return "03_config"
    if lower_path.endswith("pyproject.toml") or lower_path.endswith("requirements.txt"):
        return "03_config"

    # Build patterns
    if "/pom.xml" in lower_path or "/build.gradle" in lower_path or "/build.gradle.kts" in lower_path:
        return "04_build"
    if "/package.json" in lower_path or "/go.mod" in lower_path:
        return "04_build"
    if "/frontend/package.json" in lower_path:
        return "04_build"

    return ""


import os
