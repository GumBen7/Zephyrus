from dataclasses import dataclass, field

from models.route import Route


@dataclass
class PointsRoute(Route):
    points: dict[tuple[int, int], tuple[float, float]] = field(default_factory=dict)