from dataclasses import dataclass, field
from typing import List

from models.routes.points_route import PointsRoute


@dataclass(kw_only=True)
class MonthlyDataRoute(PointsRoute):
    year: int
    month: int
    densities: List[float] = field(default_factory=list)