from typing import Any

import pandas as pd

import config
from .. import City
from ..exporter import Exporter


class CsvExporter(Exporter):
    def __init__(self):
        pass

    def export(self, city: City, data: list[dict[str, Any]]):
        df = pd.DataFrame(data)
        df = df.pivot_table(
            index=['year', 'bearing'],
            columns='distance',
            values='no2_umol_m2'
        ).reset_index()
        df = df.rename_axis(columns=None)

        output_file_name = f"no2_february_{city.id}.csv"

        df.to_csv(config.EXPORTS_FOLDER + '/' + output_file_name, index=False, decimal=",", sep="\t")
