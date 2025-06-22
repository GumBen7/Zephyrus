import math
from typing import Optional

import config
from models import City, Fetcher, Exporter
from models.routes import MonthlyDataRoute


def calculate_new_coordinates(lat: float, lon: float, distance_km: float, bearing_deg: float) \
        -> tuple[float, float]:
    lat_rad = math.radians(lat)
    lon_rad = math.radians(lon)
    bearing_rad = math.radians(bearing_deg)
    delta = distance_km / config.EARTH_RADIUS_KM

    new_lat_rad = math.asin(
        math.sin(lat_rad) * math.cos(delta) +
        math.cos(lat_rad) * math.sin(delta) * math.cos(bearing_rad)
    )
    new_lon_rad = lon_rad + math.atan2(
        math.sin(bearing_rad) * math.sin(delta) * math.cos(lat_rad),
        math.cos(delta) - math.sin(lat_rad) * math.sin(new_lat_rad)
    )
    return math.degrees(new_lat_rad), math.degrees(new_lon_rad)

class Analysis:
    def __init__(self):
        self.current_city: Optional[City] = None
        self.cities: dict[str, City] = {}
        self.data_fetcher: Optional[Fetcher] = None
        self.exporter: Optional[Exporter] = None

    def run(self, city: City, fetcher: Fetcher, exporter: Exporter):
        self.current_city = city
        if not self.cities.get(city.id):
            self.cities[city.id] = city
        self.data_fetcher = fetcher
        self.exporter = exporter
        self._generate_points(config.DISTANCES_KM, config.BEARINGS_DEG)
        self.obtain_data()

    def _generate_points(self, distances: list[int], bearings: list[int]):
        current_city = self.current_city
        origin_lat, origin_lon = current_city.coordinates
        for bearing in bearings:
            route = MonthlyDataRoute(bearing=bearing)
            for distance in distances:
                route.distances.append(distance)
                new_lat, new_lon = calculate_new_coordinates(origin_lat, origin_lon, distance, bearing)
                route.points[distance] = new_lat, new_lon
            current_city.routes[bearing] = route

    def obtain_data(self):
        current_city = self.current_city
        all_data = []
        for year in config.YEARS_TO_ANALYZE:
            monthly_data = self.data_fetcher.fetch(current_city, year, config.MONTH_TO_ANALYZE)
            all_data.extend(monthly_data)
        self.exporter.export(current_city, all_data)