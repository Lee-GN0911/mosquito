"""서울시 유문등 원본을 정제하고 모기 관측량 그래프와 집계표를 생성한다.

실행: python analysis.py
원본은 수정하지 않는다. 파일 경로는 이 스크립트의 위치를 기준으로 한다.
"""
from pathlib import Path
import json
import re

import numpy as np
import pandas as pd
import openpyxl
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
from matplotlib import font_manager
from matplotlib.patches import Patch

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "data/raw/mosquito_2008_2023.xlsx"
WEATHER_RAW = ROOT / "data/raw/weather_api"
OUT = ROOT / "data/processed"
IMAGES = ROOT / "images"
BLUE, ORANGE, GRAY = "#26718C", "#D16B3C", "#9BA7B0"


def read_mosquito():
    """시트마다 다른 열 위치를 제목으로 찾는다. 원본 행 번호를 보존한다."""
    book = openpyxl.load_workbook(RAW, data_only=True)
    records, issues = [], []
    for sheet in book:
        year = int(sheet.title)
        rows = list(sheet.values)
        header = rows[2]
        date_col = header.index("채집일")
        total_col = next(i for i, v in enumerate(header) if v in ("계", "모기 계"))
        species_header = rows[3] if year >= 2011 else header
        pip_col = species_header.index("빨간집모기")
        for row_num, row in enumerate(rows, 1):
            match = re.fullmatch(r"\s*(\d+)월\s*(\d+)주\s*", str(row[date_col]))
            if not match:  # 제목, 설명, 연간 총계는 관측값이 아니다.
                continue
            month, week = map(int, match.groups())
            species = row[date_col + 1:total_col]
            valid_species = [v for v in species if isinstance(v, (int, float))]
            total = row[total_col]
            if not isinstance(total, (int, float)) or total < 0:
                raise ValueError(f"합계 확인 필요: {year} 시트 {row_num}행")
            # 종별 칸 전체가 비어 있고 합계만 0이면 실제 무포집인지 판단 불가.
            ambiguous = len(valid_species) == 0
            if len(valid_species) != len(species):
                issues.append({"year": year, "source_row": row_num,
                               "week_label": row[date_col],
                               "issue": "all_species_blank" if ambiguous else "partial_species_blank"})
            if len(valid_species) == len(species) and sum(valid_species) != total:
                raise ValueError(f"종별 합과 원본 합계 불일치: {year} {row_num}행")
            records.append({"year": year, "month": month, "week_in_month": week,
                            "week_label": f"{month}월 {week}주", "mosquito_total": total,
                            "culex_pipiens": row[pip_col], "ambiguous_observation": ambiguous,
                            "source_sheet": sheet.title, "source_row": row_num})
    df = pd.DataFrame(records).sort_values(["year", "month", "week_in_month"]).reset_index(drop=True)
    if df.duplicated(["year", "month", "week_in_month"]).any():
        raise ValueError("연도·월·주차 중복이 있습니다.")
    selected = df[df.month.between(5, 10) & ~df.ambiguous_observation].copy()
    if len(selected) < 100:
        raise ValueError("분석 가능한 실제 시계열 관측값이 100개 미만입니다.")
    if selected[["mosquito_total", "culex_pipiens"]].isna().any().any():
        raise ValueError("분석 대상 열에 결측값이 있습니다.")
    return df, selected, issues


def aggregate(weekly):
    monthly = weekly.groupby(["year", "month"], as_index=False).agg(
        mosquito_mean=("mosquito_total", "mean"), mosquito_sum=("mosquito_total", "sum"),
        weeks_observed=("mosquito_total", "size"), pipiens_mean=("culex_pipiens", "mean"))
    # 6개 월을 동일한 비중으로 평균: 관측 주가 많은 월에 가중치가 쏠리지 않게 한다.
    annual = monthly.groupby("year").agg(
        months_observed=("month", "size"), mean_monthly_count=("mosquito_mean", "mean"),
        weeks_observed=("weeks_observed", "sum"))
    annual["complete_months"] = annual.months_observed.eq(6)
    annual.loc[~annual.complete_months, "mean_monthly_count"] = np.nan
    # pct_change의 기본 결측 전파에 의존하지 않고 직전 달력 연도와 직접 계산.
    previous = annual.mean_monthly_count.shift(1)
    annual["yoy_percent"] = (annual.mean_monthly_count / previous - 1) * 100
    annual.loc[previous.eq(0), "yoy_percent"] = np.nan
    peaks = monthly.loc[monthly.groupby("year").mosquito_mean.idxmax(), ["year", "month", "mosquito_mean"]]
    peaks = peaks.rename(columns={"month": "peak_month", "mosquito_mean": "peak_month_mean"})
    annual = annual.reset_index().merge(peaks, on="year", validate="one_to_one")
    seasonal = monthly[monthly.month.between(6, 10)].copy()
    seasonal["season"] = np.where(seasonal.month.le(8), "summer", "autumn")
    seasons = seasonal.pivot_table(index="year", columns="season", values="mosquito_mean", aggfunc="mean")
    # 가을 두 달 중 하나라도 없으면 가을 평균과 비율은 계산하지 않는다.
    counts = seasonal.groupby(["year", "season"]).size().unstack()
    seasons.loc[counts.autumn.ne(2), "autumn"] = np.nan
    seasons.loc[counts.summer.ne(3), "summer"] = np.nan
    seasons["autumn_summer_ratio"] = seasons.autumn / seasons.summer.replace(0, np.nan)
    return monthly, annual.merge(seasons.reset_index(), on="year", validate="one_to_one")


def read_weather():
    """기상청 ASOS 서울(108) 일자료에서 분석에 필요한 다섯 요소만 읽는다."""
    rows = []
    for path in sorted(WEATHER_RAW.glob("seoul_asos_*.txt")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if not (len(line) >= 8 and line[:8].isdigit()):
                continue
            values = line.split()
            if len(values) != 56:
                raise ValueError(f"기상자료 열 수 확인 필요: {path.name} {values[0]}")
            rows.append({"date": values[0], "station_id": values[1],
                         "avg_temp": values[10], "max_temp": values[11],
                         "avg_humidity": values[18], "rainfall_raw": values[38]})
    weather = pd.DataFrame(rows)
    if len(weather) != 5844:
        raise ValueError(f"기상 일자료는 5,844행이어야 합니다: 현재 {len(weather):,}행")
    weather["date"] = pd.to_datetime(weather.date, format="%Y%m%d")
    for col in ["avg_temp", "max_temp", "avg_humidity", "rainfall_raw"]:
        weather[col] = pd.to_numeric(weather[col], errors="raise")
    weather["rainfall"] = weather.rainfall_raw.mask(weather.rainfall_raw.eq(-9), 0)
    weather[["avg_temp", "max_temp", "avg_humidity"]] = weather[
        ["avg_temp", "max_temp", "avg_humidity"]].mask(lambda x: x.eq(-9))
    weather["heatwave_day"] = weather.max_temp.ge(33)
    weather["year"], weather["month"] = weather.date.dt.year, weather.date.dt.month
    selected = weather[weather.month.between(5, 10)].copy()
    monthly = selected.groupby(["year", "month"], as_index=False).agg(
        avg_temp=("avg_temp", "mean"), avg_max_temp=("max_temp", "mean"),
        peak_temp=("max_temp", "max"), rainfall=("rainfall", "sum"),
        avg_humidity=("avg_humidity", "mean"), heatwave_days=("heatwave_day", "sum"),
        weather_days=("date", "size"))
    return weather, monthly


def combine_weather(mosquito_monthly, weather_monthly):
    combined = mosquito_monthly.merge(weather_monthly, on=["year", "month"], validate="one_to_one")
    if len(combined) != len(mosquito_monthly):
        raise ValueError("모기와 기상 월자료의 결합 행 수가 다릅니다.")
    metrics = ["avg_temp", "avg_max_temp", "peak_temp", "rainfall", "avg_humidity", "heatwave_days"]
    stats = []
    for metric in metrics:
        overall = combined.mosquito_mean.corr(combined[metric], method="spearman")
        # 월별 계절성을 제거한 뒤 순위상관: 같은 달 안에서 연도 차이를 비교한다.
        mosquito_rank = combined.groupby("month").mosquito_mean.rank()
        metric_rank = combined.groupby("month")[metric].rank()
        within_month = mosquito_rank.corr(metric_rank)
        stats.append({"weather_metric": metric, "spearman_overall": overall,
                      "spearman_within_month": within_month, "observations": len(combined)})
    return combined, pd.DataFrame(stats)


def style():
    font = ROOT / "assets/NanumGothic-Regular.ttf"
    font_manager.fontManager.addfont(str(font))
    plt.rcParams.update({"font.family": "NanumGothic", "font.size": 11, "axes.unicode_minus": False,
                         "axes.spines.top": False, "axes.spines.right": False,
                         "axes.edgecolor": "#CBD2D8", "axes.labelcolor": "#334550",
                         "xtick.color": "#52626C", "ytick.color": "#52626C",
                         "figure.facecolor": "white", "axes.facecolor": "white",
                         "axes.titleweight": "bold", "axes.titlepad": 15,
                         "savefig.dpi": 170})


def save(fig, name, note):
    fig.set_layout_engine("constrained", rect=(0, .055, 1, .945))
    fig.text(.02, .012, note, fontsize=9, color="#60717C")
    fig.savefig(IMAGES / name, bbox_inches="tight")
    plt.close(fig)


def make_charts(weekly, monthly, annual, combined, correlations):
    style()
    # 원본에 실제 날짜가 없으므로 연도+월+월내 주차 순서를 표시한다.
    fig, ax = plt.subplots(figsize=(14, 4.8), layout="constrained")
    for year, part in weekly.groupby("year"):
        x = year + (part.month - 1 + (part.week_in_month - 1) / 5) / 12
        ax.plot(x, part.mosquito_total, color=BLUE, lw=1.2, marker="o", ms=2)
    ax.set(title="서울 모기 관측량은 어떻게 변했을까?", ylabel="주별 포집량 · 전체 종 (마리)", xlabel="연도 · 5~10월 관측 기록")
    ax.set_xticks(range(2008, 2024))
    ax.set_ylim(bottom=0)
    ax.grid(axis="y", alpha=.16)
    save(fig, "01_weekly_counts.png", "출처: 서울시 유문등 채집 자료. 가로축은 월·주차의 순서이며 실제 날짜가 아님. 연도 사이 비관측 구간은 연결하지 않음.")

    fig, ax = plt.subplots(figsize=(14, 5.2), layout="constrained")
    ax.bar(annual.year, annual.mean_monthly_count, color=BLUE, width=.65)
    for row in annual.itertuples():
        if pd.notna(row.mean_monthly_count):
            ax.text(row.year, row.mean_monthly_count + 10, f"{row.mean_monthly_count:.0f}", ha="center", fontsize=10)
        else:
            ax.text(row.year, 15, "10월\n자료 없음", ha="center", fontsize=9, color=ORANGE)
    ax.set(title="해마다 모기 관측 수준은 높아졌을까?", ylabel="5~10월 월평균 포집량의 평균 (마리)", xlabel="연도")
    ax.set_xticks(annual.year)
    ax.set_ylim(0, annual.mean_monthly_count.max() * 1.18)
    ax.grid(axis="y", alpha=.16)
    save(fig, "02_annual_counts.png", "6개 월을 같은 비중으로 평균. 2009년은 10월 부재로 제외. 관측 지점·횟수 변화까지 보정한 값은 아님.")

    fig, axes = plt.subplots(4, 4, figsize=(14, 12), sharex=True, sharey=True, layout="constrained")
    limit = monthly.mosquito_mean.max() * 1.18
    for ax, year in zip(axes.flat, range(2008, 2024)):
        part = monthly[monthly.year.eq(year)].set_index("month").reindex(range(5, 11))
        ax.bar(part.index, part.mosquito_mean, color=[ORANGE if m >= 9 else BLUE for m in part.index], width=.7)
        peak = part.mosquito_mean.idxmax()
        ax.text(peak, part.loc[peak, "mosquito_mean"] + 18, f"{part.loc[peak, 'mosquito_mean']:.0f}", ha="center", fontsize=9)
        if year == 2009:
            ax.text(10, 20, "자료 없음", ha="center", fontsize=8, color=ORANGE)
        ax.set_title(str(year), loc="left", fontsize=12)
        ax.set_ylim(0, limit)
        ax.set_xticks(range(5, 11))
        ax.tick_params(labelbottom=True)
        ax.grid(axis="y", alpha=.14)
    fig.suptitle("모기가 가장 많았던 달은 바뀌었을까?", fontsize=17)
    fig.supxlabel("월")
    fig.legend(handles=[Patch(color=BLUE, label="5~8월"),
                        Patch(color=ORANGE, label="가을 · 9~10월")],
               loc="lower right", bbox_to_anchor=(.99, .018), ncol=2,
               frameon=False, fontsize=10)
    fig.supylabel("월별 평균 주간 포집량 · 전체 종 (마리)")
    save(fig, "03_monthly_counts.png", "모든 연도의 세로축 범위가 같음. 막대는 월별 관측 주의 평균. 자료가 없는 달은 0이 아님.")

    annual_weather = combined.groupby("year", as_index=False).agg(
        avg_temp=("avg_temp", "mean"), heatwave_days=("heatwave_days", "sum"))
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 7.5), sharex=True, layout="constrained")
    ax1.plot(annual_weather.year, annual_weather.avg_temp, color=ORANGE, marker="o", lw=2.2)
    for row in annual_weather.itertuples():
        ax1.text(row.year, row.avg_temp + .08, f"{row.avg_temp:.1f}", ha="center", fontsize=9)
    ax1.set(title="5~10월 평균기온은 어떻게 변했을까?", ylabel="평균기온 (도)")
    ax1.grid(axis="y", alpha=.16)
    ax2.bar(annual_weather.year, annual_weather.heatwave_days, color="#D99163", width=.65)
    ax2.set(title="같은 기간 최고기온 33도 이상인 날은 얼마나 있었을까?", ylabel="폭염 기준일 수", xlabel="연도")
    ax2.set_xticks(annual_weather.year)
    ax2.yaxis.set_major_locator(MaxNLocator(integer=True))
    ax2.grid(axis="y", alpha=.16)
    save(fig, "04_temperature_trend.png", "출처: 기상청 ASOS 서울(108) 일자료. 평균기온은 5~10월 일평균기온의 평균, 폭염 기준일은 일최고기온 33도 이상.")

    plot_data = combined.copy()
    plot_data["x"] = plot_data.year + (plot_data.month - 1) / 12
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 7.5), sharex=True, layout="constrained")
    for year, part in plot_data.groupby("year"):
        ax1.plot(part.x, part.mosquito_mean, color=BLUE, marker="o", lw=1.5)
        ax2.plot(part.x, part.avg_temp, color=ORANGE, marker="o", lw=1.5)
    ax1.set(title="같은 달의 모기 관측량과 기온을 나란히 보면", ylabel="월평균 주간 포집량 (마리)")
    ax2.set(ylabel="월평균기온 (도)", xlabel="연도 · 5~10월", xticks=range(2008, 2024))
    ax1.grid(axis="y", alpha=.16); ax2.grid(axis="y", alpha=.16)
    save(fig, "05_mosquito_temperature_timeline.png", "각 연도 안에서 5~10월만 연결함. 모기 원자료에는 정확한 날짜가 없어 월 단위로 결합함.")

    labels = [("avg_temp", "월평균기온 (도)"), ("rainfall", "월강수량 (mm)"),
              ("avg_humidity", "월평균 상대습도 (%)")]
    stat_map = correlations.set_index("weather_metric")
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.8), layout="constrained")
    colors = np.where(combined.month.ge(9), ORANGE, BLUE)
    for ax, (metric, label) in zip(axes, labels):
        ax.scatter(combined[metric], combined.mosquito_mean, c=colors, alpha=.72, s=35)
        clean = combined[[metric, "mosquito_mean"]].dropna()
        slope, intercept = np.polyfit(clean[metric], clean.mosquito_mean, 1)
        xs = np.linspace(clean[metric].min(), clean[metric].max(), 100)
        ax.plot(xs, slope * xs + intercept, color="#475761", lw=1.4, ls="--")
        row = stat_map.loc[metric]
        ax.set(title=f"전체 상관={row.spearman_overall:.2f} · 월통제={row.spearman_within_month:.2f}",
               xlabel=label)
        ax.grid(alpha=.14)
    axes[0].set_ylabel("월평균 주간 포집량 (마리)")
    fig.suptitle("기온만으로 충분할까? 강수량·습도와 함께 비교", fontsize=17)
    fig.legend(handles=[Patch(color=BLUE, label="5~8월"), Patch(color=ORANGE, label="9~10월")],
               loc="lower right", ncol=2, frameon=False)
    save(fig, "06_weather_relationships.png", "점 1개는 연도·월 1개. 상관은 스피어만 순위상관. ‘월통제’는 달별 순위를 사용해 계절 차이를 줄인 탐색값이며 인과효과가 아님.")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    IMAGES.mkdir(parents=True, exist_ok=True)
    all_rows, weekly, issues = read_mosquito()
    monthly, annual = aggregate(weekly)
    weather_daily, weather_monthly = read_weather()
    combined, correlations = combine_weather(monthly, weather_monthly)
    for name, frame in [("mosquito_all_weeks.csv", all_rows), ("mosquito_may_oct.csv", weekly),
                        ("mosquito_monthly.csv", monthly), ("mosquito_annual.csv", annual)]:
        frame.to_csv(OUT / name, index=False, encoding="utf-8-sig", float_format="%.6f")
    for name, frame in [("weather_daily.csv", weather_daily), ("weather_monthly.csv", weather_monthly),
                        ("mosquito_weather_monthly.csv", combined), ("weather_correlations.csv", correlations)]:
        frame.to_csv(OUT / name, index=False, encoding="utf-8-sig", float_format="%.6f")
    audit = {"source_rows": len(all_rows), "analysis_rows": len(weekly), "monthly_rows": len(monthly),
             "duplicate_keys": 0, "missing_analysis_values": 0, "source_issues": issues,
             "annual_excluded_years": annual.loc[~annual.complete_months, "year"].tolist(),
             "species_total_check": "all fully numeric species rows reconcile to source total",
             "weather_daily_rows": len(weather_daily), "weather_monthly_rows": len(weather_monthly),
             "combined_monthly_rows": len(combined), "weather_station": 108,
             "weather_daily_field_count": 56,
             "weather_rain_minus9_rule": "treated as zero precipitation; other selected -9 values treated as missing"}
    (OUT / "quality_check.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")
    make_charts(weekly, monthly, annual, combined, correlations)
    print(f"완료: 모기 주간 {len(weekly)}행, 결합 월별 {len(combined)}행, 그래프 6개")
    print("\n기상요소와 모기 관측량의 스피어만 상관")
    print(correlations.round(3).to_string(index=False))
    print(annual.round(2).to_string(index=False))


if __name__ == "__main__":
    main()
