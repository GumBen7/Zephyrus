from dataclasses import dataclass, field
from typing import List


@dataclass
class Route:
    bearing: float
    distances: List[float] = field(default_factory=list)