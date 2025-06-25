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

    def run(self, city: City, bearings: list[int], month: int, distances: list[int], fetcher: Fetcher, exporter: Exporter) -> list[dict[str, Any]]:
        print("Analysis.run method started.")
        try:
            self.current_city = city
            if not self.cities.get(city.id):
                self.cities[city.id] = city
                print(f"Added {city.name} to cities cache.")

            all_flat_data_for_export = [] # Сюда будут собираться все данные для экспорта

            self.current_month = month # Устанавливаем текущий месяц для obtain_data
            self.data_fetcher = fetcher
            self.exporter = exporter

            # Мы будем получать данные для КАЖДОГО года и создавать отдельный MonthlyDataRoute
            for bearing in bearings:
                print(f"  Processing bearing: {bearing}")
                origin_lat, origin_lon = city.coordinates

                # Подготовим points для всех дистанций один раз для данного азимута
                points_for_current_bearing = {}
                for distance in distances:
                    new_lat, new_lon = calculate_new_coordinates(origin_lat, origin_lon, distance, bearing)
                    points_for_current_bearing[distance] = new_lat, new_lon
                print(f"    Generated points for all distances for bearing {bearing}.")

                for year in config.YEARS_TO_ANALYZE:
                    print(f"    Fetching data for year: {year}, bearing: {bearing}, month: {month}")

                    # Создаем НОВЫЙ MonthlyDataRoute для каждого года, азимута и месяца
                    monthly_data_route = MonthlyDataRoute(
                        bearing=bearing,
                        year=year,
                        month=month,
                        distances=list(distances), # Копируем distances в новый объект
                        points=points_for_current_bearing.copy() # Копируем сгенерированные точки
                    )

                    # Получаем данные конкретно для этого маршрута (года, азимута, месяца)
                    # GeeFetcher.fetch теперь принимает список из ОДНОГО маршрута для обработки
                    # или мы можем передать его как часть словаря, как раньше, но с одним элементом
                    routes_for_fetch = {bearing: monthly_data_route}

                    monthly_data = self.data_fetcher.fetch(routes_for_fetch, year, month)

                    # Обновляем densities в только что созданном MonthlyDataRoute
                    for record in monthly_data:
                        dist = record['distance']
                        no2_val = record['no2_umol_m2']
                        monthly_data_route.densities[dist] = no2_val

                    # Добавляем этот *уникальный* MonthlyDataRoute в список маршрутов города
                    city.routes.append(monthly_data_route)
                    all_flat_data_for_export.extend(monthly_data) # Собираем все плоские данные для экспорта

                    print(f"    Finished fetching for year {year}, bearing {bearing}, month {month}. City routes size: {len(city.routes)}")

            print("Finished processing all bearings and years.")

            print("Data obtained. About to export...")
            self.exporter.export(city, all_flat_data_for_export) # Экспорт всех данных, которые были получены
            print("Data exported. Analysis.run finished.")
            return all_flat_data_for_export # Возвращаем данные для дальнейшего использования
        except Exception as e:
            error_message = f"Error in Analysis.run: {e}"
            print(error_message)
            traceback.print_exc()
            raise