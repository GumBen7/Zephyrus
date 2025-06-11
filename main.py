import ee
import pandas as pd
import math
from typing import Tuple, List, Dict, Any

G_PROJECT_ID = 'plated-monolith-425409-f3'
CITY_NAME_CHITA = "chita"
CITY_COORDINATES_CHITA = (52.033635, 113.501049)
DISTANCES_KM = [10, 20, 30, 50, 100, 150, 200]
BEARINGS_DEG = [0, 45, 90, 135, 180, 225, 270, 315]
YEARS_TO_ANALYZE = [2019, 2020, 2021, 2022, 2023, 2024]
MONTH_TO_ANALYZE = 2
EARTH_RADIUS_KM = 6371
GEE_NO2_COLLECTION = "COPERNICUS/S5P/OFFL/L3_NO2"
GEE_COLLECTION_SCALE = 1113.2
MOL_PER_M2_TO_UMOL_PER_M2 = 10 ** 6


def initialize_ee(project_id: str):
    try:
        ee.Initialize(project=project_id)
    except Exception as e:
        # ee.Authenticate()
        # ee.Initialize(project=project_id)
        raise


def calculate_new_coordinates(lat: float, lon: float, distance_km: float, bearing_deg: float) -> Tuple[float, float]:
    lat_rad = math.radians(lat)
    lon_rad = math.radians(lon)
    bearing_rad = math.radians(bearing_deg)
    delta = distance_km / EARTH_RADIUS_KM

    new_lat_rad = math.asin(
        math.sin(lat_rad) * math.cos(delta) +
        math.cos(lat_rad) * math.sin(delta) * math.cos(bearing_rad)
    )
    new_lon_rad = lon_rad + math.atan2(
        math.sin(bearing_rad) * math.sin(delta) * math.cos(lat_rad),
        math.cos(delta) - math.sin(lat_rad) * math.sin(new_lat_rad)
    )
    return math.degrees(new_lat_rad), math.degrees(new_lon_rad)


def create_analysis_points(origin: Tuple[float, float], distances: List[float],
                           bearings: List[float]) -> ee.FeatureCollection:
    points = []
    origin_lat, origin_lon = origin
    for bearing in bearings:
        for distance in distances:
            new_lat, new_lon = calculate_new_coordinates(origin_lat, origin_lon, distance, bearing)
            point = ee.Geometry.Point(new_lon, new_lat)
            feature = ee.Feature(point, {'bearing': bearing, 'distance': distance})
            points.append(feature)
    return ee.FeatureCollection(points)


def fetch_monthly_no2_data(year: int, month: int, points_fc: ee.FeatureCollection) -> List[Dict[str, Any]]:
    start_date = ee.Date.fromYMD(year, month, 1)
    end_date = start_date.advance(1, 'month')

    monthly_mean_image = (
        ee.ImageCollection(GEE_NO2_COLLECTION)
        .select("NO2_column_number_density")
        .filterDate(start_date, end_date)
        .mean()
    )

    sampled_features = monthly_mean_image.sampleRegions(
        collection=points_fc,
        scale=GEE_COLLECTION_SCALE,
        geometries=True
    )

    try:
        results_info = sampled_features.getInfo()['features']
    except Exception as e:
        return []

    processed_results = []
    for feature in results_info:
        props = feature['properties']
        no2_value = props.get("NO2_column_number_density")

        processed_results.append({
            'year': year,
            'bearing': props['bearing'],
            'distance': props['distance'],
            'no2_umol_m2': no2_value * MOL_PER_M2_TO_UMOL_PER_M2 if no2_value is not None else None
        })
    return processed_results


def main():
    initialize_ee(G_PROJECT_ID)

    analysis_points = create_analysis_points(CITY_COORDINATES_CHITA, DISTANCES_KM, BEARINGS_DEG)

    all_data = []
    for year in YEARS_TO_ANALYZE:
        monthly_data = fetch_monthly_no2_data(year, MONTH_TO_ANALYZE, analysis_points)
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

    output_file_name = f"no2_february_{CITY_NAME_CHITA}_refactored.csv"

    df.to_csv(output_file_name, index=False, decimal=",", sep="\t")


if __name__ == "__main__":
    main()