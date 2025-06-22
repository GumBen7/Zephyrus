from dataclasses import dataclass

from .route import Route


@dataclass
class City:
    id: str
    name: str
    coordinates: tuple[float, float]
    routes: dict[int, Route]