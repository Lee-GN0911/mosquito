"""우주 발사 횟수·발사 비용·우주에 간 사람 수를 연도별로 집계하고 선그래프를 만든다.

실행: python analysis.py   (먼저 python collect_data.py 로 원자료를 받는다)
원자료는 수정하지 않는다. 결과는 data/processed 와 images 에 저장한다.
"""
from pathlib import Path
import json

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.ticker import FuncFormatter

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "data/raw"
OUT = ROOT / "data/processed"
IMAGES = ROOT / "images"
from paths import FONT
BLUE, ORANGE, GRAY, DARK = "#26718C", "#D16B3C", "#9BA7B0", "#2B3A42"

LAST_FULL_YEAR = 2025          # 2026년은 아직 진행 중이라 추세 계산에서 뺀다.
# 비교 기준 연도: 2025년 한 해와 비교하므로 기준도 한 해(2000년)로 잡는다.
# 2011~2015년은 우주왕복선 퇴역 직후라 유인비행이 유난히 적어 기준으로 쓰면 증가가 부풀려진다.
BASE_YEAR = 2000
FORECAST_YEARS = (2021, LAST_FULL_YEAR)  # 민간 유인선·대량 발사가 자리 잡은 뒤 5년
SOURCE_NOTE = "자료: GCAT·유인비행 목록(Jonathan McDowell, planet4589.org)"
COST_NOTE = "자료: Our World in Data / CSIS Aerospace Security (2021년 미국 달러 기준)"


def read_tsv(name):
    """McDowell 파일은 '#'으로 시작하는 제목·주석 줄이 섞여 있다."""
    df = pd.read_csv(RAW / name, sep="\t", dtype=str)
    df.columns = [c.lstrip("#").strip() for c in df.columns]
    df = df.apply(lambda s: s.str.strip())
    first = df.columns[0]
    return df[~df[first].fillna("#").str.startswith("#")].copy()


# ---------------------------------------------------------------- 집계
def launches_by_year():
    d = read_tsv("launch.tsv")
    d = d[d["LaunchCode"].str[0] == "O"].copy()  # 궤도 발사(성공 + 실패)만
    d["year"] = d["Launch_Date"].str[:4].astype(int)
    d["success"] = d["LaunchCode"].str[1] == "S"
    d["spacex"] = d["LV_Type"].str.startswith(("Falcon", "Starship"))
    g = d.groupby("year").agg(launches=("success", "size"), successes=("success", "sum"),
                              spacex=("spacex", "sum"))
    g["without_spacex"] = g["launches"] - g["spacex"]
    return g, d["Launch_Date"].max()


def people_by_year():
    missions = read_tsv("missions.tsv")
    missions = missions[missions["MType"] == "FLT"]  # 실패·동물 비행 제외
    missions["kind"] = np.where(missions["OrbID"].str.startswith("ORB"), "orbital", "suborbital")
    rides = read_tsv("rides.tsv")
    rides = rides[rides["Categ"] != "A"]  # 침팬지 제외
    j = rides.merge(missions[["HSFID", "kind"]], on="HSFID", how="inner")
    j["year"] = j["LDate"].str[:4].astype(int)
    people = j.groupby(["year", "kind"]).size().unstack(fill_value=0)
    people["total"] = people.sum(axis=1)
    missions["year"] = missions["LDate"].str[:4].astype(int)
    crewed_orbital = missions[missions["kind"] == "orbital"].groupby("year").size().rename("crewed_orbital_launches")
    first_flight = j.sort_values("LDate").drop_duplicates("ID").groupby("year").size().rename("new_people")
    return people.join(crewed_orbital).join(first_flight).fillna(0).astype(int), len(j), len(rides)


# OWID 로켓 이름 → GCAT 로켓 이름(정규식). 같은 계열의 변형 모델은 같은 가격으로 본다.
# 가격 표에 없는 계열(예: 보스호트, 몰니야, 아리안 5ECA, 창정 6A)은 일부러 연결하지 않는다.
VEHICLE_MAP = {
    "Angara": r"Angara", "Antares": r"Antares", "Ariane 44": r"Ariane 44", "Ariane 5G": r"Ariane 5G",
    "Athena 1": r"Athena-?1|LLV1", "Atlas Centaur": r"Atlas (LV-3C|SLV-3C|SLV-3D|G) Centaur|Atlas Centaur",
    "Atlas II": r"Atlas II(A|AS)?$", "Atlas III": r"Atlas III", "Atlas V": r"Atlas V ",
    "Delta 3910": r"Delta 3910", "Delta 3000-Series": r"Delta 3\d{3}", "Delta E": r"Thor Delta E",
    "Delta II": r"Delta (6|7)\d{3}", "Delta III": r"Delta 8930", "Delta IV Heavy": r"Delta 4H",
    "Delta IV": r"Delta 4M", "Dnepr": r"Dnepr", "Electron": r"Electron", "Epsilon": r"Epsilon",
    "Falcon 1": r"Falcon 1", "Falcon 9": r"Falcon 9", "Falcon Heavy": r"Falcon Heavy",
    "GSLV": r"GSLV Mk ?(I|II)$|GSLV$", "LVM3": r"GSLV Mk ?III|LVM3", "H-II": r"H-II$",
    "Kosmos": r"Kosmos (11K65|11K63|63S1|65S3)", "Kuaizhou": r"Kuaizhou-1",
    "Long March 11": r"Chang Zheng 11", "Long March 2A": r"Chang Zheng 2A?$",
    "Long March 2C": r"Chang Zheng 2C", "Long March 2D": r"Chang Zheng 2D", "Long March 2E": r"Chang Zheng 2E",
    "Long March 3A": r"Chang Zheng 3A", "Long March 3B": r"Chang Zheng 3B",
    "Long March 4B": r"Chang Zheng 4B", "Long March 5": r"Chang Zheng 5",
    "M-V": r"M-V", "Minotaur I": r"Minotaur(-| )?1|Minotaur I$", "Minotaur IV": r"Minotaur IV|Minotaur-4",
    "PSLV": r"PSLV", "Pegasus XL": r"Pegasus XL", "Pegasus": r"Pegasus$|Pegasus H",
    "Proton": r"Proton", "R-36 / Cyclone": r"Tsiklon|R-36O", "Rokot": r"Rokot",
    "Saturn V": r"Saturn V", "Scout": r"Scout", "Shavit": r"Shavit", "Shian Quxian": r"Shuang Quxian 1",
    "Shtil": r"Shtil", "Soyuz": r"Soyuz", "Space Shuttle": r"Space Shuttle", "Start": r"Start",
    "Strela": r"Strela", "Taurus": r"Taurus", "Titan II": r"Titan II (SLV|GLV)",
    "Titan III+": r"Titan (III|2\dB|3\dB|34D)", "Titan IV": r"Titan 40", "Vega": r"Vega$",
    "Zenit 2": r"Zenit-2", "Zenit 3SL": r"Zenit-3SL",
}


def launch_weighted_cost(cost):
    """그 해 실제로 쏜 발사마다 해당 로켓의 kg당 가격을 붙여 연도별 평균을 낸다."""
    d = read_tsv("launch.tsv")
    d = d[d["LaunchCode"].str[0] == "O"].copy()
    d["year"] = d["Launch_Date"].str[:4].astype(int)
    price = cost.set_index("vehicle")["usd_per_kg"]
    d["owid"] = None
    for owid_name, pattern in VEHICLE_MAP.items():  # 먼저 맞은 이름을 쓴다 (Delta 3910 → 3000-Series 순서)
        hit = d["owid"].isna() & d["LV_Type"].str.match(pattern)
        d.loc[hit, "owid"] = owid_name
    d["usd_per_kg"] = d["owid"].map(price)
    g = d.groupby("year").agg(launches=("year", "size"), priced=("usd_per_kg", "count"),
                              avg_usd_per_kg=("usd_per_kg", "mean"))
    g["coverage_pct"] = (g.priced / g.launches * 100).round(1)
    mapping = (d.dropna(subset=["owid"]).groupby(["owid", "LV_Type"]).size()
               .rename("launches").reset_index())
    return g, mapping


def cost_frontier():
    c = pd.read_csv(RAW / "owid_launch_cost.csv")
    c = c.rename(columns={"Entity": "vehicle", "Year": "year",
                          "Launch cost per kilogram of payload": "usd_per_kg",
                          "Launch vehicle class": "vehicle_class"}).sort_values("year")
    years = range(int(c.year.min()), LAST_FULL_YEAR + 1)
    record = [c[c.year <= y].usd_per_kg.min() for y in years]
    frontier = pd.DataFrame({"year": years, "record_low_usd_per_kg": record}).set_index("year")
    return c, frontier


# ---------------------------------------------------------------- 그래프 공통
def setup():
    font_manager.fontManager.addfont(str(FONT))
    plt.rcParams.update({"font.family": "NanumGothic", "font.size": 12, "axes.unicode_minus": False,
                         "axes.spines.top": False, "axes.spines.right": False,
                         "axes.edgecolor": "#B8C2C8", "axes.titlesize": 17, "axes.titleweight": "bold",
                         "axes.titlelocation": "left", "axes.grid": True, "grid.color": "#E6EBEE",
                         "grid.linewidth": .8, "savefig.dpi": 170})


def save(fig, name, note, slide_size=None):
    """보고서용(제목·출처 포함)과 슬라이드용(슬라이드에 제목·출처가 따로 있으므로 뺀 것) 두 장을 저장한다.
    slide_size를 주면 슬라이드 칸 비율에 맞게 그림 크기를 바꿔 저장한다."""
    note_text = fig.text(.01, -.03, note, fontsize=9.5, color="#60717C")
    fig.savefig(IMAGES / name, bbox_inches="tight", facecolor="white")
    note_text.remove()
    if fig._suptitle is not None:
        fig._suptitle.set_text("")
    main = fig.axes[0]._left_title  # 큰 제목은 왼쪽 정렬 제목으로 달았다
    if main.get_fontsize() >= 17:
        main.set_text("")
    if slide_size:
        fig.set_size_inches(*slide_size)
    (IMAGES / "slide").mkdir(exist_ok=True)
    fig.savefig(IMAGES / "slide" / name, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def label_end(ax, x, y, text, color, dy=0, ha="left"):
    ax.annotate(text, (x, y), xytext=(8, dy), textcoords="offset points", color=color,
                fontsize=12, fontweight="bold", va="center", ha=ha)


# ---------------------------------------------------------------- 그래프
def chart_launches(launch):
    s = launch.loc[:LAST_FULL_YEAR, "launches"]
    fig, ax = plt.subplots(figsize=(13, 5.4), layout="constrained")
    ax.plot(s.index, s.values, color=BLUE, lw=2.6)
    ax.scatter([s.index[-1]], [s.iloc[-1]], color=BLUE, zorder=3)
    label_end(ax, s.index[-1], s.iloc[-1], f"{s.iloc[-1]}회", BLUE)
    for y in (1967, 2015):
        ax.annotate(f"{y}년 {s[y]}회", (y, s[y]), xytext=(0, 18), textcoords="offset points",
                    ha="center", fontsize=11, color=DARK)
    ax.set_title("1년에 몇 번이나 우주로 쏘아 올릴까")
    ax.set_ylabel("궤도 발사 횟수 (회)")
    ax.set_xlim(1955, LAST_FULL_YEAR + 4)
    ax.set_ylim(0, s.max() * 1.15)
    save(fig, "01_launches_per_year.png", SOURCE_NOTE + " · 실패한 발사 포함", slide_size=(16, 4.6))


COST_START = 1967  # 이보다 이른 해는 가격을 붙일 수 있는 발사가 절반이 안 된다.


def chart_cost(weighted):
    w = weighted.loc[COST_START:LAST_FULL_YEAR]
    fig, ax = plt.subplots(figsize=(13, 5.6), layout="constrained")
    ax.plot(w.index, w.avg_usd_per_kg, color=ORANGE, lw=2.8)
    ax.scatter([w.index[-1]], [w.avg_usd_per_kg.iloc[-1]], color=ORANGE, zorder=3)
    label_end(ax, w.index[-1], w.avg_usd_per_kg.iloc[-1], f"${w.avg_usd_per_kg.iloc[-1]:,.0f}", ORANGE)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"${v:,.0f}"))
    ax.set_ylim(0, w.avg_usd_per_kg.max() * 1.1)
    ax.set_title("1kg을 우주로 보내는 데 드는 돈")
    ax.set_ylabel("그 해 발사 평균, 1kg당 비용")
    ax.set_xlim(COST_START - 1, LAST_FULL_YEAR + 4)
    save(fig, "02_launch_cost_per_kg.png",
         "자료: 발사 기록 GCAT(McDowell) × 로켓별 kg당 가격 Our World in Data/CSIS (2021년 달러) · "
         f"가격이 공개된 로켓의 발사만 계산 (해마다 발사의 {w.coverage_pct.min():.0f}~{w.coverage_pct.max():.0f}%), "
         "로켓별 가격은 연도와 관계없이 하나로 고정")


def chart_cost_by_vehicle(cost, frontier):
    """참고용: 로켓 기종별 가격표 (점 1개 = 기종 1종). 슬라이드에는 쓰지 않는다."""
    f = frontier.loc[:LAST_FULL_YEAR, "record_low_usd_per_kg"]
    fig, ax = plt.subplots(figsize=(13, 5.4), layout="constrained")
    ax.scatter(cost.year, cost.usd_per_kg, color=GRAY, s=28, alpha=.8, label=f"로켓 기종 1종 = 점 1개 ({len(cost)}종, 처음 성공한 해에 표시)")
    ax.step(f.index, f.values, where="post", color=ORANGE, lw=2.8, label="그 해까지의 최저 비용 기록")
    ax.set_yscale("log")
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:,.0f}"))
    for name, dx, dy in [("Space Shuttle", 8, 12), ("Saturn V", 6, -18), ("Falcon 9", -8, -20),
                         ("Falcon Heavy", 10, 0)]:
        r = cost[cost.vehicle == name].iloc[0]
        ax.annotate(f"{name}\n${r.usd_per_kg:,.0f}", (r.year, r.usd_per_kg), xytext=(dx, dy),
                    textcoords="offset points", fontsize=10, color=DARK, va="center",
                    ha="right" if dx < 0 else "left")
    ax.set_ylim(1000, 250000)
    ax.set_title("1kg을 우주로 보내는 데 드는 돈")
    ax.set_ylabel("저궤도 1kg당 비용 (달러, 로그 눈금)")
    ax.set_xlim(1960, LAST_FULL_YEAR + 2)
    ax.legend(frameon=False, loc="upper right")
    save(fig, "ref_cost_by_vehicle.png", COST_NOTE + " · 공시 가격 기준, 2019년 이후 신형 로켓 미포함")


def chart_people(people):
    p = people.loc[:LAST_FULL_YEAR]
    fig, ax = plt.subplots(figsize=(13, 5.4), layout="constrained")
    ax.plot(p.index, p.orbital, color=BLUE, lw=2.6, label="궤도 비행 (우주정거장 등)")
    ax.plot(p.index, p.suborbital, color=ORANGE, lw=2.2, label="준궤도 비행 (우주관광 등, 수 분간)")
    label_end(ax, p.index[-1], p.orbital.iloc[-1], f"{p.orbital.iloc[-1]}명", BLUE)
    label_end(ax, p.index[-1], p.suborbital.iloc[-1], f"{p.suborbital.iloc[-1]}명", ORANGE)
    ax.set_ylim(0, p.orbital.max() * 1.1)
    ax.set_title("1년에 몇 명이나 우주에 갈까")
    ax.set_ylabel("우주에 간 사람 (연인원, 명)")
    ax.set_xlim(1955, LAST_FULL_YEAR + 4)
    ax.legend(frameon=False, loc="upper left")
    save(fig, "03_people_per_year.png", SOURCE_NOTE + " · 80km 이상 도달 기준, 같은 사람이 두 번 가면 2명으로 셈",
         slide_size=(16, 4.6))


def chart_index(merged):
    """발사 횟수와 사람 수를 각자의 실제 단위로 위아래에 나눠 그린다 (지수로 겹치면 사람 수가 부풀어 보인다)."""
    m = merged.loc[BASE_YEAR:LAST_FULL_YEAR]
    fig, axes = plt.subplots(2, 1, figsize=(12, 8), sharex=True, layout="constrained")
    for ax, col, color, name, unit in [(axes[0], "launches", BLUE, "궤도 발사 횟수", "회"),
                                       (axes[1], "people", ORANGE, "우주에 간 사람 수 (궤도 + 준궤도)", "명")]:
        s = m[col]
        ax.plot(s.index, s, color=color, lw=3)
        for yr in (BASE_YEAR, LAST_FULL_YEAR):
            ax.scatter([yr], [s[yr]], color=color, s=60, zorder=3)
            ax.annotate(f"{yr}년 {s[yr]:.0f}{unit}", (yr, s[yr]), textcoords="offset points",
                        xytext=((4, 12) if col == "launches" else (4, 40)) if yr == BASE_YEAR else (0, 12),
                        ha="left" if yr == BASE_YEAR else "right", fontsize=15, color=color, weight="bold")
        ax.set_title(name, loc="left", fontsize=16, fontweight="bold", color=color)  # 17 이상이면 슬라이드용에서 지워짐
        ax.set_ylabel(unit, rotation=0, labelpad=14)
        ax.set_ylim(0, s.max() * 1.25)
        ax.tick_params(labelsize=13, labelbottom=True)
    fig.suptitle("발사가 늘어난 만큼 사람도 늘었을까", x=.01, ha="left", fontsize=17, fontweight="bold")
    axes[1].set_xlim(BASE_YEAR - .5, LAST_FULL_YEAR + .8)
    save(fig, "04_launches_vs_people_index.png", SOURCE_NOTE + " · 사람은 80km 이상 도달한 연인원")


def trend(series, start, end, to_year):
    """최근 구간의 연평균 증가율(로그 선형 회귀)을 마지막 실제 값에서부터 이어 붙인다."""
    s = series.loc[start:end]
    slope, _ = np.polyfit(s.index, np.log(s.values), 1)
    years = np.arange(end, to_year + 1)
    return pd.Series(s.iloc[-1] * np.exp(slope * (years - end)), index=years), np.exp(slope) - 1


def chart_forecast(merged):
    (start, end), to = FORECAST_YEARS, 2030
    fl, gl = trend(merged.launches, start, end, to)
    fp, gp = trend(merged.orbital, start, end, to)
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.2), layout="constrained")
    for ax, col, f, g, color, title, unit in [
        (axes[0], "launches", fl, gl, BLUE, "궤도 발사 횟수", "회"),
        (axes[1], "orbital", fp, gp, ORANGE, "궤도에 간 사람", "명")]:
        s = merged.loc[2005:end, col]
        ax.plot(s.index, s, color=color, lw=2.6)
        ax.plot(f.index, f.values, color=color, lw=2.2, ls="--")
        ax.axvspan(end, to + .5, color="#F2F4F5", zorder=0)
        ax.text(end + .3, ax.get_ylim()[1] * .02, "추세 연장", fontsize=10, color="#60717C")
        label_end(ax, to, f.iloc[-1], f"{f.iloc[-1]:,.0f}{unit}?", color, ha="right", dy=16)
        ax.set_title(f"{title}  ({start}~{end}년 연평균 {g * 100:+.0f}%)", fontsize=14)
        ax.set_xlim(2005, to + 1)
        ax.set_ylim(0, None)
    fig.suptitle("이 속도가 이어진다면 2030년에는?", x=.01, ha="left", fontsize=17, fontweight="bold")
    save(fig, "05_forecast_2030.png",
         SOURCE_NOTE + f" · {start}~{end}년 증가율을 그대로 연장한 단순 추세 (예측 모델 아님)",
         slide_size=(10.5, 7))
    return {"launches_2030": round(fl.iloc[-1]), "launch_growth": round(gl, 3),
            "people_2030": round(fp.iloc[-1]), "people_growth": round(gp, 3)}


# ---------------------------------------------------------------- 실행
def main():
    OUT.mkdir(parents=True, exist_ok=True)
    IMAGES.mkdir(exist_ok=True)
    setup()
    launch, last_launch = launches_by_year()
    people, joined, rides = people_by_year()
    cost, frontier = cost_frontier()

    merged = launch.join(people, how="left").fillna(0).astype(int)
    merged = merged.rename(columns={"total": "people"})
    merged["crewed_share_pct"] = (merged.crewed_orbital_launches / merged.launches * 100).round(1)
    merged.to_csv(OUT / "space_annual.csv", encoding="utf-8-sig")
    cost.to_csv(OUT / "launch_cost_by_vehicle.csv", index=False, encoding="utf-8-sig")
    frontier.to_csv(OUT / "launch_cost_record_low.csv", encoding="utf-8-sig")
    weighted, mapping = launch_weighted_cost(cost)
    weighted.round(1).to_csv(OUT / "launch_cost_weighted_annual.csv", encoding="utf-8-sig")
    mapping.to_csv(OUT / "vehicle_name_mapping.csv", index=False, encoding="utf-8-sig")

    chart_launches(launch)
    chart_cost(weighted)
    chart_cost_by_vehicle(cost, frontier)
    chart_people(people)
    chart_index(merged)
    forecast = chart_forecast(merged)

    base = merged.loc[BASE_YEAR]
    y = merged.loc[LAST_FULL_YEAR]
    summary = {
        "last_launch_in_data": last_launch,
        "rides_matched": f"{joined}/{rides}",
        "base_year": BASE_YEAR,
        "base": base[["launches", "people", "crewed_orbital_launches"]].to_dict(),
        str(LAST_FULL_YEAR): y[["launches", "spacex", "without_spacex", "people", "orbital", "suborbital",
                                "crewed_orbital_launches", "new_people", "crewed_share_pct"]].to_dict(),
        "launch_ratio_vs_base": round(y.launches / base.launches, 2),
        "people_ratio_vs_base": round(y.people / base.people, 2),
        "forecast": forecast,
        "weighted_cost": {
            "base": round(weighted.loc[BASE_YEAR].avg_usd_per_kg),
            str(LAST_FULL_YEAR): round(weighted.loc[LAST_FULL_YEAR].avg_usd_per_kg),
            f"coverage_{LAST_FULL_YEAR}_pct": weighted.loc[LAST_FULL_YEAR].coverage_pct,
            f"min_coverage_since_{COST_START}_pct": weighted.loc[COST_START:LAST_FULL_YEAR].coverage_pct.min(),
        },
    }
    (OUT / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2, default=int), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2, default=int))

    # 발표 정리용 요약 (예전 '그래서, 우주시대는 열렸을까' 슬라이드 내용)
    wc = summary["weighted_cost"]
    print(f"\n[정리] {BASE_YEAR}년 → {LAST_FULL_YEAR}년")
    print(f"  발사 횟수   {base.launches:.0f}회 → {y.launches:.0f}회 ({summary['launch_ratio_vs_base']:.1f}배): 늘었다")
    print(f"  1kg당 비용  약 ${wc['base']:,} → 약 ${wc[str(LAST_FULL_YEAR)]:,} "
          f"({wc[str(LAST_FULL_YEAR)] / wc['base'] * 100:.0f}% 수준): 싸졌다")
    print(f"  우주에 간 사람 {base.people:.0f}명 → {y.people:.0f}명 ({summary['people_ratio_vs_base']:.1f}배): "
          f"늘었지만 {y.suborbital / y.people * 100:.0f}%는 몇 분짜리 준궤도 관광")
    print("  결론: 우주로 가는 길은 넓어졌지만, 그 길을 주로 쓰는 건 아직 사람이 아니라 기계다.")


if __name__ == "__main__":
    main()
