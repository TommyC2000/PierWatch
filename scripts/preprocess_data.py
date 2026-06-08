from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.config import EXCEL_PATH, DATA_PROCESSED
from src.data_loader import load_river_stage, load_gps_data, load_pp15_filter
from src.event_detection import detect_low_water_events
from src.river_stage import compute_low_water_severity
from src.gps_processing import compute_event_movement
from src.sensor_quality import compute_sensor_quality


def main():
    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    river = load_river_stage(str(EXCEL_PATH))
    river.to_csv(DATA_PROCESSED / "river_stage_clean.csv", index=False)
    events = compute_low_water_severity(detect_low_water_events(river))
    events.to_csv(DATA_PROCESSED / "low_water_events.csv", index=False)

    gps = load_gps_data(str(EXCEL_PATH))
    gps.to_csv(DATA_PROCESSED / "gps_clean.csv", index=False)
    movement = compute_event_movement(gps, events) if not gps.empty else None
    if movement is not None:
        movement.to_csv(DATA_PROCESSED / "event_movement_summary.csv", index=False)
        q = compute_sensor_quality(gps, "pier_id", "timestamp", "longitudinal_in")
        q.to_csv(DATA_PROCESSED / "sensor_quality_summary.csv", index=False)

    pp15 = load_pp15_filter(str(EXCEL_PATH))
    pp15.to_csv(DATA_PROCESSED / "pp15_filter_clean.csv", index=False)
    print("Preprocessing complete. Processed files written to data/processed/.")


if __name__ == "__main__":
    main()
