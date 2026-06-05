"""Template code linking cross-file plugin.

Generates edges from template files to their corresponding backend code.
"""

from pathlib import Path

from ...common.base import Edge
from ..base import CrossFilePlugin
from ..registry import register


class TemplateCodeLinkPlugin(CrossFilePlugin):
    """Cross-file plugin for template → code bindings."""
    
    @property
    def name(self) -> str:
        return "template_code"
    
    @property
    def description(self) -> str:
        return "Template files → backend code bindings"
    
    @property
    def supported_langs(self) -> list[str]:
        return ["python", "javascript", "go"]
    
    def can_produce(self, context, lang: str = None) -> bool:
        """Check if we have template data."""
        if not context.ui_data.get("templates"):
            return False
        return lang in self.supported_langs
    
    def produce(self, context, lang: str = None, elements: dict = None) -> list[dict]:
        """Generate template → code cross-file edges."""
        edges = []
        
        template_lang_map = {
            "jinja2": "python",
            "vue": "javascript",
            "jsx": "javascript",
            "go_template": "go",
        }
        
        for template_result in (elements or {}).get("templates", []):
            file_path = template_result.get("file", "")
            elements = template_result.get("elements", [])
            
            for elem in elements:
                kind = elem.get("kind", "")
                target = elem.get("target", "")
                
                if kind == "template_include" and target:
                    edges.append(Edge(
                        kind="template_include",
                        from_qname=f"template::{file_path}",
                        to_qname=f"template::{target}",
                        file=file_path,
                        line=elem.get("line", 1),
                    ))
                
                elif kind == "template_url_for" and target:
                    edges.append(Edge(
                        kind="template_url_for",
                        from_qname=f"template::{file_path}",
                        to_qname=f"fn::{target}",
                        file=file_path,
                        line=elem.get("line", 1),
                    ))
        
        return [e.to_dict() for e in edges]


# Register the plugin
register(TemplateCodeLinkPlugin)
