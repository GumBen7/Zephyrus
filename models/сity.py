from dataclasses import dataclass
from typing import Tuple, List

from models.route import Route


@dataclass
class City:
    name: str
    coordinates: Tuple[float, float]
    routes: List[Route]