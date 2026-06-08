"""
Mode-aware data source wrappers for PierWatch.

Pages should import from here instead of calling loaders directly.
This module routes to local Excel loaders (DATA_MODE='local') or
demo CSV loaders (DATA_MODE='demo') based on the PIERWATCH_DATA_MODE env var.

Usage in pages:
    from src.data_sources import (
        source_cache_key, show_mode_banner, is_data_available,
        get_river_stage_data, get_gps_data, get_primary_device_data,
        get_device_sheet_data, get_pp15_filter_data, get_sensor_quality_data,
    )
    _mode, _ck_path, _ck_mtime = source_cache_key()
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from src.config import DATA_MODE, DATA_DEMO, EXCEL_PATH


def is_data_available() -> bool:
    """True if data is accessible for the current DATA_MODE."""
    if DATA_MODE == "demo":
        return (DATA_DEMO / "demo_river_stage.csv").exists()
    return EXCEL_PATH.exists()


def source_cache_key() -> tuple[str, str, float]:
    """
    Return (data_mode, path_hint, mtime) for use as @st.cache_data keys.
    Include DATA_MODE so switching modes invalidates cached results.
    """
    if DATA_MODE == "demo":
        p = DATA_DEMO / "demo_river_stage.csv"
        mt = float(p.stat().st_mtime) if p.exists() else 0.0
        return DATA_MODE, str(DATA_DEMO), mt
    mt = float(EXCEL_PATH.stat().st_mtime) if EXCEL_PATH.exists() else 0.0
    return DATA_MODE, str(EXCEL_PATH), mt


def show_mode_banner() -> None:
    """Show an info/warning banner for the current data mode (call near page top)."""
    if DATA_MODE == "demo":
        st.info(
            "**Demo mode:** using synthetic sample data. "
            "Not official monitoring records. "
            "Run with `PIERWATCH_DATA_MODE=local` and provide the R1 workbook for full analysis."
        )


def get_river_stage_data() -> pd.DataFrame:
    if DATA_MODE == "demo":
        from src.demo_data_loader import load_demo_river_stage
        return load_demo_river_stage()
    from src.data_loader import load_river_stage
    return load_river_stage(str(EXCEL_PATH))


def get_gps_data() -> pd.DataFrame:
    if DATA_MODE == "demo":
        from src.demo_data_loader import load_demo_gps_data
        return load_demo_gps_data()
    from src.data_loader import load_gps_data
    return load_gps_data(str(EXCEL_PATH))


def get_primary_device_data() -> pd.DataFrame:
    if DATA_MODE == "demo":
        from src.demo_data_loader import load_all_demo_primary_device_data
        return load_all_demo_primary_device_data()
    from src.data_loader import load_all_primary_device_data
    return load_all_primary_device_data(str(EXCEL_PATH))


def get_device_sheet_data(device_id: str) -> pd.DataFrame:
    if DATA_MODE == "demo":
        from src.demo_data_loader import load_demo_device_sheet
        return load_demo_device_sheet(device_id)
    from src.data_loader import load_device_sheet
    sheet_map = {"W2": "W2", "PP15": "PP 15", "E2": "E2", "E3": "E3"}
    sheet_name = sheet_map.get(device_id, device_id)
    return load_device_sheet(str(EXCEL_PATH), sheet_name, device_id)


def get_pp15_filter_data() -> pd.DataFrame:
    if DATA_MODE == "demo":
        from src.demo_data_loader import load_demo_device_sheet
        return load_demo_device_sheet("PP15")
    from src.data_loader import load_pp15_filter
    return load_pp15_filter(str(EXCEL_PATH))


def get_sensor_quality_data() -> pd.DataFrame:
    """Compute sensor quality metrics; routes to demo or local mode."""
    if DATA_MODE == "demo":
        from src.demo_data_loader import (
            load_demo_river_stage, load_demo_gps_data, load_all_demo_primary_device_data,
        )
        from src.sensor_quality import compute_series_quality
        rows = []
        river = load_demo_river_stage()
        rows.append(compute_series_quality(river, "timestamp", ["stage_ft"],
                                           source_name="River Stage", sensor_id="stage_ft"))
        gps = load_demo_gps_data()
        for pier in sorted(gps["pier_id"].unique()):
            g = gps[gps["pier_id"] == pier]
            for col in ["longitudinal_in", "transverse_in"]:
                rows.append(compute_series_quality(
                    g, "timestamp", [col],
                    source_name="GPS",
                    sensor_id=f"{pier}_{col.replace('_in', '')}",
                ))
        devices = load_all_demo_primary_device_data()
        for device_id in sorted(devices["device_id"].unique()):
            dev = devices[devices["device_id"] == device_id]
            for col in ["measured_expansion_in", "temperature_f", "corrected_expansion_in"]:
                label = col.replace("_in", "").replace("_f", "").replace("_", " ")
                rows.append(compute_series_quality(
                    dev, "timestamp", [col],
                    source_name="Primary Device",
                    sensor_id=f"{device_id} {label}",
                    expected_freq="6h",
                ))
        return pd.DataFrame(rows) if rows else pd.DataFrame()
    from src.sensor_quality import compute_all_sensor_quality
    return compute_all_sensor_quality(str(EXCEL_PATH))
