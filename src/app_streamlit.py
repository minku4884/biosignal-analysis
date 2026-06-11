
from __future__ import annotations

from pathlib import Path
import json
from typing import Any

import pandas as pd
import streamlit as st


# =========================================================
# Path setting
# =========================================================
ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "processed"
FIG = ROOT / "figures"

SUMMARY_PATH = DATA / "analysis_summary.json"
DEVICE_SUMMARY_PATH = DATA / "device_summary.csv"
RISK_RESULT_PATH = DATA / "unified_biosignal_risk_results.csv"


# =========================================================
# Page config
# =========================================================
st.set_page_config(
    page_title="Radar Biosignal Dashboard",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded",
)


# =========================================================
# Custom CSS
# =========================================================
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;600;700;800&display=swap');

    html, body, [class*="css"] {
        font-family: 'Noto Sans KR', sans-serif;
    }

    .stApp {
        background:
            radial-gradient(circle at top left, rgba(43, 125, 255, 0.18), transparent 32%),
            radial-gradient(circle at top right, rgba(16, 185, 129, 0.12), transparent 30%),
            linear-gradient(180deg, #f7f9fc 0%, #eef3f8 100%);
    }

    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0f172a 0%, #111827 100%);
    }

    section[data-testid="stSidebar"] * {
        color: #f8fafc !important;
    }

    section[data-testid="stSidebar"] .stSelectbox label,
    section[data-testid="stSidebar"] .stMultiSelect label,
    section[data-testid="stSidebar"] .stSlider label,
    section[data-testid="stSidebar"] .stCheckbox label {
        font-weight: 700;
    }

    .block-container {
        padding-top: 2rem;
        padding-bottom: 3rem;
        max-width: 1500px;
    }

    .hero-card {
        padding: 2.1rem 2.3rem;
        border-radius: 28px;
        background:
            linear-gradient(135deg, rgba(15, 23, 42, 0.98), rgba(30, 64, 175, 0.90)),
            radial-gradient(circle at top right, rgba(56, 189, 248, 0.35), transparent 35%);
        color: white;
        box-shadow: 0 24px 70px rgba(15, 23, 42, 0.28);
        margin-bottom: 1.4rem;
        border: 1px solid rgba(255, 255, 255, 0.12);
    }

    .hero-title {
        font-size: 2.35rem;
        font-weight: 850;
        line-height: 1.25;
        margin-bottom: 0.6rem;
        letter-spacing: -0.04em;
    }

    .hero-subtitle {
        color: #dbeafe;
        font-size: 1.02rem;
        line-height: 1.75;
        max-width: 980px;
    }

    .hero-badge {
        display: inline-block;
        padding: 0.42rem 0.82rem;
        border-radius: 999px;
        background: rgba(255, 255, 255, 0.13);
        border: 1px solid rgba(255, 255, 255, 0.20);
        color: #e0f2fe;
        font-size: 0.82rem;
        font-weight: 700;
        margin-bottom: 0.8rem;
    }

    .section-card {
        padding: 1.2rem 1.35rem;
        border-radius: 22px;
        background: rgba(255, 255, 255, 0.88);
        border: 1px solid rgba(148, 163, 184, 0.22);
        box-shadow: 0 14px 38px rgba(15, 23, 42, 0.08);
        margin-bottom: 1rem;
    }

    .metric-card {
        padding: 1.15rem 1.2rem;
        border-radius: 22px;
        background: rgba(255, 255, 255, 0.92);
        border: 1px solid rgba(148, 163, 184, 0.22);
        box-shadow: 0 12px 34px rgba(15, 23, 42, 0.08);
        min-height: 132px;
    }

    .metric-label {
        color: #64748b;
        font-size: 0.85rem;
        font-weight: 800;
        text-transform: uppercase;
        letter-spacing: 0.02em;
        margin-bottom: 0.4rem;
    }

    .metric-value {
        color: #0f172a;
        font-size: 1.85rem;
        font-weight: 850;
        line-height: 1.1;
        letter-spacing: -0.03em;
    }

    .metric-help {
        color: #64748b;
        font-size: 0.82rem;
        margin-top: 0.55rem;
        line-height: 1.45;
    }

    .mini-title {
        color: #0f172a;
        font-size: 1.22rem;
        font-weight: 850;
        margin-bottom: 0.2rem;
        letter-spacing: -0.03em;
    }

    .mini-desc {
        color: #64748b;
        font-size: 0.92rem;
        line-height: 1.55;
        margin-bottom: 1rem;
    }

    .pill {
        display: inline-block;
        padding: 0.32rem 0.7rem;
        border-radius: 999px;
        background: #eff6ff;
        color: #1d4ed8;
        font-size: 0.78rem;
        font-weight: 800;
        border: 1px solid #bfdbfe;
        margin-right: 0.35rem;
        margin-bottom: 0.35rem;
    }

    .danger-pill {
        background: #fff1f2;
        color: #be123c;
        border: 1px solid #fecdd3;
    }

    .success-pill {
        background: #ecfdf5;
        color: #047857;
        border: 1px solid #a7f3d0;
    }

    .warning-pill {
        background: #fffbeb;
        color: #b45309;
        border: 1px solid #fde68a;
    }

    div[data-testid="stMetric"] {
        background: rgba(255,255,255,0.88);
        padding: 1rem;
        border-radius: 18px;
        border: 1px solid rgba(148, 163, 184, 0.18);
        box-shadow: 0 8px 22px rgba(15, 23, 42, 0.06);
    }

    div[data-testid="stDataFrame"] {
        border-radius: 18px;
        overflow: hidden;
        border: 1px solid rgba(148, 163, 184, 0.25);
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 0.5rem;
        background: rgba(255, 255, 255, 0.55);
        padding: 0.45rem;
        border-radius: 18px;
        border: 1px solid rgba(148, 163, 184, 0.18);
    }

    .stTabs [data-baseweb="tab"] {
        height: 48px;
        border-radius: 14px;
        padding: 0 1.15rem;
        font-weight: 800;
        color: #475569;
    }

    .stTabs [aria-selected="true"] {
        background: #0f172a !important;
        color: white !important;
    }

    .figure-card {
        padding: 1rem;
        border-radius: 22px;
        background: rgba(255, 255, 255, 0.9);
        border: 1px solid rgba(148, 163, 184, 0.22);
        box-shadow: 0 14px 34px rgba(15, 23, 42, 0.07);
        margin-bottom: 1rem;
    }

    .footer {
        margin-top: 2rem;
        padding: 1rem 1.2rem;
        border-radius: 18px;
        color: #64748b;
        background: rgba(255, 255, 255, 0.72);
        border: 1px solid rgba(148, 163, 184, 0.18);
        font-size: 0.88rem;
    }

    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# Helpers
# =========================================================
@st.cache_data(show_spinner=False)
def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


@st.cache_data(show_spinner=False)
def load_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path)


def fmt_int(value: Any) -> str:
    try:
        return f"{int(float(value)):,}"
    except Exception:
        return "-"


def fmt_pct(value: Any, digits: int = 1) -> str:
    try:
        return f"{float(value) * 100:.{digits}f}%"
    except Exception:
        return "-"


def fmt_float(value: Any, digits: int = 3) -> str:
    try:
        return f"{float(value):.{digits}f}"
    except Exception:
        return "-"


def find_col(df: pd.DataFrame, candidates: list[str]) -> str | None:
    lower_map = {c.lower(): c for c in df.columns}
    for cand in candidates:
        if cand.lower() in lower_map:
            return lower_map[cand.lower()]
    return None


def filter_by_device(df: pd.DataFrame, selected_devices: list[str]) -> pd.DataFrame:
    device_col = find_col(df, ["device_id", "device", "Device"])
    if device_col is None or not selected_devices:
        return df
    return df[df[device_col].astype(str).isin(selected_devices)]


def make_metric_card(label: str, value: str, help_text: str = "") -> None:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
            <div class="metric-help">{help_text}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def section_header(title: str, desc: str = "") -> None:
    st.markdown(
        f"""
        <div class="mini-title">{title}</div>
        <div class="mini-desc">{desc}</div>
        """,
        unsafe_allow_html=True,
    )


def styled_dataframe(df: pd.DataFrame, height: int = 420) -> None:
    st.dataframe(
        df,
        width="stretch",
        height=height,
        hide_index=True,
    )


def show_image(path: Path, caption: str) -> None:
    if path.exists():
        st.markdown('<div class="figure-card">', unsafe_allow_html=True)
        st.image(str(path), caption=caption, width="stretch")
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.warning(f"이미지를 찾을 수 없습니다: {path.name}")


def safe_sort(df: pd.DataFrame, col: str | None, ascending: bool = False) -> pd.DataFrame:
    if col and col in df.columns:
        return df.sort_values(col, ascending=ascending)
    return df


def add_ratio_columns(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()

    for col in ["fixed_risk_rate", "personalized_risk_rate", "heart_breath_corr"]:
        if col in result.columns:
            result[col] = pd.to_numeric(result[col], errors="coerce")

    return result


# =========================================================
# File validation
# =========================================================
if not SUMMARY_PATH.exists():
    st.error("분석 결과가 없습니다. 먼저 `python src/run_pipeline.py`를 실행하세요.")
    st.stop()

if not DEVICE_SUMMARY_PATH.exists():
    st.error("device_summary.csv 파일이 없습니다. 먼저 `python src/run_pipeline.py`를 실행하세요.")
    st.stop()

if not RISK_RESULT_PATH.exists():
    st.error("unified_biosignal_risk_results.csv 파일이 없습니다. 먼저 `python src/run_pipeline.py`를 실행하세요.")
    st.stop()


# =========================================================
# Load data
# =========================================================
summary = load_json(SUMMARY_PATH)
device_summary = add_ratio_columns(load_csv(DEVICE_SUMMARY_PATH))
risk = load_csv(RISK_RESULT_PATH)

device_col_summary = find_col(device_summary, ["device_id", "device", "Device"])
device_col_risk = find_col(risk, ["device_id", "device", "Device"])

available_devices: list[str] = []
if device_col_summary:
    available_devices = sorted(device_summary[device_col_summary].dropna().astype(str).unique().tolist())


# =========================================================
# Sidebar
# =========================================================
with st.sidebar:
    st.markdown("## 📡 Radar Dashboard")
    st.markdown("Multi-device biosignal risk detection")

    st.divider()

    selected_devices = st.multiselect(
        "Device 선택",
        options=available_devices,
        default=available_devices,
    )

    max_rows = st.slider(
        "Risk table 표시 row 수",
        min_value=50,
        max_value=1000,
        value=200,
        step=50,
    )

    show_only_risk = st.checkbox("위험 row만 보기", value=False)

    risk_filter_options = []
    for col in ["fixed_risk", "personalized_risk", "if_anomaly", "ocsvm_anomaly", "Drop"]:
        if col in risk.columns:
            risk_filter_options.append(col)

    selected_risk_flags = st.multiselect(
        "위험 플래그 필터",
        options=risk_filter_options,
        default=[],
        help="선택하지 않으면 전체 데이터를 표시합니다.",
    )

    st.divider()

    st.markdown("### 분석 파일")
    st.caption(f"DATA: `{DATA}`")
    st.caption(f"FIG: `{FIG}`")

    if st.button("데이터 새로고침"):
        st.cache_data.clear()
        st.rerun()


# =========================================================
# Apply filters
# =========================================================
filtered_device_summary = filter_by_device(device_summary, selected_devices)
filtered_risk = filter_by_device(risk, selected_devices)

if selected_risk_flags:
    mask = pd.Series(False, index=filtered_risk.index)
    for flag in selected_risk_flags:
        if flag in filtered_risk.columns:
            mask = mask | (pd.to_numeric(filtered_risk[flag], errors="coerce").fillna(0) > 0)
    filtered_risk = filtered_risk[mask]

if show_only_risk:
    risk_cols = [
        col for col in ["fixed_risk", "personalized_risk", "if_anomaly", "ocsvm_anomaly", "Drop"]
        if col in filtered_risk.columns
    ]
    if risk_cols:
        mask = pd.Series(False, index=filtered_risk.index)
        for col in risk_cols:
            mask = mask | (pd.to_numeric(filtered_risk[col], errors="coerce").fillna(0) > 0)
        filtered_risk = filtered_risk[mask]


# =========================================================
# Hero
# =========================================================
st.markdown(
    """
    <div class="hero-card">
        <div class="hero-badge">Final Project · Multi-device Radar Biosignal Analysis</div>
        <div class="hero-title">Radar Biosignal Multi-device Risk Detection Dashboard</div>
        <div class="hero-subtitle">
            6개 레이더 장치의 Heart, Breath, Drop 데이터를 통합하여
            고정 임계값, 개인화 baseline, 비지도 이상탐지 모델 결과를 한 화면에서 비교합니다.
            중간발표의 전처리·피벗 구조를 확장하여 장치별 위험률, 상관관계, Drop 전후 패턴까지 확인할 수 있습니다.
        </div>
        <div style="margin-top: 1rem;">
            <span class="pill success-pill">Unified Wide Data</span>
            <span class="pill">Fixed Rule</span>
            <span class="pill">Personalized Baseline</span>
            <span class="pill warning-pill">Isolation Forest</span>
            <span class="pill danger-pill">Drop Event Window</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# KPI cards
# =========================================================
k1, k2, k3, k4, k5 = st.columns(5)

with k1:
    make_metric_card(
        "Devices",
        fmt_int(summary.get("device_count")),
        "분석에 포함된 레이더 장치 수",
    )

with k2:
    make_metric_card(
        "Analysis Rows",
        fmt_int(summary.get("valid_analysis_rows")),
        "재실/유효 vital 기준 분석 row",
    )

with k3:
    make_metric_card(
        "Heart-Breath r",
        fmt_float(summary.get("heart_breath_corr_overall"), 3),
        "전체 Heart-Breath 상관계수",
    )

with k4:
    make_metric_card(
        "Fixed Risk",
        fmt_pct(summary.get("fixed_risk_rate"), 1),
        "고정 threshold 기준 위험률",
    )

with k5:
    make_metric_card(
        "Personalized Risk",
        fmt_pct(summary.get("personalized_risk_rate"), 1),
        "환자 baseline 기준 위험률",
    )


# =========================================================
# Quick interpretation
# =========================================================
st.markdown('<div class="section-card">', unsafe_allow_html=True)
section_header(
    "핵심 해석",
    "기말 분석에서는 단순 전처리 결과보다, multi-device 환경에서 위험 탐지를 어떻게 안정화할 수 있는지를 확인합니다.",
)

c1, c2, c3 = st.columns(3)

with c1:
    st.markdown(
        """
        <span class="pill">Result 1</span><br>
        <b>고정 기준은 넓게 탐지</b><br>
        Fixed risk는 민감하게 위험을 잡지만, 알람 수가 많아질 수 있습니다.
        """,
        unsafe_allow_html=True,
    )

with c2:
    st.markdown(
        """
        <span class="pill success-pill">Result 2</span><br>
        <b>개인화 기준은 과탐 감소</b><br>
        환자별 baseline을 반영하면 불필요한 위험 row를 줄일 수 있습니다.
        """,
        unsafe_allow_html=True,
    )

with c3:
    st.markdown(
        """
        <span class="pill warning-pill">Result 3</span><br>
        <b>IF 모델은 운영 후보</b><br>
        Isolation Forest는 개인화 rule과 비교했을 때 더 안정적인 anomaly 후보를 제공합니다.
        """,
        unsafe_allow_html=True,
    )

st.markdown("</div>", unsafe_allow_html=True)


# =========================================================
# Tabs
# =========================================================
tab_overview, tab_device, tab_figures, tab_risk, tab_about = st.tabs(
    [
        "📊 Overview",
        "🛏️ Device 분석",
        "🖼️ Figures",
        "🚨 Risk Results",
        "🧠 해석 가이드",
    ]
)


# =========================================================
# Tab 1: Overview
# =========================================================
with tab_overview:
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    section_header(
        "분석 Pipeline Summary",
        "raw device export → schema mapping → unified wide → feature engineering → rule/model detection → report/dashboard",
    )

    p1, p2, p3, p4 = st.columns(4)

    raw_pivot = summary.get("raw_pivot_rows", summary.get("raw_rows", 0))
    valid_rows = summary.get("valid_analysis_rows", 0)
    fixed_rows = summary.get("fixed_risk_rows", 0)
    personalized_rows = summary.get("personalized_risk_rows", 0)

    with p1:
        st.metric("Raw Pivot", fmt_int(raw_pivot))
    with p2:
        st.metric("Valid Analysis", fmt_int(valid_rows))
    with p3:
        st.metric("Fixed Risk Rows", fmt_int(fixed_rows))
    with p4:
        st.metric("Personalized Risk Rows", fmt_int(personalized_rows))

    funnel_data = pd.DataFrame(
        {
            "Stage": ["Raw Pivot", "Valid Analysis", "Fixed Risk", "Personalized Risk"],
            "Rows": [
                int(float(raw_pivot or 0)),
                int(float(valid_rows or 0)),
                int(float(fixed_rows or 0)),
                int(float(personalized_rows or 0)),
            ],
        }
    )

    st.bar_chart(
        funnel_data.set_index("Stage"),
        width="stretch",
        height=360,
    )

    st.markdown("</div>", unsafe_allow_html=True)

    col_a, col_b = st.columns([1.2, 1])

    with col_a:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        section_header(
            "Device별 Risk Rate 미리보기",
            "Fixed risk와 Personalized risk를 비교해서 알람 과탐 가능성을 확인합니다.",
        )

        chart_cols = []
        if "fixed_risk_rate" in filtered_device_summary.columns:
            chart_cols.append("fixed_risk_rate")
        if "personalized_risk_rate" in filtered_device_summary.columns:
            chart_cols.append("personalized_risk_rate")

        if device_col_summary and chart_cols:
            chart_df = filtered_device_summary[[device_col_summary] + chart_cols].copy()
            chart_df[device_col_summary] = chart_df[device_col_summary].astype(str)
            chart_df = chart_df.set_index(device_col_summary)
            st.bar_chart(chart_df, width="stretch", height=330)
        else:
            st.info("device_summary.csv에 risk rate 컬럼이 없어 차트를 표시하지 못했습니다.")

        st.markdown("</div>", unsafe_allow_html=True)

    with col_b:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        section_header(
            "Drop / Model Summary",
            "낙상 이벤트와 비지도 이상탐지 결과를 함께 확인합니다.",
        )

        drop_events = summary.get("drop_events", summary.get("drop_event_count", 0))
        if_anomaly_rows = summary.get("if_anomaly_rows", summary.get("isolation_forest_anomaly_rows", 0))
        ocsvm_anomaly_rows = summary.get("ocsvm_anomaly_rows", summary.get("oneclass_svm_anomaly_rows", 0))

        st.metric("Drop Events", fmt_int(drop_events))
        st.metric("Isolation Forest Anomaly", fmt_int(if_anomaly_rows))
        st.metric("One-Class SVM Anomaly", fmt_int(ocsvm_anomaly_rows))

        st.caption(
            "IF/OCSVM은 실제 정답 label이 부족한 상황에서 정상 패턴에서 벗어난 row를 찾기 위한 비지도 이상탐지 모델입니다."
        )

        st.markdown("</div>", unsafe_allow_html=True)


# =========================================================
# Tab 2: Device analysis
# =========================================================
with tab_device:
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    section_header(
        "Device Summary Table",
        "장치별 row 수, 평균 Heart/Breath, Drop 이벤트, 위험률, Heart-Breath 상관계수를 확인합니다.",
    )

    sort_candidates = [
        "personalized_risk_rate",
        "fixed_risk_rate",
        "analysis_rows",
        "drop_events",
        "heart_breath_corr",
    ]
    sort_options = [c for c in sort_candidates if c in filtered_device_summary.columns]

    if sort_options:
        sort_col = st.selectbox("정렬 기준", sort_options, index=0)
        filtered_device_summary_view = safe_sort(filtered_device_summary, sort_col, ascending=False)
    else:
        filtered_device_summary_view = filtered_device_summary

    styled_dataframe(filtered_device_summary_view, height=430)
    st.markdown("</div>", unsafe_allow_html=True)

    c1, c2 = st.columns(2)

    with c1:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        section_header(
            "Device별 Heart-Breath 상관계수",
            "각 device 내부에서 Heart와 Breath가 함께 움직이는 정도를 확인합니다.",
        )

        corr_col = find_col(filtered_device_summary, ["heart_breath_corr", "corr", "correlation"])
        if device_col_summary and corr_col:
            corr_df = filtered_device_summary[[device_col_summary, corr_col]].copy()
            corr_df[device_col_summary] = corr_df[device_col_summary].astype(str)
            corr_df[corr_col] = pd.to_numeric(corr_df[corr_col], errors="coerce")
            corr_df = corr_df.set_index(device_col_summary)
            st.bar_chart(corr_df, width="stretch", height=340)
        else:
            st.info("상관계수 컬럼을 찾지 못했습니다.")

        st.markdown("</div>", unsafe_allow_html=True)

    with c2:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        section_header(
            "Device별 분석 row 수",
            "장치별 데이터량 차이를 확인합니다. 위험률 비교 시 표본 수 차이도 함께 고려해야 합니다.",
        )

        rows_col = find_col(filtered_device_summary, ["analysis_rows", "valid_analysis_rows", "rows"])
        if device_col_summary and rows_col:
            rows_df = filtered_device_summary[[device_col_summary, rows_col]].copy()
            rows_df[device_col_summary] = rows_df[device_col_summary].astype(str)
            rows_df[rows_col] = pd.to_numeric(rows_df[rows_col], errors="coerce")
            rows_df = rows_df.set_index(device_col_summary)
            st.bar_chart(rows_df, width="stretch", height=340)
        else:
            st.info("row 수 컬럼을 찾지 못했습니다.")

        st.markdown("</div>", unsafe_allow_html=True)


# =========================================================
# Tab 3: Figures
# =========================================================
with tab_figures:
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    section_header(
        "분석 Figure Gallery",
        "보고서와 발표자료에 사용한 주요 그림을 대시보드에서 확인합니다.",
    )

    figure_catalog = [
        ("fig_00_architecture.png", "분석 구조 Architecture"),
        ("fig_01_device_coverage.png", "Device별 유효 분석 row 수"),
        ("fig_02_pipeline_funnel.png", "분석 파이프라인 Funnel"),
        ("fig_03_heart_distribution.png", "Heart 분포"),
        ("fig_04_breath_distribution.png", "Breath 분포"),
        ("fig_05_correlation_by_device.png", "Device별 Heart-Breath 상관계수"),
        ("fig_06_risk_rate_by_device.png", "Device별 위험 탐지율 비교"),
        ("fig_07_timeline_example.png", "72시간 Timeline 예시"),
        ("fig_08_threshold_sensitivity.png", "Threshold sensitivity"),
        ("fig_09_model_comparison.png", "비지도 이상탐지 모델 비교"),
        ("fig_10_drop_event_window.png", "Drop 이벤트 전후 vital window"),
    ]

    existing_figures = [(file, title) for file, title in figure_catalog if (FIG / file).exists()]

    if not existing_figures:
        st.warning("표시할 figure 파일이 없습니다.")
    else:
        selected_fig_titles = st.multiselect(
            "표시할 Figure 선택",
            options=[title for _, title in existing_figures],
            default=[title for _, title in existing_figures[:6]],
        )

        selected_figs = [
            (file, title)
            for file, title in existing_figures
            if title in selected_fig_titles
        ]

        for i in range(0, len(selected_figs), 2):
            left, right = st.columns(2)

            with left:
                file, title = selected_figs[i]
                show_image(FIG / file, title)

            if i + 1 < len(selected_figs):
                with right:
                    file, title = selected_figs[i + 1]
                    show_image(FIG / file, title)

    st.markdown("</div>", unsafe_allow_html=True)


# =========================================================
# Tab 4: Risk results
# =========================================================
with tab_risk:
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    section_header(
        "Risk Results Sample",
        "필터 조건에 맞는 위험 탐지 결과를 확인합니다. 발표 시에는 최근 100~200개 row만 보여주는 것이 좋습니다.",
    )

    r1, r2, r3, r4 = st.columns(4)

    with r1:
        st.metric("Filtered Rows", fmt_int(len(filtered_risk)))

    with r2:
        if "fixed_risk" in filtered_risk.columns:
            fixed_count = int((pd.to_numeric(filtered_risk["fixed_risk"], errors="coerce").fillna(0) > 0).sum())
            st.metric("Fixed Risk Rows", fmt_int(fixed_count))
        else:
            st.metric("Fixed Risk Rows", "-")

    with r3:
        if "personalized_risk" in filtered_risk.columns:
            pers_count = int((pd.to_numeric(filtered_risk["personalized_risk"], errors="coerce").fillna(0) > 0).sum())
            st.metric("Personalized Risk Rows", fmt_int(pers_count))
        else:
            st.metric("Personalized Risk Rows", "-")

    with r4:
        if "Drop" in filtered_risk.columns:
            drop_count = int((pd.to_numeric(filtered_risk["Drop"], errors="coerce").fillna(0) > 0).sum())
            st.metric("Drop Rows", fmt_int(drop_count))
        else:
            st.metric("Drop Rows", "-")

    st.divider()

    view_df = filtered_risk.tail(max_rows).copy()

    preferred_cols = [
        "timestamp",
        "datetime",
        "device_id",
        "patient_id",
        "Heart",
        "Breath",
        "Drop",
        "fixed_risk",
        "personalized_risk",
        "if_anomaly",
        "ocsvm_anomaly",
        "heart_delta",
        "breath_delta",
        "heart_robust_z",
        "breath_robust_z",
    ]

    existing_preferred_cols = [c for c in preferred_cols if c in view_df.columns]
    other_cols = [c for c in view_df.columns if c not in existing_preferred_cols]
    view_df = view_df[existing_preferred_cols + other_cols]

    styled_dataframe(view_df, height=520)

    csv = view_df.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        label="현재 표시 결과 CSV 다운로드",
        data=csv,
        file_name="filtered_risk_results.csv",
        mime="text/csv",
    )

    st.markdown("</div>", unsafe_allow_html=True)


# =========================================================
# Tab 5: Guide
# =========================================================
with tab_about:
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    section_header(
        "발표용 해석 가이드",
        "대시보드 시연 중 같이 설명하면 좋은 핵심 문장입니다.",
    )

    st.markdown(
        """
        ### 1. 왜 device별로 봤는가?

        전체 데이터를 한 번에 섞어서 보면 환자별 baseline, 장치별 설치 환경, 데이터 수 차이가 묻힐 수 있습니다.  
        그래서 이번 기말 분석에서는 각 device 내부에서 Heart와 Breath의 관계, 위험률, Drop 이벤트를 따로 확인했습니다.

        ### 2. Fixed risk와 Personalized risk 차이

        Fixed risk는 모든 환자에게 같은 기준을 적용하기 때문에 민감하게 위험을 잡을 수 있습니다.  
        하지만 알람이 과도하게 많아질 수 있습니다.  
        Personalized risk는 환자별 median과 MAD 기반 baseline을 사용하기 때문에, 개인의 평소 상태에서 벗어난 변화만 더 선별적으로 잡을 수 있습니다.

        ### 3. IF와 OCSVM을 사용한 이유

        실제 임상 정답 label이 충분하지 않은 상황에서는 지도학습 분류 모델을 바로 쓰기 어렵습니다.  
        그래서 정상 패턴에서 벗어난 row를 찾기 위해 비지도 이상탐지 모델인 Isolation Forest와 One-Class SVM을 비교했습니다.

        ### 4. 최종 활용 가능성

        이 결과는 병동 모니터링 dashboard, 환자별 baseline 기반 알람, device별 우선 점검 대상 선정, Drop 이벤트 전후 패턴 분석, 알람 피로도 감소 전략에 활용할 수 있습니다.
        """
    )

    st.markdown("</div>", unsafe_allow_html=True)


# =========================================================
# Footer
# =========================================================
st.markdown(
    """
    <div class="footer">
        Radar Biosignal Multi-device Dashboard · Python / Streamlit ·
        Fixed Rule + Personalized Baseline + Unsupervised Anomaly Detection
    </div>
    """,
    unsafe_allow_html=True,
)