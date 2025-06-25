from dataclasses import dataclass, field


@dataclass
class Route:
    city_id: str
    bearing: int
    distances: list[int] = field(default_factory=list)