import math
from typing import cast, Any

import ee
import pandas as pd

import config
from models import City, MonthlyDataRoute, PointsRoute


def initialize_ee(project_id: str):
    try:
        ee.Initialize(project=project_id)
    except Exception:
        # ee.Authenticate()
        # ee.Initialize(project=project_id)
        raise


def calculate_new_coordinates(lat: float, lon: float, distance_km: float, bearing_deg: float) -> tuple[float, float]:
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


def create_analysis_points(city: City, distances: list[int],
                           bearings: list[int]):
    origin_lat, origin_lon = city.coordinates
    for bearing in bearings:
        route = MonthlyDataRoute(bearing=bearing)
        for distance in distances:
            route.distances.append(distance)
            new_lat, new_lon = calculate_new_coordinates(origin_lat, origin_lon, distance, bearing)
            route.points[distance] = new_lat, new_lon
        city.routes[bearing] = route


def fetch_monthly_no2_data(city: City, year: int, month: int) -> list[dict[str, Any]]:
    start_date = ee.Date.fromYMD(year, month, 1)
    end_date = start_date.advance(1, 'month')

    monthly_mean_image = (
        ee.ImageCollection(config.GEE_NO2_COLLECTION)
        .select("NO2_column_number_density")
        .filterDate(start_date, end_date)
        .mean()
    )

    points = []
    for route in city.routes.values():
        for distance in route.distances:
            lat, lon = cast(PointsRoute, route).points[distance]
            point = ee.Geometry.Point(lon, lat)
            feature = ee.Feature(point, {'bearing': route.bearing, 'distance': distance})
            points.append(feature)

    sampled_features = monthly_mean_image.sampleRegions(
        collection=ee.FeatureCollection(points),
        scale=config.GEE_COLLECTION_SCALE,
        geometries=True
    )

    try:
        results_info = sampled_features.getInfo()['features']
    except Exception:
        raise

    processed_results = []
    for feature in results_info:
        props = feature['properties']
        no2_value = props.get("NO2_column_number_density")
        no2_umol_m2 = no2_value * config.MOL_PER_M2_TO_UMOL_PER_M2 if no2_value is not None else None
        bearing = props['bearing']
        distance = props['distance']
        cast(MonthlyDataRoute, city.routes[bearing]).densities[distance] = no2_umol_m2

        processed_results.append({
            'year': year,
            'bearing': bearing,
            'distance': distance,
            'no2_umol_m2': no2_umol_m2
        })
    return processed_results


def main():
    city = City(name=config.CITY_NAME_CHITA, coordinates=config.CITY_COORDINATES_CHITA, routes={})
    initialize_ee(config.G_PROJECT_ID)

    create_analysis_points(city, config.DISTANCES_KM, config.BEARINGS_DEG)

    all_data = []
    for year in config.YEARS_TO_ANALYZE:
        monthly_data = fetch_monthly_no2_data(city, year, config.MONTH_TO_ANALYZE)
        all_data.extend(monthly_data)

    if not all_data:
        return

    df = pd.DataFrame(all_data)
    df = df.pivot_table(
        index=['year', 'bearing'],
        columns='distance',
        values='no2_umol_m2'
    ).reset_index()
    df = df.rename_axis(columns=None)

    output_file_name = f"no2_february_{config.CITY_NAME_CHITA}.csv"

    df.to_csv(config.EXPORTS_FOLDER + '/' + output_file_name, index=False, decimal=",", sep="\t")


if __name__ == "__main__":
    main()