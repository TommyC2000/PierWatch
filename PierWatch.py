import streamlit as st

st.set_page_config(page_title="PierWatch", layout="wide")
st.title("PierWatch")
st.subheader("Engineering-Informed SHM Early Warning for Low-Water-Induced Bridge Pier Movement")

st.markdown("""
PierWatch is a monitoring-data-driven and engineering-informed decision-support prototype. It is **not** a full finite-element digital twin.

Core mechanism:

`Low river stage → E-1 / E-2 pier movement → E-3 joint opening and PP-15 joint closing → reduced remaining clearance → span jacking risk`

Use the left sidebar pages to inspect data, detect low-water events, track pier movement, and run PP-15 joint clearance risk scenarios.
""")

st.info("Start with Data Overview and Low-Water Event Detector. Run `python scripts/preprocess_data.py` first if processed files are missing.")
