import traceback
from typing import Any, cast

import ee

import config
from models import Fetcher
from models.routes import MonthlyDataRoute, PointsRoute


class GeeFetcher(Fetcher):
    def __init__(self):
        self._initialize_ee()

    def _initialize_ee(self):
        try:
            ee.Initialize(project=config.G_PROJECT_ID)
            print("Earth Engine initialized successfully.")
        except Exception as e:
            print(e)
            raise

    def fetch(self, routes_by_bearing: dict[int, MonthlyDataRoute], year: int, month: int) -> list[dict[str, Any]]:
        print(f"GeeFetcher.fetch called for year={year}, month={month}")
        start_date = ee.Date.fromYMD(year, month, 1)
        end_date = start_date.advance(1, 'month')
        print(f"Fetching NO2 data for {start_date.getInfo()} to {end_date.getInfo()}")

        monthly_mean_image = (
            ee.ImageCollection(config.GEE_NO2_COLLECTION)
            .select("NO2_column_number_density")
            .filterDate(start_date, end_date)
            .mean()
        )
        print("Image collection filtered and mean calculated.")

        points = []
        for route in routes_by_bearing.values():
            for distance in route.distances:
                lat, lon = cast(PointsRoute, route).points[distance]
                point = ee.Geometry.Point(lon, lat)
                feature = ee.Feature(point, {'bearing': route.bearing, 'distance': distance})
                points.append(feature)
        print(f"Generated {len(points)} points for sampling.")

        sampled_features = monthly_mean_image.sampleRegions(
            collection=ee.FeatureCollection(points),
            scale=config.GEE_COLLECTION_SCALE,
            geometries=True
        )

        print("SampleRegions operation defined. About to call getInfo()...")

        try:
            results_info = sampled_features.getInfo()['features']
            print("getInfo() call completed successfully.")
        except Exception as e:
            print(e)
            traceback.print_exc()
            raise

        processed_results = []
        for feature in results_info:
            props = feature['properties']
            no2_value = props.get("NO2_column_number_density")
            no2_umol_m2 = no2_value * config.MOL_PER_M2_TO_UMOL_PER_M2 if no2_value is not None else None
            bearing = props['bearing']
            distance = props['distance']
            routes_by_bearing[bearing].densities[distance] = no2_umol_m2

            processed_results.append({
                'year': year,
                'bearing': bearing,
                'distance': distance,
                'no2_umol_m2': no2_umol_m2
            })
        return processed_results
