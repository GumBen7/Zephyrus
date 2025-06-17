from dataclasses import dataclass

from models.route import Route


@dataclass
class City:
    name: str
    coordinates: tuple[float, float]
    routes: list[Route]