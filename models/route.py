from dataclasses import dataclass, field


@dataclass
class Route:
    bearing: int
    distances: list[int] = field(default_factory=list)