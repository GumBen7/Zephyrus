from dataclasses import dataclass, field

from models.routes.points_route import PointsRoute


@dataclass
class MonthlyDataRoute(PointsRoute):
    year: int = 0
    month: int = 0
    densities: dict[tuple[int, int], float] = field(default_factory=dict)