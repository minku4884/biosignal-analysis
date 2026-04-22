# python -m streamlit run app_streamlit.py
import json
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd

PROJECT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_DIR / "data"
FIG_DIR = PROJECT_DIR / "figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)

RAW_PATH = DATA_DIR / "biosignal_raw_long_simulated.csv"

plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.dpi"] = 160


def save_fig(path: Path):
    plt.tight_layout()
    plt.savefig(path, bbox_inches="tight", facecolor="white")
    plt.close()


def main():
    raw_df = pd.read_csv(RAW_PATH)
    raw_df.head(20).to_csv(DATA_DIR / "raw_sample_20rows.csv", index=False, encoding="utf-8-sig")

    # device_id 익명화
    raw_df["device_id"] = raw_df["device_id"].apply(lambda x: f"device_{int(x)}")

    # long -> wide
    wide_df = raw_df.pivot_table(
        index=["timestamp", "device_id"],
        columns="data_category",
        values="avg_value",
        aggfunc="mean"
    ).reset_index()

    wide_df.columns = ["timestamp", "device_id", "Status", "Drop", "Breath", "Heart"]
    wide_df["datetime"] = pd.to_datetime(wide_df["timestamp"], unit="s")
    wide_df = wide_df[["datetime", "timestamp", "device_id", "Status", "Breath", "Heart", "Drop"]]
    wide_df = wide_df.sort_values("datetime").reset_index(drop=True)

    # 전처리
    clean_df = wide_df.dropna(subset=["Heart", "Breath", "Status", "Drop"]).copy()
    clean_df = clean_df[clean_df["Status"] == 1].copy()
    clean_df = clean_df[
        (clean_df["Heart"].between(45, 130)) &
        (clean_df["Breath"].between(8, 30))
    ].copy()

    # 파생 변수
    clean_df["heart_roll5"] = clean_df["Heart"].rolling(5, min_periods=1).mean().round(2)
    clean_df["breath_roll5"] = clean_df["Breath"].rolling(5, min_periods=1).mean().round(2)
    clean_df["heart_delta"] = clean_df["Heart"].diff().fillna(0).round(2)
    clean_df["breath_delta"] = clean_df["Breath"].diff().fillna(0).round(2)
    clean_df["hour"] = clean_df["datetime"].dt.hour
    clean_df["date"] = clean_df["datetime"].dt.date.astype(str)

    # 위험 상태 정의
    # 1) Drop 발생
    # 2) Heart > 100
    # 3) Breath > 25
    # 4) Heart 급변(직전 대비 15 이상)
    # 5) Breath 급변(직전 대비 5 이상)
    clean_df["risk_flag"] = (
        (clean_df["Drop"] == 1) |
        (clean_df["Heart"] > 100) |
        (clean_df["Breath"] > 25) |
        (clean_df["heart_delta"].abs() >= 15) |
        (clean_df["breath_delta"].abs() >= 5)
    ).astype(int)

    def classify_risk(row):
        if row["Drop"] == 1:
            return "Drop Event"
        if row["Heart"] > 100 and row["Breath"] > 25:
            return "High Heart + High Breath"
        if row["Heart"] > 100:
            return "High Heart"
        if row["Breath"] > 25:
            return "High Breath"
        if abs(row["heart_delta"]) >= 15 or abs(row["breath_delta"]) >= 5:
            return "Sudden Change"
        return "Normal"

    clean_df["risk_type"] = clean_df.apply(classify_risk, axis=1)

    # 저장
    wide_df.to_csv(DATA_DIR / "biosignal_wide_before_cleaning.csv", index=False, encoding="utf-8-sig")
    clean_df.to_csv(DATA_DIR / "biosignal_processed_wide.csv", index=False, encoding="utf-8-sig")

    duplicate_count = int(
        raw_df.duplicated(subset=["timestamp", "device_id", "data_category"], keep=False).sum()
    )
    desc = clean_df[["Heart", "Breath"]].describe().round(2)

    summary = {
        "raw_rows": int(len(raw_df)),
        "wide_rows_before_cleaning": int(len(wide_df)),
        "analysis_rows_after_cleaning": int(len(clean_df)),
        "duplicate_raw_rows": duplicate_count,
        "missing_heart_rows": int(wide_df["Heart"].isna().sum()),
        "missing_breath_rows": int(wide_df["Breath"].isna().sum()),
        "heart_outlier_rows": int(
            ((wide_df["Heart"] > 130) | ((wide_df["Heart"] > 0) & (wide_df["Heart"] < 45))).sum()
        ),
        "breath_outlier_rows": int(
            ((wide_df["Breath"] > 30) | ((wide_df["Breath"] > 0) & (wide_df["Breath"] < 8))).sum()
        ),
        "present_minutes_before_cleaning": int((wide_df["Status"] == 1).sum()),
        "absent_minutes_before_cleaning": int((wide_df["Status"] == 0).sum()),
        "drop_events_after_cleaning": int(clean_df["Drop"].sum()),
        "risk_rows_after_cleaning": int(clean_df["risk_flag"].sum()),
        "heart_breath_correlation": round(float(clean_df[["Heart", "Breath"]].corr().iloc[0, 1]), 3),
        "heart_mean": float(desc.loc["mean", "Heart"]),
        "heart_std": float(desc.loc["std", "Heart"]),
        "heart_min": float(desc.loc["min", "Heart"]),
        "heart_max": float(desc.loc["max", "Heart"]),
        "breath_mean": float(desc.loc["mean", "Breath"]),
        "breath_std": float(desc.loc["std", "Breath"]),
        "breath_min": float(desc.loc["min", "Breath"]),
        "breath_max": float(desc.loc["max", "Breath"]),
    }

    (DATA_DIR / "analysis_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    preprocess_table = pd.DataFrame([
        ["Raw long rows", len(raw_df), "Includes duplicates and partial missing rows"],
        ["After pivot", len(wide_df), "One row per timestamp"],
        [
            "After missing removal",
            len(wide_df.dropna(subset=["Heart", "Breath", "Status", "Drop"])),
            "Removed partial timestamps"
        ],
        [
            "After presence filter",
            len(
                wide_df.dropna(subset=["Heart", "Breath", "Status", "Drop"])[
                    wide_df.dropna(subset=["Heart", "Breath", "Status", "Drop"])["Status"] == 1
                ]
            ),
            "Removed absent periods"
        ],
        ["Final cleaned rows", len(clean_df), "Heart 45-130, Breath 8-30"],
    ], columns=["step", "rows", "note"])

    preprocess_table.to_csv(DATA_DIR / "preprocessing_summary.csv", index=False, encoding="utf-8-sig")
    desc.to_csv(DATA_DIR / "descriptive_statistics.csv", encoding="utf-8-sig")

    # 그래프 색상 정의
    COLOR_FUNNEL = "#4E79A7"
    COLOR_PRESENT = "#59A14F"
    COLOR_ABSENT = "#E15759"
    COLOR_HEART = "#D62728"
    COLOR_BREATH = "#1F77B4"
    COLOR_DROP = "#9467BD"
    COLOR_HIST_HEART = "#FF7F0E"
    COLOR_HIST_BREATH = "#2CA02C"
    COLOR_SCATTER = "#17BECF"
    COLOR_HOURLY_HEART = "#C44E52"
    COLOR_HOURLY_BREATH = "#4C72B0"

    # 그래프 1: 전처리 퍼널
    plt.figure(figsize=(8.2, 4.5))
    bars = plt.bar(
        preprocess_table["step"],
        preprocess_table["rows"],
        color=COLOR_FUNNEL,
        edgecolor="black",
        alpha=0.85
    )
    plt.title("Preprocessing Funnel")
    plt.ylabel("Row count")
    plt.xticks(rotation=15, ha="right")
    for b, v in zip(bars, preprocess_table["rows"]):
        plt.text(
            b.get_x() + b.get_width() / 2,
            v + max(preprocess_table["rows"]) * 0.015,
            f"{v:,}",
            ha="center",
            va="bottom",
            fontsize=9
        )
    save_fig(FIG_DIR / "fig_01_preprocessing_funnel.png")

    # 그래프 2: 재실 / 부재
    counts = pd.Series({
        "Present": summary["present_minutes_before_cleaning"],
        "Absent": summary["absent_minutes_before_cleaning"]
    })
    plt.figure(figsize=(5.2, 4.2))
    bars = plt.bar(
        counts.index,
        counts.values,
        color=[COLOR_PRESENT, COLOR_ABSENT],
        edgecolor="black",
        alpha=0.85
    )
    plt.title("Presence Status Distribution")
    plt.ylabel("Minutes")
    for b, v in zip(bars, counts.values):
        plt.text(
            b.get_x() + b.get_width() / 2,
            v + counts.max() * 0.02,
            f"{v:,}",
            ha="center",
            va="bottom",
            fontsize=10
        )
    save_fig(FIG_DIR / "fig_02_status_distribution.png")

    # 그래프 3: 72시간 타임라인
    timeline = clean_df.iloc[:72 * 60].copy()
    fig, ax1 = plt.subplots(figsize=(10.5, 4.8))
    ax1.plot(
        timeline["datetime"],
        timeline["Heart"],
        linewidth=1.2,
        color=COLOR_HEART,
        label="Heart"
    )
    ax1.set_ylabel("Heart (bpm)", color=COLOR_HEART)
    ax1.tick_params(axis="y", labelcolor=COLOR_HEART)
    ax1.xaxis.set_major_locator(mdates.HourLocator(interval=12))
    ax1.xaxis.set_major_formatter(mdates.DateFormatter("%m-%d %H:%M"))

    ax2 = ax1.twinx()
    ax2.plot(
        timeline["datetime"],
        timeline["Breath"],
        linewidth=1.0,
        alpha=0.9,
        color=COLOR_BREATH,
        label="Breath"
    )
    ax2.set_ylabel("Breath (rpm)", color=COLOR_BREATH)
    ax2.tick_params(axis="y", labelcolor=COLOR_BREATH)

    for d in timeline[timeline["Drop"] == 1]["datetime"]:
        ax1.axvline(d, linestyle="--", linewidth=1, color=COLOR_DROP, alpha=0.9)

    plt.title("72-Hour Vital Sign Timeline")
    fig.autofmt_xdate()
    save_fig(FIG_DIR / "fig_03_timeline_72h.png")

    # 그래프 4: 분포
    fig, axes = plt.subplots(1, 2, figsize=(9.6, 3.9))
    axes[0].hist(clean_df["Heart"], bins=28, edgecolor="white", color=COLOR_HIST_HEART, alpha=0.9)
    axes[0].set_title("Heart Distribution")
    axes[0].set_xlabel("bpm")
    axes[0].set_ylabel("Count")

    axes[1].hist(clean_df["Breath"], bins=24, edgecolor="white", color=COLOR_HIST_BREATH, alpha=0.9)
    axes[1].set_title("Breath Distribution")
    axes[1].set_xlabel("rpm")
    axes[1].set_ylabel("Count")
    save_fig(FIG_DIR / "fig_04_distributions.png")

    # 그래프 5: 상관관계
    sample = clean_df.sample(n=min(2500, len(clean_df)), random_state=42)
    plt.figure(figsize=(5.4, 4.5))
    plt.scatter(
        sample["Heart"],
        sample["Breath"],
        s=10,
        alpha=0.35,
        color=COLOR_SCATTER
    )
    plt.title(f'Heart vs Breath Correlation (r={summary["heart_breath_correlation"]})')
    plt.xlabel("Heart (bpm)")
    plt.ylabel("Breath (rpm)")
    save_fig(FIG_DIR / "fig_05_correlation_scatter.png")

    # 그래프 6: 낙상 이벤트 전후
    if clean_df["Drop"].sum() > 0:
        drop_idx = clean_df.index[clean_df["Drop"] == 1][0]
        window = clean_df.loc[
            max(drop_idx - 20, clean_df.index.min()): min(drop_idx + 20, clean_df.index.max())
        ].copy()

        plt.figure(figsize=(8.4, 4.4))
        plt.plot(
            window["datetime"],
            window["Heart"],
            label="Heart",
            linewidth=1.5,
            color=COLOR_HEART
        )
        plt.plot(
            window["datetime"],
            window["Breath"] * 4,
            label="Breath x4",
            linewidth=1.5,
            color=COLOR_BREATH
        )
        drop_time = clean_df.loc[drop_idx, "datetime"]
        plt.axvline(
            drop_time,
            linestyle="--",
            linewidth=1.3,
            label="Drop event",
            color=COLOR_DROP
        )
        plt.title("Representative Drop Event Window (+/-20 min)")
        plt.ylabel("Scaled value")
        plt.xlabel("Time")
        plt.legend(frameon=False, ncol=3)
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter("%m-%d %H:%M"))
        plt.xticks(rotation=20, ha="right")
        save_fig(FIG_DIR / "fig_06_drop_event_window.png")

    # 그래프 7: 시간대별 평균 패턴
    hourly = clean_df.groupby("hour")[["Heart", "Breath"]].mean().reset_index()
    fig, ax1 = plt.subplots(figsize=(8.6, 4.2))
    ax1.plot(
        hourly["hour"],
        hourly["Heart"],
        marker="o",
        linewidth=1.6,
        color=COLOR_HOURLY_HEART
    )
    ax1.set_xlabel("Hour of day")
    ax1.set_ylabel("Heart (bpm)", color=COLOR_HOURLY_HEART)
    ax1.tick_params(axis="y", labelcolor=COLOR_HOURLY_HEART)
    ax1.set_xticks(range(0, 24, 2))

    ax2 = ax1.twinx()
    ax2.plot(
        hourly["hour"],
        hourly["Breath"],
        marker="s",
        linewidth=1.4,
        color=COLOR_HOURLY_BREATH
    )
    ax2.set_ylabel("Breath (rpm)", color=COLOR_HOURLY_BREATH)
    ax2.tick_params(axis="y", labelcolor=COLOR_HOURLY_BREATH)

    plt.title("Average Vital Signs by Hour")
    save_fig(FIG_DIR / "fig_07_hourly_pattern.png")

    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()