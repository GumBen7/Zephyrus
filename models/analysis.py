import math
import traceback
from typing import Optional, Any

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
        self.current_month: int | None = None

    def run(self, city: City, bearings: list[int], month: int, distances: list[int], fetcher: Fetcher, exporter: Exporter):
        print("Analysis.run method started.")
        try:
            self.current_city = city
            if not self.cities.get(city.id):
                self.cities[city.id] = city
                print(f"Added {city.name} to cities cache.")

            # Создаем или находим MonthlyDataRoute для текущих параметров
            routes_to_process: dict[int, MonthlyDataRoute] = {}
            print(f"Processing {len(bearings)} bearings for month {month}.")
            for bearing in bearings:
                print(f"  Checking bearing: {bearing}")

                found_route = None
                print(
                    f"  Searching for existing route in city.routes (current size: {len(city.routes)}). Type of city.routes: {type(city.routes).__name__}.")  # Добавлен вывод типа

                # Добавим дополнительную проверку на итерируемость, хотя это и маловероятно
                if not isinstance(city.routes, (list, tuple)):
                    print(f"  ERROR: city.routes is not an iterable (list/tuple). It's {type(city.routes).__name__}.")
                    raise TypeError("city.routes must be a list or tuple of routes.")

                for i, r in enumerate(city.routes):
                    print(
                        f"    Inspecting route {i}: type={type(r).__name__}, bearing={getattr(r, 'bearing', 'N/A')}, month={getattr(r, 'month', 'N/A')}")
                    if isinstance(r, MonthlyDataRoute) and r.bearing == bearing and r.month == month:
                        found_route = r
                        print(f"    Found existing route for bearing {bearing}, month {month}.")
                        break
                print(
                    f"  Finished searching for existing route for bearing {bearing}.")  # Новый отладочный вывод, сразу после цикла

                if not found_route:
                    found_route = MonthlyDataRoute(bearing=bearing, year=0, month=month)
                    city.routes.append(found_route)
                    print(
                        f"    Created new route for bearing {bearing}, month {month}. city.routes new size: {len(city.routes)}.")  # Отладочный вывод

                # Генерируем точки для маршрута
                origin_lat, origin_lon = city.coordinates
                print(f"    Generating points for {len(distances)} distances from {origin_lat}, {origin_lon}.")
                for distance in distances:
                    if distance not in found_route.distances:
                        found_route.distances.append(distance)
                    new_lat, new_lon = calculate_new_coordinates(origin_lat, origin_lon, distance, bearing)
                    found_route.points[distance] = new_lat, new_lon

                routes_to_process[bearing] = found_route
                print(f"  Finished processing bearing: {bearing}. Route added to routes_to_process.")

            print("Finished generating points for all bearings.")

            self.current_month = month
            self.data_fetcher = fetcher
            self.exporter = exporter

            print("About to obtain data from fetcher...")
            all_data = self.obtain_data(routes_to_process)
            print("Data obtained. About to export...")
            self.exporter.export(city, all_data)
            print("Data exported. Analysis.run finished.")
            return all_data
        except Exception as e:
            error_message = f"Error in Analysis.run: {e}"
            print(error_message)
            traceback.print_exc()
            raise

    def obtain_data(self, routes_by_bearing: dict[int, MonthlyDataRoute]) -> list[dict[str, Any]]:
        print("Analysis.obtain_data method started.")
        try:
            all_data = []
            for year in config.YEARS_TO_ANALYZE:
                print(f"  Fetching data for year: {year}")
                for route in routes_by_bearing.values():
                    route.year = year

                print(f"  Calling data_fetcher.fetch for year {year} and month {self.current_month}.")
                monthly_data = self.data_fetcher.fetch(routes_by_bearing, year, self.current_month)
                all_data.extend(monthly_data)
                print(f"  Received {len(monthly_data)} records for year {year}.")
            print("Analysis.obtain_data method finished.")
            return all_data
        except Exception as e:
            error_message = f"Error in Analysis.obtain_data: {e}"
            print(error_message)
            traceback.print_exc()
            raise