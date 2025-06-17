from dataclasses import dataclass, field
from typing import List

from models.routes.points_route import PointsRoute


@dataclass
class MonthlyDataRoute(PointsRoute):
    year: int = 0
    month: int = 0
    densities: List[float] = field(default_factory=list)