from abc import ABC, abstractmethod
from typing import Any

from .routes import MonthlyDataRoute
from .сity import City


class Fetcher(ABC):
    @abstractmethod
    def fetch(self, routes_by_bearing: dict[int, MonthlyDataRoute], year: int, month: int) -> list[dict[str, Any]]:
        pass