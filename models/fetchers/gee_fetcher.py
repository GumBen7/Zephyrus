from typing import Any, cast

import ee

import config
from .. import City
from ..fetcher import Fetcher
from ..routes import PointsRoute, MonthlyDataRoute


class GeeFetcher(Fetcher):
    def __init__(self):
        self._initialize_ee()

    def _initialize_ee(self):
        try:
            ee.Initialize(project=config.G_PROJECT_ID)
            print("Earth Engine initialized successfully.")
        except Exception as e:
            print(e)
            # ee.Authenticate()
            # ee.Initialize(project=project_id)
            raise

    def fetch(self, city: City, year: int, month: int) -> list[dict[str, Any]]:
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
        except Exception as e :
            print(e)
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