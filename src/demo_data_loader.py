"""Demo-mode CSV loaders. Return DataFrames with the same column schema as local-mode loaders."""
from __future__ import annotations
import pandas as pd
from src.config import DATA_DEMO


def load_demo_river_stage() -> pd.DataFrame:
    df = pd.read_csv(DATA_DEMO / "demo_river_stage.csv")
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.dropna(subset=["timestamp", "stage_ft"]).sort_values("timestamp").reset_index(drop=True)
    return df


def load_demo_gps_data() -> pd.DataFrame:
    df = pd.read_csv(DATA_DEMO / "demo_gps_data.csv")
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.dropna(subset=["timestamp"]).sort_values("timestamp").reset_index(drop=True)
    return df


def load_demo_device_data() -> pd.DataFrame:
    df = pd.read_csv(DATA_DEMO / "demo_device_data.csv")
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.dropna(subset=["timestamp"]).sort_values(["device_id", "timestamp"]).reset_index(drop=True)
    return df


def load_all_demo_primary_device_data() -> pd.DataFrame:
    return load_demo_device_data()


def load_demo_device_sheet(device_id: str) -> pd.DataFrame:
    df = load_demo_device_data()
    return df[df["device_id"] == device_id].copy().reset_index(drop=True)
