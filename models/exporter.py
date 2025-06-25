from abc import ABC, abstractmethod
from typing import Any

from .сity import City


class Exporter(ABC):
    @abstractmethod
    def export(self, city: City, data: list[dict[str, Any]]):
        pass
