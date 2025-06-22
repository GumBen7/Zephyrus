from dataclasses import dataclass

from .route import Route


@dataclass
class City:
    name: str
    coordinates: tuple[float, float]
    routes: dict[int, Route]