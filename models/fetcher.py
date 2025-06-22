from abc import ABC, abstractmethod
from typing import Any

from .сity import City


class Fetcher(ABC):
    @abstractmethod
    def fetch(self, city: City, year: int, month: int) -> list[dict[str, Any]]:
        pass