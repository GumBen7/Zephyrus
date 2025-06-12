from dataclasses import dataclass, field
from typing import List, Tuple

from models.route import Route


@dataclass
class PointsRoute(Route):
    points: List[Tuple[float, float]] = field(default_factory=list)