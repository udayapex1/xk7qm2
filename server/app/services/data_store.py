from __future__ import annotations

from pathlib import Path

import pandas as pd


DATA_DIR = Path(__file__).resolve().parents[2] / "data"


class DataStore:
    def __init__(self, actuals: pd.DataFrame, forecasts: pd.DataFrame) -> None:
        """Normalize, deduplicate, and retain the snapshot tables in memory."""
        self.actuals = actuals.copy()
        self.forecasts = forecasts.copy()
        self.actuals["startTime"] = pd.to_datetime(self.actuals["startTime"], utc=True)
        self.forecasts["startTime"] = pd.to_datetime(self.forecasts["startTime"], utc=True)
        self.forecasts["publishTime"] = pd.to_datetime(self.forecasts["publishTime"], utc=True)
        self.actuals["generation"] = pd.to_numeric(self.actuals["generation"], errors="raise")
        self.forecasts["generation"] = pd.to_numeric(self.forecasts["generation"], errors="raise")
        self.actuals = (
            self.actuals.drop_duplicates(subset=["startTime"], keep="last")
            .sort_values("startTime")
            .reset_index(drop=True)
        )
        self.forecasts = (
            self.forecasts.drop_duplicates(subset=["startTime", "publishTime"], keep="last")
            .sort_values(["startTime", "publishTime"])
            .reset_index(drop=True)
        )

    @classmethod
    def from_csv(cls, data_dir: Path = DATA_DIR) -> "DataStore":
        """Load both committed snapshot CSVs from a data directory."""
        actual_path = data_dir / "actuals.csv"
        forecast_path = data_dir / "forecasts.csv"
        if not actual_path.is_file() or not forecast_path.is_file():
            raise FileNotFoundError(
                f"Snapshot is missing; expected {actual_path} and {forecast_path}. "
                "Run `python server/scripts/fetch_data.py`."
            )
        return cls(pd.read_csv(actual_path), pd.read_csv(forecast_path))

    def actuals_for(self, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
        """Return actual records in the half-open UTC timestamp range."""
        return self.actuals.loc[
            (self.actuals["startTime"] >= start) & (self.actuals["startTime"] < end)
        ].copy()

    def forecasts_for(self, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
        """Return forecast vintages targeting the half-open UTC range."""
        return self.forecasts.loc[
            (self.forecasts["startTime"] >= start) & (self.forecasts["startTime"] < end)
        ].copy()

    def forecast_vintages(self, target: pd.Timestamp) -> pd.DataFrame:
        """Return all forecast vintages for one exact UTC target timestamp."""
        return self.forecasts.loc[self.forecasts["startTime"] == target].copy()


def load_store() -> DataStore:
    """Load the process-wide snapshot store."""
    return DataStore.from_csv()
