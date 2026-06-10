from __future__ import annotations

import argparse
import json
import warnings
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import joblib
import numpy as np
import pandas as pd

from sklearn.ensemble import IsolationForest
from sklearn.metrics import precision_recall_fscore_support
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import OneClassSVM

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

from common import (
    episode_count,
    find_column,
    list_input_files,
    load_json,
    project_root,
    robust_mad,
    write_csv,
)

warnings.filterwarnings("ignore", category=UserWarning)


# ============================================================
# 0. Fixed default mapping for your actual CSV structure
# ============================================================

DEFAULT_CATEGORY_CODE_MAP = {
    "14223": "Heart",
    "14221": "Breath",
    "14215": "Drop",
    "14211": "Status",

    "63": "Heart",
    "64": "Breath",
    "65": "Drop",
    "66": "Status",

    "heart": "Heart",
    "Heart": "Heart",
    "HEART": "Heart",
    "bpm": "Heart",
    "BPM": "Heart",
    "심박": "Heart",
    "심박수": "Heart",

    "breath": "Breath",
    "Breath": "Breath",
    "BREATH": "Breath",
    "rpm": "Breath",
    "RPM": "Breath",
    "호흡": "Breath",
    "호흡수": "Breath",

    "drop": "Drop",
    "Drop": "Drop",
    "fall": "Drop",
    "Fall": "Drop",
    "FALL": "Drop",
    "낙상": "Drop",

    "status": "Status",
    "Status": "Status",
    "STATUS": "Status",
    "presence": "Status",
    "present": "Status",
    "재실": "Status",
    "상태": "Status",
}

DEFAULT_ALIASES = {
    "datetime": [
        "datetime",
        "date_time",
        "time",
        "created_at",
        "measured_at",
        "측정시간",
        "시간",
        "일시",
    ],
    "timestamp": [
        "timestamp",
        "time_stamp",
        "unix_time",
        "unix_timestamp",
        "ts",
    ],
    "device_id": [
        "device_id",
        "deviceId",
        "deviceID",
        "DeviceID",
        "DEVICE_ID",
        "uid",
        "UID",
        "기기ID",
        "기기아이디",
        "장치ID",
    ],
    "patient_id": [
        "patient_id",
        "patientId",
        "subject_id",
        "subjectId",
        "user_id",
        "userId",
        "환자ID",
        "대상자ID",
    ],
    "room_id": [
        "room_id",
        "roomId",
        "room",
        "room_no",
        "ward_room",
        "병실",
        "호실",
    ],
    "data_category": [
        "data_category",
        "category",
        "category_code",
        "dataCategory",
        "DataCategory",
        "type",
        "code",
    ],
    "value": [
        "avg_value",
        "average_value",
        "avg",
        "mean",
        "value",
        "data_value",
        "measured_value",
    ],
    "Heart": [
        "Heart",
        "heart",
        "heart_rate",
        "heartrate",
        "hr",
        "HR",
        "bpm",
        "BPM",
        "심박",
        "심박수",
    ],
    "Breath": [
        "Breath",
        "breath",
        "breath_rate",
        "breathrate",
        "respiration",
        "respiration_rate",
        "br",
        "BR",
        "rpm",
        "RPM",
        "호흡",
        "호흡수",
    ],
    "Drop": [
        "Drop",
        "drop",
        "fall",
        "Fall",
        "fall_detection",
        "fall_flag",
        "낙상",
    ],
    "Status": [
        "Status",
        "status",
        "presence",
        "present",
        "is_present",
        "occupancy",
        "재실",
        "상태",
    ],
}


# ============================================================
# 1. General utility
# ============================================================

def setup_plot_font() -> None:
    """
    Windows / macOS / Linux 환경별 한글 폰트 자동 선택.
    NanumGothic 없어서 뜨던 findfont 경고 방지용.
    """
    try:
        available_fonts = {f.name for f in font_manager.fontManager.ttflist}
    except Exception:
        available_fonts = set()

    preferred_fonts = [
        "Malgun Gothic",
        "AppleGothic",
        "NanumGothic",
        "Noto Sans CJK KR",
        "DejaVu Sans",
    ]

    selected = "DejaVu Sans"

    for font in preferred_fonts:
        if font in available_fonts:
            selected = font
            break

    plt.rcParams["font.family"] = selected
    plt.rcParams["axes.unicode_minus"] = False


def read_table_safe(path: Path) -> pd.DataFrame:
    """
    CSV/XLSX 읽기.
    566.csv처럼 특정 줄에 쉼표가 하나 더 있는 경우 ParserError가 나므로
    on_bad_lines='skip'으로 깨진 줄만 건너뛰게 처리.
    """
    suffix = path.suffix.lower()

    if suffix in [".xlsx", ".xls"]:
        return pd.read_excel(path)

    if suffix == ".csv":
        encodings = ["utf-8-sig", "utf-8", "cp949", "euc-kr"]

        last_error = None

        for enc in encodings:
            try:
                return pd.read_csv(path, encoding=enc)
            except pd.errors.ParserError:
                try:
                    return pd.read_csv(
                        path,
                        encoding=enc,
                        engine="python",
                        on_bad_lines="skip",
                    )
                except Exception as exc:
                    last_error = exc
            except UnicodeDecodeError as exc:
                last_error = exc
            except Exception as exc:
                last_error = exc

        if last_error:
            raise last_error

    raise ValueError(f"Unsupported file type: {path}")


def normalize_category_code(x) -> Optional[str]:
    """
    data_category가 14223, 14223.0, '14223 ' 등으로 들어와도
    모두 '14223'으로 맞춰주는 함수.
    """
    if pd.isna(x):
        return None

    text = str(x).strip()

    if text == "":
        return None

    try:
        return str(int(float(text)))
    except Exception:
        return text


def get_aliases(schema: Dict, key: str) -> List[str]:
    """
    schema_mapping.json에 alias가 부족해도 DEFAULT_ALIASES를 합쳐서 사용.
    """
    schema_aliases = []
    try:
        schema_aliases = schema.get("standard_columns", {}).get(key, [])
    except Exception:
        schema_aliases = []

    default_aliases = DEFAULT_ALIASES.get(key, [])

    merged = []
    for item in list(schema_aliases) + list(default_aliases):
        if item not in merged:
            merged.append(item)

    return merged


def build_category_map(schema: Dict) -> Dict[str, str]:
    """
    schema_mapping.json의 category_code_map과 내부 기본 매핑을 합친다.
    """
    merged = {}

    for k, v in DEFAULT_CATEGORY_CODE_MAP.items():
        merged[normalize_category_code(k)] = v

    try:
        for k, v in schema.get("category_code_map", {}).items():
            merged[normalize_category_code(k)] = v
    except Exception:
        pass

    return merged


def build_datetime(df: pd.DataFrame, col_datetime: Optional[str], col_timestamp: Optional[str]) -> pd.Series:
    """
    datetime 또는 timestamp를 이용해서 datetime Series를 생성한다.
    네 CSV는 timestamp가 Unix seconds 형태임.
    """
    dt = pd.Series(pd.NaT, index=df.index)

    if col_datetime and col_datetime in df.columns:
        dt_try = pd.to_datetime(df[col_datetime], errors="coerce")
        if dt_try.notna().sum() > 0:
            dt = dt_try

    if dt.isna().all() and col_timestamp and col_timestamp in df.columns:
        raw_ts = pd.to_numeric(df[col_timestamp], errors="coerce")

        candidates = []

        for unit in ["s", "ms", "us", "ns"]:
            try:
                cand = pd.to_datetime(raw_ts, unit=unit, errors="coerce")
                valid = cand.notna()

                if valid.any():
                    years = cand[valid].dt.year
                    plausible = ((years >= 2000) & (years <= 2100)).sum()
                    valid_count = valid.sum()
                    score = plausible * 10 + valid_count
                    candidates.append((score, cand))
            except Exception:
                pass

        if candidates:
            candidates.sort(key=lambda x: x[0], reverse=True)
            dt = candidates[0][1]

    if dt.isna().all():
        dt = pd.Series(
            pd.date_range(
                start="2026-01-01 00:00:00",
                periods=len(df),
                freq="5min",
            ),
            index=df.index,
        )

    return dt


def safe_corr(g: pd.DataFrame) -> Optional[float]:
    if len(g) <= 2:
        return None

    if "Heart" not in g.columns or "Breath" not in g.columns:
        return None

    if g["Heart"].nunique(dropna=True) <= 1:
        return None

    if g["Breath"].nunique(dropna=True) <= 1:
        return None

    corr = g[["Heart", "Breath"]].corr().iloc[0, 1]

    if pd.isna(corr):
        return None

    return round(float(corr), 3)


def save_empty_figure(path: Path, title: str, message: str) -> None:
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.set_title(title)
    ax.text(0.5, 0.5, message, ha="center", va="center", fontsize=12)
    ax.axis("off")
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


# ============================================================
# 2. File standardization
# ============================================================

def standardize_file(path: Path, schema: Dict) -> pd.DataFrame:
    """
    하나의 CSV/XLSX 파일을 공통 wide format으로 변환.

    네 실제 CSV 구조:
        timestamp,device_id,data_category,min_value,avg_value,max_value

    변환 결과:
        datetime, timestamp, device_id, patient_id, room_id,
        Heart, Breath, Drop, Status, source_file
    """
    df = read_table_safe(path)
    original_columns = list(df.columns)

    if df.empty:
        raise ValueError(f"{path.name}: file is empty")

    col_datetime = find_column(df, get_aliases(schema, "datetime"))
    col_timestamp = find_column(df, get_aliases(schema, "timestamp"))
    col_device = find_column(df, get_aliases(schema, "device_id"))
    col_patient = find_column(df, get_aliases(schema, "patient_id"))
    col_room = find_column(df, get_aliases(schema, "room_id"))
    col_category = find_column(df, get_aliases(schema, "data_category"))
    col_value = find_column(df, get_aliases(schema, "value"))

    dt = build_datetime(df, col_datetime, col_timestamp)

    if col_timestamp and col_timestamp in df.columns:
        timestamp = pd.to_numeric(df[col_timestamp], errors="coerce")
    else:
        timestamp = pd.Series(
            pd.to_datetime(dt).astype("int64") // 10**9,
            index=df.index,
        )

    if col_device:
        device = df[col_device].astype(str)
    else:
        device = pd.Series([path.stem] * len(df), index=df.index)

    if col_patient:
        patient = df[col_patient].astype(str)
    else:
        patient = pd.Series([None] * len(df), index=df.index)

    if col_room:
        room = df[col_room].astype(str)
    else:
        room = pd.Series([None] * len(df), index=df.index)

    # 중요:
    # pivot_table은 index 컬럼에 NaN이 있으면 row를 버릴 수 있음.
    # 실제 CSV에는 patient_id, room_id가 없으므로 여기서 반드시 채워야 함.
    device = pd.Series(device, index=df.index).replace(
        {None: np.nan, "None": np.nan, "nan": np.nan, "": np.nan}
    )
    device = device.fillna(path.stem).astype(str)

    patient = pd.Series(patient, index=df.index).replace(
        {None: np.nan, "None": np.nan, "nan": np.nan, "": np.nan}
    )
    patient = patient.fillna("patient_" + device.astype(str)).astype(str)

    room = pd.Series(room, index=df.index).replace(
        {None: np.nan, "None": np.nan, "nan": np.nan, "": np.nan}
    )
    room = room.fillna("unknown").astype(str)
    # ------------------------------------------------------------
    # A. Long format: data_category + avg_value
    # ------------------------------------------------------------
    if col_category and col_value:
        temp = pd.DataFrame({
            "datetime": dt,
            "timestamp": timestamp,
            "device_id": device,
            "patient_id": patient,
            "room_id": room,
            "data_category": df[col_category],
            "value": pd.to_numeric(df[col_value], errors="coerce"),
            "source_file": path.name,
        })

        for optional in ["synthetic_flag", "scenario_event"]:
            if optional in df.columns:
                temp[optional] = df[optional].values

        category_map = build_category_map(schema)

        temp["category_key"] = temp["data_category"].map(normalize_category_code)
        temp["metric"] = temp["category_key"].map(category_map)

        temp = temp[temp["metric"].notna()].copy()

        if temp.empty:
            unique_codes = (
                pd.Series(df[col_category].dropna().unique())
                .astype(str)
                .head(30)
                .tolist()
            )

            raise ValueError(
                f"{path.name}: data_category values did not match mapping. "
                f"Found codes={unique_codes}. "
                f"Expected examples: 14223 Heart, 14221 Breath, 14215 Drop, 14211 Status."
            )

        id_cols = [
            "datetime",
            "timestamp",
            "device_id",
            "patient_id",
            "room_id",
            "source_file",
        ]

        if "synthetic_flag" in temp.columns:
            id_cols.append("synthetic_flag")

        wide = (
    temp.pivot_table(
        index=id_cols,
        columns="metric",
        values="value",
        aggfunc="mean",
        dropna=False,
    )
    .reset_index()
)

        wide.columns.name = None

        if "scenario_event" in temp.columns:
            scenario = (
                temp.groupby(id_cols, dropna=False)["scenario_event"]
                .first()
                .reset_index()
            )
            wide = wide.merge(scenario, on=id_cols, how="left")

    # ------------------------------------------------------------
    # B. Wide format: Heart / Breath columns already exist
    # ------------------------------------------------------------
    else:
        metric_cols = {
            m: find_column(df, get_aliases(schema, m))
            for m in ["Heart", "Breath", "Drop", "Status"]
        }

        if not metric_cols["Heart"] or not metric_cols["Breath"]:
            raise ValueError(
                f"{path.name}: could not find long-format columns "
                f"(data_category + avg_value) or wide Heart/Breath columns. "
                f"Columns={original_columns}"
            )

        wide = pd.DataFrame({
            "datetime": dt,
            "timestamp": timestamp,
            "device_id": device,
            "patient_id": patient,
            "room_id": room,
            "source_file": path.name,
            "Heart": pd.to_numeric(df[metric_cols["Heart"]], errors="coerce"),
            "Breath": pd.to_numeric(df[metric_cols["Breath"]], errors="coerce"),
        })

        if metric_cols["Drop"]:
            wide["Drop"] = pd.to_numeric(df[metric_cols["Drop"]], errors="coerce")
        else:
            wide["Drop"] = 0

        if metric_cols["Status"]:
            wide["Status"] = pd.to_numeric(df[metric_cols["Status"]], errors="coerce")
        else:
            wide["Status"] = 1

        for optional in ["synthetic_flag", "scenario_event"]:
            if optional in df.columns:
                wide[optional] = df[optional].values

    # ------------------------------------------------------------
    # Required columns
    # ------------------------------------------------------------
    for col in ["Heart", "Breath", "Drop", "Status"]:
        if col not in wide.columns:
            if col == "Drop":
                wide[col] = 0
            elif col == "Status":
                wide[col] = 1
            else:
                wide[col] = np.nan

        wide[col] = pd.to_numeric(wide[col], errors="coerce")

    wide["device_id"] = wide["device_id"].replace(
        {None: np.nan, "None": np.nan, "nan": np.nan, "": np.nan}
    )
    wide["device_id"] = wide["device_id"].fillna(path.stem).astype(str)

    wide["patient_id"] = wide["patient_id"].replace(
        {None: np.nan, "None": np.nan, "nan": np.nan, "": np.nan}
    )
    wide["patient_id"] = wide["patient_id"].fillna(
        "patient_" + wide["device_id"].astype(str)
    )

    wide["room_id"] = wide["room_id"].replace(
        {None: np.nan, "None": np.nan, "nan": np.nan, "": np.nan}
    )
    wide["room_id"] = wide["room_id"].fillna("unknown")

    wide["source_file"] = path.name

    before_datetime_filter = len(wide)
    wide = wide[wide["datetime"].notna()].copy()

    if wide.empty:
        raise ValueError(
            f"{path.name}: all rows were removed because datetime could not be parsed. "
            f"Original rows={before_datetime_filter}, Columns={original_columns}"
        )

    wide = wide.sort_values(["device_id", "patient_id", "datetime"])

    return wide


def ingest_all(input_dir: Path, schema: Dict) -> Tuple[pd.DataFrame, pd.DataFrame]:
    files = list_input_files(input_dir)

    records = []
    frames = []

    for path in files:
        try:
            frame = standardize_file(path, schema)
            frames.append(frame)

            records.append({
                "source_file": path.name,
                "status": "loaded",
                "rows": int(len(frame)),
                "message": "",
            })

        except Exception as exc:
            records.append({
                "source_file": path.name,
                "status": "error",
                "rows": 0,
                "message": str(exc),
            })

    import_report = pd.DataFrame(records)

    if not frames:
        raise RuntimeError(
            f"No usable device data files found in {input_dir}.\n"
            f"Import report:\n{import_report.to_string(index=False)}"
        )

    wide = pd.concat(frames, ignore_index=True)

    group_cols = [
        "datetime",
        "timestamp",
        "device_id",
        "patient_id",
        "room_id",
    ]

    agg = {
        "Heart": "mean",
        "Breath": "mean",
        "Drop": "max",
        "Status": "max",
        "source_file": "first",
    }

    if "synthetic_flag" in wide.columns:
        agg["synthetic_flag"] = "max"

    if "scenario_event" in wide.columns:
        agg["scenario_event"] = "first"

    before = len(wide)

    wide = (
        wide.groupby(group_cols, dropna=False)
        .agg(agg)
        .reset_index()
    )

    wide["duplicate_rows_collapsed"] = before - len(wide)

    wide = wide.sort_values(["device_id", "patient_id", "datetime"])

    return wide, import_report


# ============================================================
# 3. Preprocessing
# ============================================================

def infer_presence_from_status(df: pd.DataFrame) -> Tuple[pd.Series, str]:
    """
    실제 Status 의미가 장비/서버마다 다를 수 있으므로 자동 판단.

    - Status 1 = 재실/유효일 수도 있음
    - Status 0 = 재실/유효일 수도 있음
    - 둘 다 애매하면 Heart/Breath가 있으면 유효로 판단
    """
    vitals_exist = df["Heart"].notna() & df["Breath"].notna()

    if "Status" not in df.columns:
        return vitals_exist, "missing_status_use_vitals_only"

    status = pd.to_numeric(df["Status"], errors="coerce")

    if status.notna().sum() == 0:
        return vitals_exist, "empty_status_use_vitals_only"

    status = status.fillna(1).clip(0, 1)

    present_if_one = vitals_exist & (status >= 0.5)
    present_if_zero = vitals_exist & (status < 0.5)

    n_one = int(present_if_one.sum())
    n_zero = int(present_if_zero.sum())
    n_vitals = int(vitals_exist.sum())

    if n_vitals == 0:
        return pd.Series([False] * len(df), index=df.index), "no_vitals"

    if n_zero > n_one * 1.2:
        return present_if_zero, "status_0_is_present"

    if n_one > n_zero * 1.2:
        return present_if_one, "status_1_is_present"

    return vitals_exist, "ambiguous_status_use_vitals_only"


def preprocess_features(wide: pd.DataFrame, config: Dict) -> Tuple[pd.DataFrame, Dict]:
    df = wide.copy()

    raw_rows = len(df)

    valid_ranges = config.get(
        "valid_ranges",
        {
            "Heart": [25, 220],
            "Breath": [3, 60],
        },
    )

    metrics = {
        "raw_rows": int(raw_rows),
    }

    required_cols = [
        "device_id",
        "patient_id",
        "datetime",
        "Heart",
        "Breath",
        "Status",
        "Drop",
    ]

    for col in required_cols:
        if col not in df.columns:
            if col == "Status":
                df[col] = 1
            elif col == "Drop":
                df[col] = 0
            elif col in ["Heart", "Breath"]:
                df[col] = np.nan
            else:
                raise KeyError(f"Required column missing after ingestion: {col}")

    for col in ["Heart", "Breath", "Status", "Drop"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    metrics["missing_heart_rows"] = int(df["Heart"].isna().sum())
    metrics["missing_breath_rows"] = int(df["Breath"].isna().sum())

    # ------------------------------------------------------------
    # Outlier removal
    # ------------------------------------------------------------
    for col in ["Heart", "Breath"]:
        lo, hi = valid_ranges.get(col, [None, None])

        if lo is None or hi is None:
            metrics[f"{col.lower()}_outlier_rows"] = 0
            continue

        outlier_mask = df[col].notna() & ((df[col] < lo) | (df[col] > hi))

        metrics[f"{col.lower()}_outlier_rows"] = int(outlier_mask.sum())

        df.loc[outlier_mask, col] = np.nan

    df["Drop"] = df["Drop"].fillna(0).clip(0, 1)

    # ------------------------------------------------------------
    # Status handling
    # ------------------------------------------------------------
    is_present, status_mode = infer_presence_from_status(df)

    df["is_present"] = is_present.astype(bool)
    df["valid_vitals"] = df["Heart"].notna() & df["Breath"].notna() & df["is_present"]

    if int(df["valid_vitals"].sum()) == 0:
        vitals_only = df["Heart"].notna() & df["Breath"].notna()

        if int(vitals_only.sum()) > 0:
            df["is_present"] = vitals_only
            df["valid_vitals"] = vitals_only
            status_mode = f"{status_mode}_fallback_vitals_only"

    metrics["status_presence_mode"] = status_mode

    if int(df["valid_vitals"].sum()) == 0:
        sample_cols = [
            c
            for c in [
                "source_file",
                "device_id",
                "patient_id",
                "datetime",
                "Heart",
                "Breath",
                "Status",
                "Drop",
            ]
            if c in df.columns
        ]

        sample = df[sample_cols].head(20).to_string(index=False)

        raise RuntimeError(
            "No valid Heart/Breath rows after preprocessing.\n"
            "Heart/Breath may not have been parsed from data_category.\n"
            f"Status mode detected: {status_mode}\n"
            f"Rows after ingestion: {len(df)}\n"
            f"Sample rows:\n{sample}"
        )

    df = df.sort_values(["device_id", "patient_id", "datetime"])

    group_cols = ["device_id", "patient_id"]

    # ------------------------------------------------------------
    # Filling for feature calculation
    # ------------------------------------------------------------
    for col in ["Heart", "Breath"]:
        df[f"{col}_filled"] = (
            df.groupby(group_cols)[col]
            .transform(lambda s: s.ffill(limit=2).bfill(limit=1))
        )

    for col in ["Heart", "Breath"]:
        filled_col = f"{col}_filled"

        global_median = df.loc[df["valid_vitals"], col].median()

        if pd.isna(global_median):
            global_median = df[col].median()

        df[filled_col] = df[filled_col].fillna(global_median)

    rolling_points = config.get("feature_windows", {}).get(
        "rolling_points",
        [3, 6, 12],
    )

    for window in rolling_points:
        df[f"heart_roll{window}"] = (
            df.groupby(group_cols)["Heart_filled"]
            .transform(lambda s: s.rolling(window, min_periods=1).median())
        )

        df[f"breath_roll{window}"] = (
            df.groupby(group_cols)["Breath_filled"]
            .transform(lambda s: s.rolling(window, min_periods=1).median())
        )

    df["heart_delta"] = (
        df.groupby(group_cols)["Heart_filled"]
        .diff()
        .fillna(0)
    )

    df["breath_delta"] = (
        df.groupby(group_cols)["Breath_filled"]
        .diff()
        .fillna(0)
    )

    df["hour"] = df["datetime"].dt.hour
    df["date"] = df["datetime"].dt.date.astype(str)

    # ------------------------------------------------------------
    # Personalized baseline
    # ------------------------------------------------------------
    baseline_rows = []

    valid_base = df[df["valid_vitals"]].copy()

    for key, g in valid_base.groupby(group_cols):
        gh = g["Heart"]
        gb = g["Breath"]

        h_med = float(gh.median()) if gh.notna().any() else np.nan
        b_med = float(gb.median()) if gb.notna().any() else np.nan

        h_mad = robust_mad(gh, floor=3.0)
        b_mad = robust_mad(gb, floor=1.0)

        baseline_rows.append({
            "device_id": key[0],
            "patient_id": key[1],
            "heart_baseline": h_med,
            "breath_baseline": b_med,
            "heart_mad": h_mad,
            "breath_mad": b_mad,
        })

    baseline_cols = [
        "device_id",
        "patient_id",
        "heart_baseline",
        "breath_baseline",
        "heart_mad",
        "breath_mad",
    ]

    if baseline_rows:
        baseline = pd.DataFrame(baseline_rows)
    else:
        baseline = pd.DataFrame(columns=baseline_cols)

    df = df.merge(baseline, on=group_cols, how="left")

    global_heart_baseline = float(valid_base["Heart"].median())
    global_breath_baseline = float(valid_base["Breath"].median())

    global_heart_mad = robust_mad(valid_base["Heart"], floor=3.0)
    global_breath_mad = robust_mad(valid_base["Breath"], floor=1.0)

    df["heart_baseline"] = df["heart_baseline"].fillna(global_heart_baseline)
    df["breath_baseline"] = df["breath_baseline"].fillna(global_breath_baseline)

    df["heart_mad"] = df["heart_mad"].fillna(global_heart_mad).replace(0, 3.0)
    df["breath_mad"] = df["breath_mad"].fillna(global_breath_mad).replace(0, 1.0)

    df["heart_robust_z"] = (
        (df["Heart_filled"] - df["heart_baseline"]) /
        (1.4826 * df["heart_mad"].replace(0, np.nan))
    )

    df["breath_robust_z"] = (
        (df["Breath_filled"] - df["breath_baseline"]) /
        (1.4826 * df["breath_mad"].replace(0, np.nan))
    )

    df["heart_robust_z"] = (
        df["heart_robust_z"]
        .replace([np.inf, -np.inf], np.nan)
        .fillna(0)
    )

    df["breath_robust_z"] = (
        df["breath_robust_z"]
        .replace([np.inf, -np.inf], np.nan)
        .fillna(0)
    )

    metrics["valid_analysis_rows"] = int(df["valid_vitals"].sum())
    metrics["device_count"] = int(df.loc[df["valid_vitals"], "device_id"].nunique())
    metrics["patient_count"] = int(df.loc[df["valid_vitals"], "patient_id"].nunique())
    metrics["drop_events"] = int(((df["Drop"] >= 0.5) & df["valid_vitals"]).sum())

    return df, metrics


# ============================================================
# 4. Rule-based risk detection
# ============================================================

def assign_risk(df: pd.DataFrame, thresholds: Dict) -> pd.DataFrame:
    t = thresholds.get(
        "fixed_thresholds",
        {
            "heart_warning_high": 100,
            "heart_warning_low": 50,
            "heart_critical_high": 120,
            "heart_critical_low": 40,
            "breath_warning_high": 25,
            "breath_warning_low": 8,
            "breath_critical_high": 30,
            "breath_critical_low": 5,
            "heart_delta_sudden": 15,
            "breath_delta_sudden": 5,
        },
    )

    p = thresholds.get(
        "personalized_thresholds",
        {
            "warning_z": 2.5,
            "danger_z": 3.5,
            "heart_delta_sudden": 15,
            "breath_delta_sudden": 5,
        },
    )

    out = df.copy()

    fixed_danger = (
        (out["Drop"] >= 0.5) |
        (out["Heart_filled"] >= t["heart_critical_high"]) |
        (out["Heart_filled"] <= t["heart_critical_low"]) |
        (out["Breath_filled"] >= t["breath_critical_high"]) |
        (out["Breath_filled"] <= t["breath_critical_low"])
    ) & out["valid_vitals"]

    fixed_warning = (
        (out["Heart_filled"] >= t["heart_warning_high"]) |
        (out["Heart_filled"] <= t["heart_warning_low"]) |
        (out["Breath_filled"] >= t["breath_warning_high"]) |
        (out["Breath_filled"] <= t["breath_warning_low"]) |
        (out["heart_delta"].abs() >= t["heart_delta_sudden"]) |
        (out["breath_delta"].abs() >= t["breath_delta_sudden"])
    ) & out["valid_vitals"]

    pers_danger = (
        (out["Drop"] >= 0.5) |
        (out["heart_robust_z"].abs() >= p["danger_z"]) |
        (out["breath_robust_z"].abs() >= p["danger_z"])
    ) & out["valid_vitals"]

    pers_warning = (
        (out["heart_robust_z"].abs() >= p["warning_z"]) |
        (out["breath_robust_z"].abs() >= p["warning_z"]) |
        (out["heart_delta"].abs() >= p["heart_delta_sudden"]) |
        (out["breath_delta"].abs() >= p["breath_delta_sudden"])
    ) & out["valid_vitals"]

    out["fixed_risk_level"] = np.select(
        [fixed_danger, fixed_warning],
        ["Danger", "Warning"],
        default="Normal",
    )

    out["personalized_risk_level"] = np.select(
        [pers_danger, pers_warning],
        ["Danger", "Warning"],
        default="Normal",
    )

    out["fixed_risk_flag"] = (out["fixed_risk_level"] != "Normal").astype(int)
    out["personalized_risk_flag"] = (out["personalized_risk_level"] != "Normal").astype(int)

    reasons = []

    for _, r in out.iterrows():
        row_reasons = []

        if bool(r.get("valid_vitals", False)):
            if r.get("Drop", 0) >= 0.5:
                row_reasons.append("Drop")

            heart = r.get("Heart_filled", np.nan)
            breath = r.get("Breath_filled", np.nan)

            if pd.notna(heart) and (
                heart >= t["heart_critical_high"] or
                heart <= t["heart_critical_low"]
            ):
                row_reasons.append("HeartCritical")
            elif pd.notna(heart) and (
                heart >= t["heart_warning_high"] or
                heart <= t["heart_warning_low"]
            ):
                row_reasons.append("HeartWarning")

            if pd.notna(breath) and (
                breath >= t["breath_critical_high"] or
                breath <= t["breath_critical_low"]
            ):
                row_reasons.append("BreathCritical")
            elif pd.notna(breath) and (
                breath >= t["breath_warning_high"] or
                breath <= t["breath_warning_low"]
            ):
                row_reasons.append("BreathWarning")

            heart_delta = float(r.get("heart_delta", 0) or 0)
            breath_delta = float(r.get("breath_delta", 0) or 0)

            if (
                abs(heart_delta) >= t["heart_delta_sudden"] or
                abs(breath_delta) >= t["breath_delta_sudden"]
            ):
                row_reasons.append("SuddenChange")

            heart_z = float(r.get("heart_robust_z", 0) or 0)
            breath_z = float(r.get("breath_robust_z", 0) or 0)

            if (
                abs(heart_z) >= p["warning_z"] or
                abs(breath_z) >= p["warning_z"]
            ):
                row_reasons.append("PersonalizedZ")

        reasons.append(";".join(row_reasons) if row_reasons else "Normal")

    out["risk_reason"] = reasons

    return out


# ============================================================
# 5. Unsupervised anomaly detection
# ============================================================

def train_models(
    df: pd.DataFrame,
    config: Dict,
    model_dir: Path,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    model_dir.mkdir(parents=True, exist_ok=True)

    df_out = df.copy()

    df_out["iforest_anomaly"] = 0
    df_out["iforest_score"] = np.nan
    df_out["ocsvm_anomaly"] = 0
    df_out["ocsvm_score"] = np.nan

    features = [
        "Heart_filled",
        "Breath_filled",
        "heart_roll3",
        "breath_roll3",
        "heart_roll6",
        "breath_roll6",
        "heart_delta",
        "breath_delta",
        "heart_robust_z",
        "breath_robust_z",
        "hour",
    ]

    work = df[df["valid_vitals"]].copy()

    if len(work) < 20:
        model_summary = pd.DataFrame([
            {
                "model": "Isolation Forest",
                "anomaly_rows": 0,
                "anomaly_rate": 0.0,
                "rule_overlap_precision_proxy": 0.0,
                "rule_coverage_recall_proxy": 0.0,
                "proxy_f1": 0.0,
                "alert_episodes": 0,
                "score_column": "iforest_score",
                "note": "Not enough valid rows for model training.",
            },
            {
                "model": "One-Class SVM",
                "anomaly_rows": 0,
                "anomaly_rate": 0.0,
                "rule_overlap_precision_proxy": 0.0,
                "rule_coverage_recall_proxy": 0.0,
                "proxy_f1": 0.0,
                "alert_episodes": 0,
                "score_column": "ocsvm_score",
                "note": "Not enough valid rows for model training.",
            },
        ])

        return df_out, model_summary

    for feature in features:
        if feature not in work.columns:
            work[feature] = 0

    X = work[features].replace([np.inf, -np.inf], np.nan)
    X = X.fillna(X.median(numeric_only=True))
    X = X.fillna(0)

    modeling = config.get("modeling", {})

    contamination = modeling.get("isolation_forest_contamination", 0.045)
    nu = modeling.get("oneclass_svm_nu", 0.05)
    seed = modeling.get("random_seed", 42)

    if_model = IsolationForest(
        n_estimators=250,
        contamination=contamination,
        random_state=seed,
    )

    if_pred = if_model.fit_predict(X)
    if_score = -if_model.score_samples(X)

    joblib.dump(if_model, model_dir / "isolation_forest_model.joblib")

    oc_model = Pipeline([
        ("scaler", StandardScaler()),
        ("ocsvm", OneClassSVM(kernel="rbf", gamma="scale", nu=nu)),
    ])

    oc_pred = oc_model.fit_predict(X)
    oc_score = -oc_model.decision_function(X)

    joblib.dump(oc_model, model_dir / "oneclass_svm_model.joblib")

    work["iforest_anomaly"] = (if_pred == -1).astype(int)
    work["iforest_score"] = if_score
    work["ocsvm_anomaly"] = (oc_pred == -1).astype(int)
    work["ocsvm_score"] = oc_score

    df_out = df_out.merge(
        work[
            [
                "datetime",
                "device_id",
                "patient_id",
                "iforest_anomaly",
                "iforest_score",
                "ocsvm_anomaly",
                "ocsvm_score",
            ]
        ],
        on=["datetime", "device_id", "patient_id"],
        how="left",
        suffixes=("", "_model"),
    )

    for col in ["iforest_anomaly", "ocsvm_anomaly"]:
        model_col = f"{col}_model"

        if model_col in df_out.columns:
            df_out[col] = (
                df_out[model_col]
                .fillna(df_out[col])
                .fillna(0)
                .astype(int)
            )
            df_out = df_out.drop(columns=[model_col])
        else:
            df_out[col] = df_out[col].fillna(0).astype(int)

    for col in ["iforest_score", "ocsvm_score"]:
        model_col = f"{col}_model"

        if model_col in df_out.columns:
            df_out[col] = df_out[model_col].fillna(df_out[col])
            df_out = df_out.drop(columns=[model_col])

    proxy = work["personalized_risk_flag"].astype(int)

    summaries = []

    for model_col, score_col, display in [
        ("iforest_anomaly", "iforest_score", "Isolation Forest"),
        ("ocsvm_anomaly", "ocsvm_score", "One-Class SVM"),
    ]:
        pred = work[model_col].astype(int)

        if proxy.nunique() > 1:
            precision, recall, f1, _ = precision_recall_fscore_support(
                proxy,
                pred,
                average="binary",
                zero_division=0,
            )
        else:
            precision = recall = f1 = 0.0

        anomaly_count = int(pred.sum())

        summaries.append({
            "model": display,
            "anomaly_rows": anomaly_count,
            "anomaly_rate": round(float(pred.mean()), 4),
            "rule_overlap_precision_proxy": round(float(precision), 4),
            "rule_coverage_recall_proxy": round(float(recall), 4),
            "proxy_f1": round(float(f1), 4),
            "alert_episodes": episode_count(
                work.assign(tmp=pred.values),
                "tmp",
                ["device_id", "patient_id"],
            ),
            "score_column": score_col,
            "note": "Proxy metrics use personalized threshold risk as a reference, not clinical ground truth.",
        })

    return df_out, pd.DataFrame(summaries)


# ============================================================
# 6. Summary
# ============================================================

def summarize_outputs(
    df: pd.DataFrame,
    import_report: pd.DataFrame,
    model_summary: pd.DataFrame,
    metrics: Dict,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, Dict]:

    valid = df[df["valid_vitals"]].copy()

    device_rows = []

    if not valid.empty:
        for device, g in valid.groupby("device_id"):
            corr = safe_corr(g)

            device_rows.append({
                "device_id": device,
                "patient_count": int(g["patient_id"].nunique()),
                "analysis_rows": int(len(g)),
                "start_datetime": str(g["datetime"].min()),
                "end_datetime": str(g["datetime"].max()),
                "heart_mean": round(float(g["Heart"].mean()), 2),
                "breath_mean": round(float(g["Breath"].mean()), 2),
                "heart_breath_corr": corr,
                "drop_events": int((g["Drop"] >= 0.5).sum()),
                "fixed_risk_rows": int(g["fixed_risk_flag"].sum()),
                "fixed_risk_rate": round(float(g["fixed_risk_flag"].mean()), 4),
                "personalized_risk_rows": int(g["personalized_risk_flag"].sum()),
                "personalized_risk_rate": round(float(g["personalized_risk_flag"].mean()), 4),
                "iforest_rate": round(float(g["iforest_anomaly"].mean()), 4),
                "ocsvm_rate": round(float(g["ocsvm_anomaly"].mean()), 4),
            })

    device_summary = pd.DataFrame(device_rows)

    if not device_summary.empty:
        device_summary = device_summary.sort_values("device_id")

    if not valid.empty:
        reason_summary = (
            valid.assign(reason=valid["risk_reason"].str.split(";"))
            .explode("reason")
            .query("reason != 'Normal'")
            .groupby("reason")
            .size()
            .reset_index(name="rows")
            .sort_values("rows", ascending=False)
        )
    else:
        reason_summary = pd.DataFrame(columns=["reason", "rows"])

    if not valid.empty:
        overall_corr = safe_corr(valid)

        if overall_corr is None:
            overall_corr = np.nan

        risk_summary = pd.DataFrame({
            "metric": [
                "input_files",
                "raw_rows_after_pivot",
                "valid_analysis_rows",
                "device_count",
                "patient_count",
                "heart_breath_corr_overall",
                "drop_events",
                "fixed_risk_rows",
                "fixed_risk_rate",
                "personalized_risk_rows",
                "personalized_risk_rate",
                "iforest_anomaly_rate",
                "ocsvm_anomaly_rate",
            ],
            "value": [
                int((import_report["status"] == "loaded").sum()),
                int(len(df)),
                int(len(valid)),
                int(valid["device_id"].nunique()),
                int(valid["patient_id"].nunique()),
                overall_corr,
                int((valid["Drop"] >= 0.5).sum()),
                int(valid["fixed_risk_flag"].sum()),
                round(float(valid["fixed_risk_flag"].mean()), 4),
                int(valid["personalized_risk_flag"].sum()),
                round(float(valid["personalized_risk_flag"].mean()), 4),
                round(float(valid["iforest_anomaly"].mean()), 4),
                round(float(valid["ocsvm_anomaly"].mean()), 4),
            ],
        })
    else:
        risk_summary = pd.DataFrame({
            "metric": [
                "input_files",
                "raw_rows_after_pivot",
                "valid_analysis_rows",
                "device_count",
                "patient_count",
                "heart_breath_corr_overall",
                "drop_events",
                "fixed_risk_rows",
                "fixed_risk_rate",
                "personalized_risk_rows",
                "personalized_risk_rate",
                "iforest_anomaly_rate",
                "ocsvm_anomaly_rate",
            ],
            "value": [
                int((import_report["status"] == "loaded").sum()),
                int(len(df)),
                0,
                0,
                0,
                np.nan,
                0,
                0,
                0.0,
                0,
                0.0,
                0.0,
                0.0,
            ],
        })

    analysis_summary = {}

    for k, v in metrics.items():
        if isinstance(v, np.integer):
            analysis_summary[k] = int(v)
        elif isinstance(v, np.floating):
            analysis_summary[k] = float(v)
        else:
            analysis_summary[k] = v

    for _, row in risk_summary.iterrows():
        value = row["value"]

        if isinstance(value, np.integer):
            value = int(value)
        elif isinstance(value, np.floating):
            value = float(value)

        analysis_summary[row["metric"]] = value

    analysis_summary["model_summary"] = model_summary.to_dict(orient="records")

    return device_summary, reason_summary, risk_summary, analysis_summary


# ============================================================
# 7. Figures
# ============================================================

def make_figures(
    df: pd.DataFrame,
    device_summary: pd.DataFrame,
    reason_summary: pd.DataFrame,
    model_summary: pd.DataFrame,
    thresholds: Dict,
    fig_dir: Path,
) -> None:
    setup_plot_font()

    fig_dir.mkdir(parents=True, exist_ok=True)

    valid = df[df["valid_vitals"]].copy()

    if valid.empty or device_summary.empty:
        for i in range(1, 11):
            save_empty_figure(
                fig_dir / f"fig_{i:02d}_empty.png",
                "No valid data",
                "No valid Heart/Breath rows were available.",
            )
        return

    # ------------------------------------------------------------
    # 01 Device coverage
    # ------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.bar(device_summary["device_id"], device_summary["analysis_rows"])
    ax.set_title("Device별 유효 분석 row 수")
    ax.set_xlabel("Device")
    ax.set_ylabel("Rows")
    ax.tick_params(axis="x", rotation=45)
    fig.tight_layout()
    fig.savefig(fig_dir / "fig_01_device_coverage.png", dpi=180)
    plt.close(fig)

    # ------------------------------------------------------------
    # 02 Pipeline funnel
    # ------------------------------------------------------------
    funnel = [
        ("Raw pivot", len(df)),
        ("Present + valid", int(valid.shape[0])),
        ("Fixed risk", int(valid["fixed_risk_flag"].sum())),
        ("Personalized risk", int(valid["personalized_risk_flag"].sum())),
        ("IF anomaly", int(valid["iforest_anomaly"].sum())),
    ]

    fig, ax = plt.subplots(figsize=(8.5, 5))
    labels, vals = zip(*funnel)
    ax.bar(labels, vals)
    ax.set_title("분석 파이프라인 Funnel")
    ax.set_ylabel("Rows")
    ax.tick_params(axis="x", rotation=20)

    for i, v in enumerate(vals):
        ax.text(i, v, f"{v:,}", ha="center", va="bottom", fontsize=9)

    fig.tight_layout()
    fig.savefig(fig_dir / "fig_02_pipeline_funnel.png", dpi=180)
    plt.close(fig)

    # ------------------------------------------------------------
    # 03 Heart distribution
    # ------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.hist(valid["Heart"].dropna(), bins=35, alpha=0.7)
    ax.set_title("Heart 분포")
    ax.set_xlabel("Heart bpm")
    ax.set_ylabel("Frequency")
    fig.tight_layout()
    fig.savefig(fig_dir / "fig_03_heart_distribution.png", dpi=180)
    plt.close(fig)

    # ------------------------------------------------------------
    # 04 Breath distribution
    # ------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.hist(valid["Breath"].dropna(), bins=35, alpha=0.7)
    ax.set_title("Breath 분포")
    ax.set_xlabel("Breath rpm")
    ax.set_ylabel("Frequency")
    fig.tight_layout()
    fig.savefig(fig_dir / "fig_04_breath_distribution.png", dpi=180)
    plt.close(fig)

    # ------------------------------------------------------------
    # 05 Correlation by device
    # ------------------------------------------------------------
    corr_series = pd.to_numeric(
        device_summary["heart_breath_corr"],
        errors="coerce",
    )

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.bar(device_summary["device_id"], corr_series.fillna(0))

    overall_corr = safe_corr(valid)

    if overall_corr is not None:
        ax.axhline(overall_corr, linestyle="--", linewidth=1)

    ax.set_title("Device별 Heart-Breath 상관계수")
    ax.set_xlabel("Device")
    ax.set_ylabel("Correlation r")
    ax.tick_params(axis="x", rotation=45)
    fig.tight_layout()
    fig.savefig(fig_dir / "fig_05_correlation_by_device.png", dpi=180)
    plt.close(fig)

    # ------------------------------------------------------------
    # 06 Risk rate by device
    # ------------------------------------------------------------
    x = np.arange(len(device_summary))
    width = 0.35

    fig, ax = plt.subplots(figsize=(10, 5))

    ax.bar(
        x - width / 2,
        device_summary["fixed_risk_rate"].astype(float) * 100,
        width,
        label="Fixed",
    )

    ax.bar(
        x + width / 2,
        device_summary["personalized_risk_rate"].astype(float) * 100,
        width,
        label="Personalized",
    )

    ax.set_title("Device별 위험 탐지율 비교")
    ax.set_xlabel("Device")
    ax.set_ylabel("Risk rate (%)")
    ax.set_xticks(x)
    ax.set_xticklabels(device_summary["device_id"], rotation=45)
    ax.legend()
    fig.tight_layout()
    fig.savefig(fig_dir / "fig_06_risk_rate_by_device.png", dpi=180)
    plt.close(fig)

    # ------------------------------------------------------------
    # 07 Timeline example
    # ------------------------------------------------------------
    sample_device = (
        device_summary.sort_values(
            "personalized_risk_rows",
            ascending=False,
        )["device_id"]
        .iloc[0]
    )

    g = (
        valid[valid["device_id"] == sample_device]
        .sort_values("datetime")
        .head(72 * 12)
    )

    fig, ax1 = plt.subplots(figsize=(12, 5))

    ax1.plot(g["datetime"], g["Heart"], label="Heart")
    ax1.set_ylabel("Heart bpm")
    ax1.tick_params(axis="x", rotation=30)

    ax2 = ax1.twinx()
    ax2.plot(g["datetime"], g["Breath"], linestyle="--", label="Breath")
    ax2.set_ylabel("Breath rpm")

    danger = g[g["personalized_risk_flag"] == 1]

    if not danger.empty:
        ax1.scatter(
            danger["datetime"],
            danger["Heart"],
            marker="x",
            s=35,
            label="Personalized risk",
        )

    ax1.set_title(f"72시간 예시 Timeline - {sample_device}")
    fig.tight_layout()
    fig.savefig(fig_dir / "fig_07_timeline_example.png", dpi=180)
    plt.close(fig)

    # ------------------------------------------------------------
    # 08 Threshold sensitivity heatmap
    # ------------------------------------------------------------
    z_vals = np.arange(2.0, 4.25, 0.25)
    d_vals = np.arange(12, 25, 2)

    heat = np.zeros((len(z_vals), len(d_vals)))

    for i, z in enumerate(z_vals):
        for j, d in enumerate(d_vals):
            flag = (
                (valid["Drop"] >= 0.5) |
                (valid["heart_robust_z"].abs() >= z) |
                (valid["breath_robust_z"].abs() >= z) |
                (valid["heart_delta"].abs() >= d) |
                (valid["breath_delta"].abs() >= max(4, d / 4))
            )

            heat[i, j] = flag.mean() * 100

    fig, ax = plt.subplots(figsize=(8.5, 5.5))
    im = ax.imshow(heat, aspect="auto", origin="lower")
    ax.set_xticks(np.arange(len(d_vals)))
    ax.set_xticklabels(d_vals)
    ax.set_yticks(np.arange(len(z_vals)))
    ax.set_yticklabels([f"{z:.2f}" for z in z_vals])
    ax.set_xlabel("Heart sudden delta threshold")
    ax.set_ylabel("Robust z threshold")
    ax.set_title("Threshold sensitivity: risk rate (%)")
    fig.colorbar(im, ax=ax)
    fig.tight_layout()
    fig.savefig(fig_dir / "fig_08_threshold_sensitivity.png", dpi=180)
    plt.close(fig)

    # ------------------------------------------------------------
    # 09 Model comparison
    # ------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(8.5, 5))

    x = np.arange(len(model_summary))

    ax.bar(
        x - 0.2,
        model_summary["anomaly_rate"].astype(float) * 100,
        0.4,
        label="Anomaly rate",
    )

    ax.bar(
        x + 0.2,
        model_summary["rule_overlap_precision_proxy"].astype(float) * 100,
        0.4,
        label="Rule overlap proxy",
    )

    ax.set_xticks(x)
    ax.set_xticklabels(model_summary["model"], rotation=0)
    ax.set_ylabel("Percent (%)")
    ax.set_title("비지도 이상탐지 모델 비교")
    ax.legend()
    fig.tight_layout()
    fig.savefig(fig_dir / "fig_09_model_comparison.png", dpi=180)
    plt.close(fig)

    # ------------------------------------------------------------
    # 10 Drop event window
    # ------------------------------------------------------------
    drops = valid[valid["Drop"] >= 0.5].copy()

    rows = []

    if not drops.empty:
        for _, drow in drops.iterrows():
            g = valid[
                (valid["device_id"] == drow["device_id"]) &
                (valid["patient_id"] == drow["patient_id"])
            ]

            g = g.sort_values("datetime").reset_index(drop=True)

            idx = g.index[g["datetime"] == drow["datetime"]]

            if len(idx) == 0:
                continue

            idx = int(idx[0])
            start = max(0, idx - 12)
            end = min(len(g), idx + 13)

            w = g.iloc[start:end].copy()

            w["relative_step"] = np.arange(len(w)) - (idx - start)

            rows.append(w[["relative_step", "Heart", "Breath"]])

    if rows:
        win = pd.concat(rows)

        agg = (
            win.groupby("relative_step")[["Heart", "Breath"]]
            .mean()
            .reset_index()
        )

        fig, ax1 = plt.subplots(figsize=(9, 5))

        ax1.plot(
            agg["relative_step"] * 5,
            agg["Heart"],
            marker="o",
            label="Heart",
        )

        ax1.set_xlabel("Minutes from Drop")
        ax1.set_ylabel("Heart bpm")

        ax2 = ax1.twinx()

        ax2.plot(
            agg["relative_step"] * 5,
            agg["Breath"],
            marker="s",
            linestyle="--",
            label="Breath",
        )

        ax2.set_ylabel("Breath rpm")

        ax1.axvline(0, linestyle=":", linewidth=1)
        ax1.set_title("Drop 이벤트 전후 평균 vital window")
        fig.tight_layout()
        fig.savefig(fig_dir / "fig_10_drop_event_window.png", dpi=180)
        plt.close(fig)

    else:
        save_empty_figure(
            fig_dir / "fig_10_drop_event_window.png",
            "Drop 이벤트 전후 평균 vital window",
            "No Drop event rows were found.",
        )


# ============================================================
# 8. Runner
# ============================================================

def run_pipeline(
    input_dir: Path,
    output_dir: Path,
    figure_dir: Path,
    model_dir: Path,
    config_dir: Path,
) -> Dict:
    schema = load_json(config_dir / "schema_mapping.json")
    config = load_json(config_dir / "pipeline_config.json")
    thresholds = load_json(config_dir / "threshold_config.json")

    output_dir.mkdir(parents=True, exist_ok=True)
    figure_dir.mkdir(parents=True, exist_ok=True)
    model_dir.mkdir(parents=True, exist_ok=True)

    wide_raw, import_report = ingest_all(input_dir, schema)

    write_csv(import_report, output_dir / "import_report.csv")
    write_csv(wide_raw, output_dir / "unified_wide_before_cleaning.csv")

    df, metrics = preprocess_features(wide_raw, config)
    df = assign_risk(df, thresholds)
    df, model_summary = train_models(df, config, model_dir)

    (
        device_summary,
        reason_summary,
        risk_summary,
        analysis_summary,
    ) = summarize_outputs(
        df,
        import_report,
        model_summary,
        metrics,
    )

    write_csv(df, output_dir / "unified_biosignal_risk_results.csv")
    write_csv(device_summary, output_dir / "device_summary.csv")
    write_csv(reason_summary, output_dir / "risk_reason_summary.csv")
    write_csv(risk_summary, output_dir / "risk_summary.csv")
    write_csv(model_summary, output_dir / "model_comparison_summary.csv")

    with open(output_dir / "analysis_summary.json", "w", encoding="utf-8") as f:
        json.dump(analysis_summary, f, indent=2, ensure_ascii=False)

    make_figures(
        df,
        device_summary,
        reason_summary,
        model_summary,
        thresholds,
        figure_dir,
    )

    return analysis_summary


def main() -> None:
    root = project_root()

    parser = argparse.ArgumentParser(
        description="Run multi-device radar biosignal ingestion, risk detection and anomaly modeling."
    )

    parser.add_argument(
        "--input-dir",
        default=str(root / "data" / "raw_devices"),
    )

    parser.add_argument(
        "--output-dir",
        default=str(root / "data" / "processed"),
    )

    parser.add_argument(
        "--figure-dir",
        default=str(root / "figures"),
    )

    parser.add_argument(
        "--model-dir",
        default=str(root / "models"),
    )

    parser.add_argument(
        "--config-dir",
        default=str(root / "configs"),
    )

    args = parser.parse_args()

    summary = run_pipeline(
        Path(args.input_dir),
        Path(args.output_dir),
        Path(args.figure_dir),
        Path(args.model_dir),
        Path(args.config_dir),
    )

    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()