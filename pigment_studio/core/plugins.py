from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List
from PySide6.QtWidgets import QWidget


class PluginBase(ABC):
    """Base class for all workspace plugins."""

    @abstractmethod
    def get_name(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def create_workspace_widget(self, parent: Optional[QWidget] = None) -> QWidget:
        raise NotImplementedError

    @abstractmethod
    def on_new_session(self):
        raise NotImplementedError

    @abstractmethod
    def export_session(self) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def import_session(self, data: Dict[str, Any]):
        raise NotImplementedError

    @abstractmethod
    def get_log_signal(self):
        """Return a Qt signal(str) or None."""
        raise NotImplementedError


class PluginManager:
    """Simple plugin registry."""

    def __init__(self):
        self._plugins: List[PluginBase] = []

    def register_plugin(self, plugin: PluginBase):
        self._plugins.append(plugin)

    def get_plugins(self) -> List[PluginBase]:
        return self._plugins
