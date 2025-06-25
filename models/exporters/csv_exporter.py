from typing import Any

import pandas as pd

import config
from models import City, Exporter


class CsvExporter(Exporter):
    def __init__(self):
        pass

    def export(self, city: City, data: list[dict[str, Any]]):
        if not data:
            print(f"No data to export for {city.name}.")
            return

        df = pd.DataFrame(data)

        required_cols = ['year', 'bearing', 'distance', 'no2_umol_m2', 'month']
        if not all(col in df.columns for col in required_cols):
            print(
                f"Missing required columns for export in {city.name}'s data. Required: {required_cols}, Present: {df.columns.tolist()}")
            return

        export_month_num = data[0]['month']
        export_month_name = config.MONTHS.get(export_month_num, f"month_{export_month_num}")

        # Map bearing numbers to names BEFORE pivoting
        df['bearing'] = df['bearing'].map(config.BEARINGS)

        df_pivot = df.pivot_table(
            index=['year', 'bearing'],
            columns='distance',
            values='no2_umol_m2'
        ).reset_index()
        df_pivot = df_pivot.rename_axis(columns=None)

        # Rename columns 'year' and 'bearing' to 'Год' and 'Направление'
        df_pivot = df_pivot.rename(columns={'year': 'Год', 'bearing': 'Направление'})

        output_file_name = f"no2_{export_month_name}_{city.name}.csv"

        df_pivot.to_csv(config.EXPORTS_FOLDER + '/' + output_file_name, index=False, decimal=",", sep="\t")
        print(f"Exported {len(df_pivot)} records to {output_file_name}")
