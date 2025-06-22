from dataclasses import dataclass, field

from ..route import Route


@dataclass
class PointsRoute(Route):
    points: dict[int, tuple[float, float]] = field(default_factory=dict)