"""슬라이드용 보조 이미지(표지 숫자, 궤도/준궤도 그림, 출처 사이트 화면)를 만든다.

실행: python slide_images.py   (analysis.py 다음에 실행)
"""
from pathlib import Path
import json

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import Circle, FancyArrowPatch
from PIL import Image

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "images/slide"
ASSETS = ROOT / "assets"
from paths import FONT
NAVY, ORANGE, SLATE, BLUE, PALE = "#0F2B3D", "#F08A3C", "#7FA7B8", "#26718C", "#EEF3F6"


def setup():
    font_manager.fontManager.addfont(str(FONT))
    plt.rcParams.update({"font.family": "NanumGothic", "axes.unicode_minus": False, "savefig.dpi": 200})


def hero():
    """표지 오른쪽 그림: 2025년 발사 횟수와 작은 추세선."""
    annual = pd.read_csv(ROOT / "data/processed/space_annual.csv", index_col=0).loc[:2025]
    n = int(annual.loc[2025, "launches"])
    hours = 365 * 24 / n
    fig = plt.figure(figsize=(9.07, 6.0), facecolor="white")
    fig.text(.07, .84, "2025년, 로켓이 우주로 날아간 횟수", fontsize=22, color=NAVY)
    fig.text(.07, .50, f"{n}", fontsize=120, color=ORANGE, fontweight="bold")
    fig.text(.07 + .115 * len(str(n)), .53, "회", fontsize=44, color=ORANGE, fontweight="bold")
    fig.text(.07, .41, f"약 {hours:.0f}시간에 한 번꼴", fontsize=24, color=NAVY)
    ax = fig.add_axes([.07, .07, .86, .26])
    ax.fill_between(annual.index, annual.launches, color=PALE)
    ax.plot(annual.index, annual.launches, color=BLUE, lw=2.4)
    ax.scatter([2025], [n], color=ORANGE, s=40, zorder=3)
    ax.text(1957, annual.launches.max() * .9, "1957", fontsize=12, color="#60717C")
    ax.text(2025, n * 1.08, "2025", fontsize=12, color="#60717C", ha="right")
    ax.axis("off")
    fig.savefig(OUT / "hero_launches.png", facecolor="white")
    plt.close(fig)


def orbit_diagrams():
    """궤도 비행 vs 준궤도 비행 개념도. 크기는 이해를 위해 과장했다."""
    for kind in ("orbital", "suborbital"):
        fig, ax = plt.subplots(figsize=(8, 5.2), facecolor="white")
        ax.set_aspect("equal")
        ax.axis("off")
        earth_r = 1.0
        ax.add_patch(Circle((0, -0.35), earth_r, color=BLUE, alpha=.9, zorder=2))
        ax.add_patch(Circle((0, -0.35), earth_r + .08, color=BLUE, alpha=.15, zorder=1))
        if kind == "orbital":
            ax.add_patch(Circle((0, -0.35), earth_r + .42, fill=False, color=ORANGE, lw=3, ls="-", zorder=3))
            ax.add_patch(FancyArrowPatch((-.25, 1.05), (-.55, .96), arrowstyle="-|>", mutation_scale=28,
                                         color=ORANGE, lw=0, zorder=4))
            rows = [("속도", "초속 약 7.8km (90분에 지구 한 바퀴)"), ("높이", "약 400km (국제우주정거장)"),
                    ("머무는 시간", "며칠 ~ 몇 달")]
        else:
            t = np.linspace(0, 1, 100)
            x = -.4 + .8 * t
            surface = -.35 + np.sqrt(earth_r ** 2 - x ** 2)
            y = surface + .02 + .3 * 4 * t * (1 - t)  # 궤도 고리(지표 위 .42)보다 낮게
            ax.add_patch(Circle((0, -0.35), earth_r + .42, fill=False, color="#C9D3D9", lw=1.5, ls="--"))
            ax.text(1.02, .98, "궤도 높이", fontsize=13, color="#9BA7B0")
            ax.plot(x, y, color=ORANGE, lw=3, zorder=3)
            ax.add_patch(FancyArrowPatch((x[-6], y[-6]), (x[-1], y[-1]), arrowstyle="-|>", mutation_scale=28,
                                         color=ORANGE, lw=0, zorder=4))
            rows = [("속도", "궤도 속도에 한참 못 미침"), ("높이", "약 100km 안팎"),
                    ("머무는 시간", "몇 분")]
        ax.set_xlim(-1.7, 1.7)
        ax.set_ylim(-.15, 1.25)
        for i, (k, v) in enumerate(rows):
            fig.text(.06, .30 - i * .1, k, fontsize=17, color=SLATE, fontweight="bold")
            fig.text(.30, .30 - i * .1, v, fontsize=17, color=NAVY)
        ax.set_position([0, .36, 1, .64])
        fig.savefig(OUT / f"diagram_{kind}.png", facecolor="white")
        plt.close(fig)


def source_shots():
    """출처 사이트 화면(headless Edge 캡처)에서 쿠키 배너 등을 잘라낸다."""
    for name, box in [("src_gcat", (0, 0, 1400, 860)), ("src_owid", (60, 95, 1340, 785))]:
        Image.open(ASSETS / f"{name}.png").crop(box).save(OUT / f"{name}.png")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    setup()
    hero()
    orbit_diagrams()
    source_shots()
    print("완료:", OUT)


if __name__ == "__main__":
    main()
