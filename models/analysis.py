import math
import traceback
from typing import Any, Optional

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
        self.cities: dict[str, City] = {}
        self.current_city: Optional[City] = None
        self.current_month: int | None = None
        self.data_fetcher: Optional[Fetcher] = None
        self.exporter: Optional[Exporter] = None
        print("Analysis model initialized.")

    def export_all_loaded_data(self, exporter: Exporter):
        print("Analysis.export_all_loaded_data started.")
        if not self.cities:
            print("No cities data loaded for export.")
            raise ValueError("Нет загруженных данных для экспорта.")

        for city_id, city_obj in self.cities.items():
            data_by_month: dict[int, list[dict[str, Any]]] = {}

            for route in city_obj.routes:
                if isinstance(route, MonthlyDataRoute) and route.densities:
                    for dist, density in route.densities.items():
                        if not math.isnan(density):
                            if route.month not in data_by_month:
                                data_by_month[route.month] = []
                            data_by_month[route.month].append({
                                'city_id': city_obj.id,
                                'city_name': city_obj.name,
                                'year': route.year,
                                'month': route.month,
                                'bearing': route.bearing,
                                'distance': dist,
                                'no2_umol_m2': density
                            })

            for month_num, month_data in data_by_month.items():
                print(f"  Exporting data for {city_obj.name}, Month: {config.MONTHS.get(month_num, str(month_num))}")
                exporter.export(city_obj, month_data)

        print("Analysis.export_all_loaded_data finished.")

    def run(self, city: City, bearings: list[int], month: int, distances: list[int], fetcher: Fetcher,
            exporter: Exporter) -> list[dict[str, Any]]:
        print("Analysis.run method started.")
        try:
            self.current_city = city
            self.data_fetcher = fetcher
            self.exporter = exporter

            if not self.cities.get(city.id):
                self.cities[city.id] = city
                print(f"Added {city.name} to cities cache.")

            self.current_month = month

            for bearing in bearings:
                print(f"  Processing bearing: {bearing}")
                origin_lat, origin_lon = city.coordinates

                points_for_current_bearing = {}
                for distance in distances:
                    new_lat, new_lon = calculate_new_coordinates(origin_lat, origin_lon, distance, bearing)
                    points_for_current_bearing[distance] = new_lat, new_lon
                print(f"    Generated points for all distances for bearing {bearing}.")

                for year in config.YEARS_TO_ANALYZE:
                    print(f"    Fetching data for year: {year}, bearing: {bearing}, month: {month}")

                    temp_monthly_data_route = MonthlyDataRoute(
                        city_id=city.id,
                        bearing=bearing,
                        year=year,
                        month=month,
                        distances=list(distances),
                        points=points_for_current_bearing.copy()
                    )

                    routes_for_fetch = {bearing: temp_monthly_data_route}
                    monthly_data = fetcher.fetch(routes_for_fetch, year, month)

                    for record in monthly_data:
                        dist = record['distance']
                        no2_val = record['no2_umol_m2']
                        temp_monthly_data_route.densities[dist] = no2_val

                    found_existing_route = False
                    for i, existing_route in enumerate(city.routes):
                        if (isinstance(existing_route, MonthlyDataRoute) and
                                existing_route.city_id == temp_monthly_data_route.city_id and
                                existing_route.bearing == temp_monthly_data_route.bearing and
                                existing_route.year == temp_monthly_data_route.year and
                                existing_route.month == temp_monthly_data_route.month):
                            city.routes[i] = temp_monthly_data_route
                            found_existing_route = True
                            print(
                                f"    Overwrote existing MonthlyDataRoute for year {year}, bearing {bearing}, month {month}.")
                            break

                    if not found_existing_route:
                        city.routes.append(temp_monthly_data_route)
                        print(f"    Added new MonthlyDataRoute for year {year}, bearing {bearing}, month {month}.")

                    print(
                        f"    Finished processing for year {year}, bearing {bearing}, month {month}. City routes size: {len(city.routes)}")

            print("Finished processing all bearings and years in Analysis.run.")

            return []
        except Exception as e:
            error_message = f"Error in Analysis.run: {e}"
            print(error_message)
            traceback.print_exc()
            raise
