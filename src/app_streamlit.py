from __future__ import annotations

from pathlib import Path
import json

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
FIG = ROOT / "figures"

st.set_page_config(page_title="Radar Biosignal Multi-device Dashboard", layout="wide")
st.title("Radar Biosignal Multi-device Risk Detection")
st.caption("Realistic synthetic demo + future Excel device import pipeline")

summary_path = DATA / "analysis_summary.json"
if not summary_path.exists():
    st.error("분석 결과가 없습니다. 먼저 `python src/run_pipeline.py`를 실행하세요.")
    st.stop()

summary = json.loads(summary_path.read_text(encoding="utf-8"))
cols = st.columns(5)
cols[0].metric("Devices", summary.get("device_count"))
cols[1].metric("Analysis rows", f"{int(summary.get('valid_analysis_rows', 0)):,}")
cols[2].metric("Heart-Breath r", summary.get("heart_breath_corr_overall"))
cols[3].metric("Fixed risk", f"{float(summary.get('fixed_risk_rate', 0))*100:.1f}%")
cols[4].metric("Personalized risk", f"{float(summary.get('personalized_risk_rate', 0))*100:.1f}%")

st.subheader("Device summary")
device_summary = pd.read_csv(DATA / "device_summary.csv")
st.dataframe(device_summary, use_container_width=True)

st.subheader("Figures")
figs = [
    "fig_06_risk_rate_by_device.png",
    "fig_05_correlation_by_device.png",
    "fig_07_timeline_example.png",
    "fig_09_model_comparison.png",
]
for f in figs:
    p = FIG / f
    if p.exists():
        st.image(str(p), caption=f, use_container_width=True)

st.subheader("Risk results sample")
risk = pd.read_csv(DATA / "unified_biosignal_risk_results.csv")
st.dataframe(risk.tail(100), use_container_width=True)
