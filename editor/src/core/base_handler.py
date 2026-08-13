"""
Base interface for file format handlers.
Implements the Strategy pattern as per technical specification.
"""
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class OperationData:
    """Unified representation of a CNC operation."""
    id: str
    name: str
    tool_id: str
    tool_name: str
    feed_rate: float
    speed: float
    depth: float
    parameters: Dict[str, str]  # Additional format-specific parameters
    xml_node_ref: Any  # Reference to the original XML node


@dataclass
class FileMetadata:
    """File metadata extracted from the document."""
    filename: str
    material: str
    thickness: float
    width: float
    length: float
    description: str


class BaseFormatHandler(ABC):
    """
    Abstract base class for format handlers (SCX, PGMX).
    Defines the common interface for parsing, editing, and saving.
    """

    def __init__(self, file_path: Optional[Path] = None):
        self.file_path = file_path
        self.operations: List[OperationData] = []
        self.metadata: Optional[FileMetadata] = None
        self.raw_data: Any = None  # Holds raw XML or ZIP content

    @abstractmethod
    def load(self, path: Path) -> bool:
        """
        Load and parse the file.
        Returns True if successful, False otherwise.
        Must handle encoding detection and format-specific parsing.
        """
        pass

    @abstractmethod
    def save(self, path: Path) -> bool:
        """
        Save changes back to the file.
        Must preserve original formatting and encoding where possible.
        Returns True if successful.
        """
        pass

    @abstractmethod
    def get_operations(self) -> List[OperationData]:
        """Return the list of parsed operations."""
        pass

    @abstractmethod
    def update_operation(self, operation_id: str, changes: Dict[str, Any]) -> bool:
        """
        Update a specific operation with new values.
        Returns True if updated successfully.
        """
        pass

    @abstractmethod
    def get_xml_tree(self) -> Any:
        """
        Return the XML tree structure for the tree view.
        """
        pass

    def validate(self) -> List[str]:
        """
        Validate the current data.
        Returns a list of error messages.
        """
        errors = []
        # Common validation logic can be implemented here
        return errors
