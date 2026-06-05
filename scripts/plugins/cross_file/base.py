"""CrossFilePlugin base class and shared types."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, TYPE_CHECKING

# Import GraphContext from the common base module
from ..common.base import GraphContext as BaseGraphContext

# For backward compatibility, alias the base class
GraphContext = BaseGraphContext


@dataclass
class CrossFileEdge:
    """Represents a cross-file edge in the knowledge graph.
    
    Cross-file edges connect elements from different files within the same project,
    enabling navigation and understanding of cross-file relationships.
    
    Attributes:
        kind: Edge type (e.g., "extends", "renders", "includes")
        from_qname: Qualified name of the source node
        to_qname: Qualified name of the target node
        file: File where this edge is defined (for reference)
        line: Line number where this edge is defined
        metadata: Additional metadata for this edge
        
        # Classification fields
        from_layer: Layer of the source (e.g., "01_source", "02_template")
        to_layer: Layer of the target
        from_type: File type of the source (e.g., "java", "jsp", "xml")
        to_type: File type of the target
        category: Edge category - "intra_type", "cross_type", or "cross_layer"
    """
    kind: str
    from_qname: str
    to_qname: str
    file: str = ""
    line: int = 0
    metadata: dict = field(default_factory=dict)
    
    # Classification fields (set by pipeline based on source/target files)
    from_layer: str = ""
    to_layer: str = ""
    from_type: str = ""
    to_type: str = ""
    category: str = ""  # "intra_type", "cross_type", "cross_layer"
    
    def to_dict(self) -> dict:
        """Convert edge to dictionary format."""
        result = {
            "kind": self.kind,
            "from_qname": self.from_qname,
            "to_qname": self.to_qname,
        }
        if self.file:
            result["file"] = self.file
        if self.line:
            result["line"] = self.line
        if self.metadata:
            result["metadata"] = self.metadata
        if self.from_layer:
            result["from_layer"] = self.from_layer
        if self.to_layer:
            result["to_layer"] = self.to_layer
        if self.from_type:
            result["from_type"] = self.from_type
        if self.to_type:
            result["to_type"] = self.to_type
        if self.category:
            result["category"] = self.category
        return result


class CrossFilePlugin(ABC):
    """Abstract base class for cross-file edge generation plugins.
    
    Cross-file plugins are responsible for generating edges that connect
    elements from different files. For example:
    - JSP form elements → Java Form classes
    - Python templates → Flask/Django view functions
    - React components → TypeScript interfaces
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Plugin identifier."""
    
    @property
    def description(self) -> str:
        """Human-readable description."""
        return ""
    
    @property
    def supported_langs(self) -> list[str]:
        """Languages this plugin supports. Empty = all languages."""
        return []
    
    def can_produce(self, context: GraphContext, lang: str = None) -> bool:
        """Check if this plugin can produce cross-file edges with the given context.
        
        Override this for complex logic. Default returns True.
        """
        return True
    
    @abstractmethod
    def produce(self, context: GraphContext, lang: str = None,
               elements: dict = None) -> list[dict]:
        """Produce cross-file edges from the given context.

        Args:
            context: GraphContext with symbols and edges
            lang: Optional language hint
            elements: Merged element data from all subgraphs
                     (e.g. {"templates": [...], "jsp": [...], "xml": [...], ...})

        Returns:
            List of edge dicts with keys: kind, from_qname, to_qname, file, line
        """
        ...
