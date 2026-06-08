#!/usr/bin/env python3
"""
Generate synthetic demo data for PierWatch public / portfolio mode.

IMPORTANT: These files are NOT copies of the real confidential monitoring data.
All values are synthetic, shifted, and simplified for demonstration purposes only.
They are not official monitoring records and should not be used for engineering decisions.

Output files (data/demo/):
  demo_river_stage.csv   — synthetic daily river stage, 2000-2026
  demo_gps_data.csv      — synthetic GPS pier positions, 2022-2026
  demo_device_data.csv   — synthetic jointmeter records, 2004-2026 (PP15, E2, E3 only; W2 ends 2019)
  demo_events.csv        — pre-computed low-water events from synthetic river stage

Usage:
  python scripts/create_demo_data.py

After running, set PIERWATCH_DATA_MODE=demo to use these files (demo loaders not yet
wired into the full app — see docs/PUBLIC_DEMO_MODE.md for Phase 2 integration).
"""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DEMO_DIR = ROOT / "data" / "demo"
DEMO_DIR.mkdir(parents=True, exist_ok=True)

RNG = np.random.default_rng(42)


# ── 1. Synthetic river stage (2000-01-01 to 2026-03-31, daily 08:00) ─────────

def _make_river_stage() -> pd.DataFrame:
    dates = pd.date_range("2000-01-01 08:00", "2026-03-31 08:00", freq="D")
    n = len(dates)

    # Seasonal base: peaks ~spring, lows ~fall
    day_of_year = dates.day_of_year.to_numpy()
    seasonal = 28.0 + 16.0 * np.sin(2 * math.pi * (day_of_year - 90) / 365)
    noise = RNG.normal(0, 3.5, n)
    stage = seasonal + noise

    # Insert synthetic low-water events (representative patterns, not real data)
    def _dip(dates_arr, center_date: str, depth_ft: float, width_days: int = 60):
        center = pd.Timestamp(center_date)
        days_from = (dates_arr - center).days
        bump = np.where(np.abs(days_from) < width_days,
                        -depth_ft * np.exp(-0.5 * (days_from / (width_days / 2.5)) ** 2),
                        0.0)
        return bump

    stage += _dip(dates, "2022-10-01", depth_ft=27.0, width_days=55)  # 2022-like major event
    stage += _dip(dates, "2023-11-15", depth_ft=22.0, width_days=70)  # 2023 moderate
    stage += _dip(dates, "2025-09-20", depth_ft=25.0, width_days=50)  # 2025 moderate
    stage += _dip(dates, "2012-09-01", depth_ft=18.0, width_days=60)  # older event
    stage += _dip(dates, "2016-10-15", depth_ft=15.0, width_days=45)

    stage = np.clip(stage, -3.0, 65.0)

    df = pd.DataFrame({"timestamp": dates, "stage_ft": np.round(stage, 2)})
    return df


river_df = _make_river_stage()
river_df.to_csv(DEMO_DIR / "demo_river_stage.csv", index=False)
print(f"  demo_river_stage.csv: {len(river_df):,} rows | "
      f"{river_df['stage_ft'].min():.1f} to {river_df['stage_ft'].max():.1f} ft")


# ── 2. Synthetic GPS pier positions (2022-06-01 to 2026-03-03, ~12h intervals) ─

def _make_gps_data() -> pd.DataFrame:
    piers = {
        "E1": {"n": 1512, "end": "2026-02-28"},
        "E2": {"n": 3434, "end": "2026-03-03"},
        "E3": {"n": 3484, "end": "2026-03-03"},
    }
    frames = []
    for pier_id, cfg in piers.items():
        ts = pd.date_range("2022-06-01", cfg["end"], periods=cfg["n"])

        # Base drift: slow long-term drift + noise
        t_norm = np.linspace(0, 1, len(ts))

        # 2022 event: large jump around t=0.05
        event_2022 = 0.05
        e1_mag = {"E1": 4.1, "E2": 3.7, "E3": -0.3}[pier_id]
        jump_2022 = e1_mag * (1 / (1 + np.exp(-80 * (t_norm - event_2022))))

        # 2025 event: smaller jump around t=0.85
        e_2025_mag = {"E1": 0.9, "E2": 0.55, "E3": -0.1}[pier_id]
        jump_2025 = e_2025_mag * (1 / (1 + np.exp(-80 * (t_norm - 0.85))))

        long_in = jump_2022 + jump_2025 + RNG.normal(0, 0.05, len(ts))
        trans_in = RNG.normal(0, 0.03, len(ts)) + 0.1 * np.sin(2 * math.pi * t_norm * 4)

        frames.append(pd.DataFrame({
            "timestamp": ts,
            "pier_id": pier_id,
            "longitudinal_in": np.round(long_in, 4),
            "transverse_in": np.round(trans_in, 4),
        }))

    df = pd.concat(frames, ignore_index=True).sort_values("timestamp").reset_index(drop=True)
    return df


gps_df = _make_gps_data()
gps_df.to_csv(DEMO_DIR / "demo_gps_data.csv", index=False)
print(f"  demo_gps_data.csv: {len(gps_df):,} rows | piers: {sorted(gps_df['pier_id'].unique())}")


# ── 3. Synthetic device data (6h intervals) ───────────────────────────────────

def _make_device_data() -> pd.DataFrame:
    # PP15 and E2/E3: 2004-08-27 to 2026-04-24
    # W2: 2004-08-27 to 2019-07-08  (monitoring ended)
    device_cfg = {
        "PP15": {"start": "2004-08-27", "end": "2026-04-24", "base_exp": -2.5, "exp_range": 1.5},
        "E2":   {"start": "2004-08-27", "end": "2026-04-24", "base_exp": -1.8, "exp_range": 1.2},
        "E3":   {"start": "2004-08-27", "end": "2026-04-24", "base_exp": -2.0, "exp_range": 1.3},
        "W2":   {"start": "2004-08-27", "end": "2019-07-08", "base_exp": -1.5, "exp_range": 1.0},
    }
    frames = []
    for device_id, cfg in device_cfg.items():
        ts = pd.date_range(cfg["start"], cfg["end"], freq="6h")
        n = len(ts)
        day_of_year = ts.day_of_year.to_numpy()

        # Temperature: seasonal, 50-90 °F + noise
        temp_f = 70 + 20 * np.sin(2 * math.pi * (day_of_year - 90) / 365) + RNG.normal(0, 4, n)
        temp_f = np.clip(temp_f, 30, 105)

        # Delta temperature
        delta_temp = np.gradient(temp_f)

        # Thermal expansion coefficient ~0.03 in/°F (span 440 ft * alpha)
        alpha = -0.035
        measured = cfg["base_exp"] + alpha * (temp_f - 70) + RNG.normal(0, 0.02, n)
        measured = measured + cfg["exp_range"] * 0.1 * np.cumsum(RNG.normal(0, 0.0005, n))
        calculated = alpha * (temp_f - 70)
        corrected = measured - calculated

        # Add ~3% missing (sentinel → NaN already handled by loader)
        miss_mask = RNG.random(n) < 0.03
        measured[miss_mask] = np.nan
        corrected[miss_mask] = np.nan

        frames.append(pd.DataFrame({
            "timestamp": ts,
            "device_id": device_id,
            "measured_expansion_in": np.round(measured, 4),
            "temperature_f": np.round(temp_f, 2),
            "delta_temperature_f": np.round(delta_temp, 4),
            "calculated_expansion_in": np.round(calculated, 4),
            "corrected_expansion_in": np.round(corrected, 4),
        }))

    df = pd.concat(frames, ignore_index=True).sort_values(["device_id", "timestamp"]).reset_index(drop=True)
    return df


device_df = _make_device_data()
device_df.to_csv(DEMO_DIR / "demo_device_data.csv", index=False)
print(f"  demo_device_data.csv: {len(device_df):,} rows | "
      f"devices: {sorted(device_df['device_id'].unique())}")


# ── 4. Pre-computed events (from synthetic river stage) ───────────────────────
#    Simple threshold-based detection so demo mode doesn't need the full event detector.

def _make_events(river: pd.DataFrame) -> pd.DataFrame:
    below_12 = river["stage_ft"] < 12.0
    # Find contiguous runs below 12 ft (at least 7 days long)
    events = []
    in_event = False
    start_idx = 0
    for i, flag in enumerate(below_12):
        if flag and not in_event:
            in_event = True
            start_idx = i
        elif not flag and in_event:
            in_event = False
            duration = i - start_idx
            if duration >= 7:
                seg = river.iloc[start_idx:i]
                events.append({
                    "start_date": str(seg["timestamp"].iloc[0].date()),
                    "end_date": str(seg["timestamp"].iloc[-1].date()),
                    "min_stage_ft": round(float(seg["stage_ft"].min()), 2),
                    "days_below_12": duration,
                    "days_below_7": int((seg["stage_ft"] < 7.0).sum()),
                })
    if in_event:
        seg = river.iloc[start_idx:]
        duration = len(seg)
        if duration >= 7:
            events.append({
                "start_date": str(seg["timestamp"].iloc[0].date()),
                "end_date": str(seg["timestamp"].iloc[-1].date()),
                "min_stage_ft": round(float(seg["stage_ft"].min()), 2),
                "days_below_12": duration,
                "days_below_7": int((seg["stage_ft"] < 7.0).sum()),
            })
    ev_df = pd.DataFrame(events)
    ev_df.insert(0, "event_id", [f"LW-SYN-{i+1:03d}" for i in range(len(ev_df))])
    ev_df["event_year"] = pd.to_datetime(ev_df["start_date"]).dt.year
    ev_df["event_class"] = ev_df["days_below_7"].apply(
        lambda d: "Extreme" if d >= 30 else ("Significant" if d >= 10 else "Moderate")
    )
    return ev_df


events_df = _make_events(river_df)
events_df.to_csv(DEMO_DIR / "demo_events.csv", index=False)
print(f"  demo_events.csv: {len(events_df)} synthetic events")

print()
print("Demo data generation complete.")
print(f"Output directory: {DEMO_DIR}")
print()
print("IMPORTANT: These are synthetic files for portfolio/public demo use only.")
print("They are NOT copies of the real confidential monitoring data.")
print("Do not use for engineering decisions.")
