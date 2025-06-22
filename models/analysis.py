import math

import config
from models import City, Fetcher, Exporter
from models.exporters import CsvExporter
from models.fetchers import GeeFetcher
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
        self.current_city: City
        self.cities: list[City]
        self.data_fetcher: Fetcher
        self.exporter: Exporter
        self.__post_init__()

    def __post_init__(self):
        self.current_city = City(name=config.CITY_NAME_CHITA, coordinates=config.CITY_COORDINATES_CHITA, routes={})
        self.cities = [self.current_city]
        self.data_fetcher = GeeFetcher()
        self.create_analysis_points(config.DISTANCES_KM, config.BEARINGS_DEG)
        self.exporter = CsvExporter()
        self.obtain_data()

    def create_analysis_points(self, distances: list[int], bearings: list[int]):
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