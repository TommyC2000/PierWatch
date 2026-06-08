import pandas as pd
from src.event_detection import detect_low_water_events

def test_event_detection_basic():
    df = pd.DataFrame({"timestamp": pd.date_range("2025-01-01", periods=10), "stage_ft": [20,11,10,6,6,8,13,20,11,10]})
    ev = detect_low_water_events(df, min_event_days=2, merge_gap_days=0)
    assert len(ev) >= 1
    assert ev.iloc[0]["days_below_7"] == 2
