from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

import json
import numpy as np
import pandas as pd


def project_root() -> Path:
    """
    src/common.py 기준으로 프로젝트 루트 경로 반환.
    """
    return Path(__file__).resolve().parents[1]


def load_json(path: Path) -> Dict[str, Any]:
    """
    JSON 설정 파일 읽기.
    """
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def write_csv(df: pd.DataFrame, path: Path) -> None:
    """
    DataFrame을 CSV로 저장.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig")


def list_input_files(input_dir: Path) -> List[Path]:
    """
    입력 폴더의 CSV/XLSX 파일 목록 반환.
    임시 파일, 숨김 파일은 제외.
    """
    input_dir.mkdir(parents=True, exist_ok=True)

    files: List[Path] = []

    for pattern in ["*.csv", "*.xlsx", "*.xls"]:
        files.extend(input_dir.glob(pattern))

    files = [
        p for p in files
        if not p.name.startswith("~$")
        and not p.name.startswith(".")
        and p.is_file()
    ]

    return sorted(files)


def find_column(df: pd.DataFrame, aliases: List[str]) -> Optional[str]:
    """
    DataFrame 컬럼 중 aliases와 일치하는 컬럼명을 찾는다.
    대소문자, 공백, 언더바 차이를 최대한 흡수.
    """
    if df is None or df.empty:
        return None

    columns = list(df.columns)

    # 1. exact match
    for alias in aliases:
        if alias in columns:
            return alias

    def norm(x: Any) -> str:
        return (
            str(x)
            .strip()
            .lower()
            .replace(" ", "")
            .replace("_", "")
            .replace("-", "")
        )

    norm_map = {norm(c): c for c in columns}

    for alias in aliases:
        key = norm(alias)
        if key in norm_map:
            return norm_map[key]

    return None


def read_table(path: Path) -> pd.DataFrame:
    """
    CSV/XLSX 파일 읽기.
    실제 export CSV에서 깨진 줄이 있어도 최대한 읽도록 처리한다.
    """
    suffix = path.suffix.lower()

    if suffix in [".xlsx", ".xls"]:
        return pd.read_excel(path)

    if suffix == ".csv":
        encodings = ["utf-8-sig", "utf-8", "cp949", "euc-kr"]

        last_error: Optional[Exception] = None

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

        if last_error is not None:
            raise last_error

    raise ValueError(f"Unsupported file type: {path}")


def ensure_datetime(
    df: pd.DataFrame,
    col_datetime: Optional[str],
    col_timestamp: Optional[str],
) -> pd.Series:
    """
    datetime 컬럼 또는 timestamp 컬럼을 datetime Series로 변환.
    timestamp는 초/밀리초/마이크로초/나노초를 자동 후보로 확인.
    """
    dt = pd.Series(pd.NaT, index=df.index)

    if col_datetime and col_datetime in df.columns:
        cand = pd.to_datetime(df[col_datetime], errors="coerce")
        if cand.notna().sum() > 0:
            dt = cand

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

    return dt


def robust_mad(series: pd.Series, floor: float = 1.0) -> float:
    """
    Median Absolute Deviation 기반 robust scale 계산.
    값이 너무 작으면 floor 적용.
    """
    s = pd.to_numeric(series, errors="coerce").dropna()

    if s.empty:
        return float(floor)

    med = s.median()
    mad = (s - med).abs().median()

    if pd.isna(mad) or mad <= 0:
        return float(floor)

    return float(max(mad, floor))


def episode_count(
    df: pd.DataFrame,
    flag_col: str,
    group_cols: List[str],
) -> int:
    """
    연속된 alert 구간을 episode 단위로 계산.
    """
    if df.empty or flag_col not in df.columns:
        return 0

    work = df.copy()

    if "datetime" in work.columns:
        work = work.sort_values(group_cols + ["datetime"])
    else:
        work = work.sort_values(group_cols)

    total = 0

    for _, g in work.groupby(group_cols, dropna=False):
        flag = pd.to_numeric(g[flag_col], errors="coerce").fillna(0).astype(int)
        starts = (flag.eq(1) & flag.shift(fill_value=0).eq(0)).sum()
        total += int(starts)

    return int(total)