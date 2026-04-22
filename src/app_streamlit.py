from pathlib import Path
import json

import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt

st.set_page_config(page_title="Biosignal Monitoring Dashboard", layout="wide")

PROJECT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_DIR / "data"
RAW_PATH = DATA_DIR / "biosignal_raw_long_simulated.csv"
PROCESSED_PATH = DATA_DIR / "biosignal_processed_wide.csv"
SUMMARY_PATH = DATA_DIR / "analysis_summary.json"

st.title("레이더 기반 환자 생체신호 분석 대시보드")
st.caption("device_id는 익명화하여 사용")

@st.cache_data
def load_data():
    raw_df = pd.read_csv(RAW_PATH)
    processed_df = pd.read_csv(PROCESSED_PATH)
    processed_df["datetime"] = pd.to_datetime(processed_df["datetime"])
    with open(SUMMARY_PATH, "r", encoding="utf-8") as f:
        summary = json.load(f)
    return raw_df, processed_df, summary

raw_df, df, summary = load_data()

st.subheader("1. 요약 지표")
c1, c2, c3, c4 = st.columns(4)
c1.metric("원본 row", f'{summary["raw_rows"]:,}')
c2.metric("최종 분석 row", f'{summary["analysis_rows_after_cleaning"]:,}')
c3.metric("낙상 이벤트", f'{summary["drop_events_after_cleaning"]:,}')
c4.metric("상관계수", f'{summary["heart_breath_correlation"]}')

c5, c6, c7, c8 = st.columns(4)
c5.metric("평균 Heart", f'{summary["heart_mean"]:.2f}')
c6.metric("평균 Breath", f'{summary["breath_mean"]:.2f}')
c7.metric("재실 분", f'{summary["present_minutes_before_cleaning"]:,}')
c8.metric("위험 row", f'{summary["risk_rows_after_cleaning"]:,}')

st.subheader("2. 위험 상태 정의")
st.markdown("""
- **Drop = 1** 이면 위험
- **Heart > 100 bpm** 이면 위험
- **Breath > 25 rpm** 이면 위험
- **Heart 변화량(|Δ|) >= 15** 이면 급변 위험
- **Breath 변화량(|Δ|) >= 5** 이면 급변 위험
""")

st.subheader("3. 데이터 미리보기")
tab1, tab2 = st.tabs(["원본 데이터", "전처리 데이터"])
with tab1:
    st.dataframe(raw_df.head(20), use_container_width=True)
with tab2:
    st.dataframe(df.head(20), use_container_width=True)

st.subheader("4. 필터")
min_dt = df["datetime"].min().to_pydatetime()
max_dt = df["datetime"].max().to_pydatetime()
date_range = st.slider(
    "시간 범위",
    min_value=min_dt,
    max_value=max_dt,
    value=(min_dt, max_dt)
)
risk_only = st.checkbox("위험 상태만 보기", value=False)

filtered = df[
    (df["datetime"] >= pd.Timestamp(date_range[0])) &
    (df["datetime"] <= pd.Timestamp(date_range[1]))
].copy()

if risk_only:
    filtered = filtered[filtered["risk_flag"] == 1]

st.write(f"필터 결과: {len(filtered):,} rows")

st.subheader("5. 심박 / 호흡 타임라인")
fig, ax1 = plt.subplots(figsize=(12, 4))
ax1.plot(filtered["datetime"], filtered["Heart"], label="Heart", linewidth=1.2)
ax1.plot(filtered["datetime"], filtered["heart_roll5"], label="Heart Roll5", linewidth=1.2)
ax1.set_ylabel("Heart")
ax1.legend(loc="upper left")

ax2 = ax1.twinx()
ax2.plot(filtered["datetime"], filtered["Breath"], label="Breath", alpha=0.5, linewidth=1.0)
ax2.plot(filtered["datetime"], filtered["breath_roll5"], label="Breath Roll5", alpha=0.8, linewidth=1.0)
ax2.set_ylabel("Breath")
st.pyplot(fig)

st.subheader("6. 상관관계")
fig2, ax = plt.subplots(figsize=(6, 4))
sample = filtered.sample(n=min(2000, len(filtered)), random_state=42) if len(filtered) > 0 else filtered
ax.scatter(sample["Heart"], sample["Breath"], s=10, alpha=0.3)
ax.set_xlabel("Heart")
ax.set_ylabel("Breath")
ax.set_title(f'Heart vs Breath (r={summary["heart_breath_correlation"]})')
st.pyplot(fig2)

st.subheader("7. 시간대별 평균 패턴")
hourly = filtered.groupby("hour")[["Heart", "Breath"]].mean().reset_index()
fig3, ax = plt.subplots(figsize=(10, 4))
ax.plot(hourly["hour"], hourly["Heart"], marker="o", label="Heart")
ax.plot(hourly["hour"], hourly["Breath"], marker="s", label="Breath")
ax.set_xlabel("Hour")
ax.set_ylabel("Average value")
ax.legend()
st.pyplot(fig3)

st.subheader("8. 위험 상태 샘플")
risk_cols = [
    "datetime", "device_id", "Heart", "Breath", "Drop",
    "heart_delta", "breath_delta", "risk_type"
]
st.dataframe(
    filtered[filtered["risk_flag"] == 1][risk_cols].head(50),
    use_container_width=True
)