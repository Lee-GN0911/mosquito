"""v5 발표자료에서 주식 예시(20~26번)를 우주 예시로 바꾸고, 모기 예시(데이터셋·강수량 추가, 기온 추이 삭제)를 손봐 v9로 저장한다.

실행: python build_slides.py   (analysis.py, slide_images.py 다음에 실행)
v5 원본은 건드리지 않는다. 기존 슬라이드의 도형을 복제해 같은 서식을 유지한다.
"""
from pathlib import Path
from copy import deepcopy
import json

from pptx import Presentation
from pptx.util import Emu, Pt
from pptx.dml.color import RGBColor
from pptx.opc.constants import RELATIONSHIP_TYPE as RT
from PIL import Image

ROOT = Path(__file__).resolve().parent
from paths import DECK, MOSQ
SRC = DECK / "2시간데이터분석맛보기_v5.pptx"
DST = DECK / "2시간데이터분석맛보기_v9.pptx"
IMG = ROOT / "images/slide"
S = json.loads((ROOT / "data/processed/summary.json").read_text(encoding="utf-8"))
S["2025"] = {k: (int(v) if float(v).is_integer() else v) for k, v in S["2025"].items()}

STOCK = range(20, 27)  # v5의 주식 슬라이드 번호(1부터)
T_SECTION, T_DATA, T_FULL, T_SIDE, T_BIG = 20, 15, 21, 22, 26  # 서식을 빌려올 v5 슬라이드
SRC_GCAT = "GCAT 발사 목록·유인비행 목록(Jonathan McDowell, planet4589.org, 2026.11.9 갱신)"
SRC_COST = "GCAT 발사 목록 × 로켓별 kg당 가격(Our World in Data / CSIS, 2021년 달러)"
BY = " · 분석: space/analysis.py"


# ---------------------------------------------------------------- 도형 다루기
def duplicate(prs, src):
    """같은 레이아웃으로 새 슬라이드를 만들고 src의 도형과 그림 연결을 복사한다."""
    new = prs.slides.add_slide(src.slide_layout)
    for shp in list(new.shapes):
        shp._element.getparent().remove(shp._element)
    for el in src.shapes._spTree.iterchildren():
        if el.tag.split("}")[1] in ("sp", "pic", "grpSp", "cxnSp", "graphicFrame"):
            new.shapes._spTree.append(deepcopy(el))
    for pic in new.shapes._spTree.iter("{http://schemas.openxmlformats.org/drawingml/2006/main}blip"):
        key = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed"
        part = src.part.related_part(pic.get(key))
        pic.set(key, new.part.relate_to(part, RT.IMAGE))
    return new


def shape(slide, name):
    return next(s for s in slide.shapes if s.name == name)


def set_text(shp, *paras):
    """첫 run의 서식을 살려 문단별 글자만 바꾼다. 문단 수가 다르면 마지막 문단을 복제/삭제한다."""
    tf = shp.text_frame
    ps = tf.paragraphs
    while len(tf.paragraphs) < len(paras):
        tf._txBody.append(deepcopy(tf.paragraphs[-1]._p))
    for p in list(tf.paragraphs)[len(paras):]:
        p._p.getparent().remove(p._p)
    for p, text in zip(tf.paragraphs, paras):
        runs = p.runs
        runs[0].text = text
        for r in runs[1:]:
            r._r.getparent().remove(r._r)


def replace_picture(slide, old_name, image, box_name, pad=0.03):
    """그림을 지우고, box 도형 안에 비율을 지켜 가운데 맞춰 새 그림을 넣는다."""
    old = shape(slide, old_name)
    old._element.getparent().remove(old._element)
    box = shape(slide, box_name)
    w, h = Image.open(image).size
    bw, bh = box.width * (1 - 2 * pad), box.height * (1 - 2 * pad)
    scale = min(bw / w, bh / h)
    pw, ph = int(w * scale), int(h * scale)
    left = box.left + (box.width - pw) // 2
    top = box.top + (box.height - ph) // 2
    return slide.shapes.add_picture(str(image), Emu(left), Emu(top), Emu(pw), Emu(ph))


def remove(slide, *names):
    for n in names:
        el = shape(slide, n)._element
        el.getparent().remove(el)


def move_to(prs, slide, position):
    """slide를 position(0부터) 위치로 옮긴다."""
    lst = prs.slides._sldIdLst
    el = next(e for e in lst if prs.slides.get(int(e.get("id"))) is slide)
    lst.remove(el)
    lst.insert(position, el)


def delete(prs, slide):
    lst = prs.slides._sldIdLst
    el = next(e for e in lst if prs.slides.get(int(e.get("id"))) is slide)
    prs.part.drop_rel(el.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"))
    lst.remove(el)


# ---------------------------------------------------------------- 슬라이드별 내용
def section(prs, t):
    s = duplicate(prs, t)
    set_text(shape(s, "Text 1"), "우주시대,", "우리도 화성", "갈 수 있을까?")
    old = shape(s, "Image 0")
    s.shapes.add_picture(str(IMG / "hero_launches.png"), old.left, old.top, old.width, old.height)
    old._element.getparent().remove(old._element)
    set_text(shape(s, "Text 2"), "자료: GCAT 발사 목록(Jonathan McDowell) · 2025년 궤도 발사, 실패 포함")
    return s


def data_cards(prs, t, title, left_img, left_label, right_img, right_label):
    s = duplicate(prs, t)
    set_text(shape(s, "Text 0"), "07   예시자료")
    s.shapes[1].text_frame.paragraphs[0].runs[0].text = title  # 두 번째 Text 0 = 제목
    replace_picture(s, "Image 0", left_img, "Shape 3")
    replace_picture(s, "Image 1", right_img, "Shape 6")
    set_text(shape(s, "Text 4"), left_label)
    set_text(shape(s, "Text 7"), right_label)
    return s


def full(prs, t, title, image, message, source):
    s = duplicate(prs, t)
    s.shapes[1].text_frame.paragraphs[0].runs[0].text = title
    replace_picture(s, "Image 0", image, "Shape 3", pad=.02)
    set_text(shape(s, "Text 5"), message)
    set_text(shape(s, "Text 6"), source)
    return s


def side(prs, t, title, image, insight, source, size=None):
    s = duplicate(prs, t)
    s.shapes[1].text_frame.paragraphs[0].runs[0].text = title
    replace_picture(s, "Image 0", image, "Shape 3", pad=.02)
    set_text(shape(s, "Text 6"), *insight)
    if size:  # 문장이 길면 글자를 줄여 패널 안에 넣는다
        for p in shape(s, "Text 6").text_frame.paragraphs:
            p.runs[0].font.size = Pt(size)
    set_text(shape(s, "Text 7"), source)
    return s


def big(prs, t, title, image, tag, line1, line2, note, source):
    s = duplicate(prs, t)
    s.shapes[1].text_frame.paragraphs[0].runs[0].text = title
    replace_picture(s, "Image 0", image, "Shape 3", pad=.02)
    set_text(shape(s, "Text 5"), tag)
    set_text(shape(s, "Text 6"), line1, line2)
    set_text(shape(s, "Text 8"), *([note] if isinstance(note, str) else note))
    set_text(shape(s, "Text 9"), source)
    return s


def summary(prs, t_side, t_full, title, cards, message):
    """인사이트 패널(남색 카드) 3장 + 아래 결론 띠."""
    s = duplicate(prs, t_side)
    s.shapes[1].text_frame.paragraphs[0].runs[0].text = title
    remove(s, "Shape 2", "Shape 3", "Image 0", "Text 7")
    panel, label, body = shape(s, "Shape 4"), shape(s, "Text 5"), shape(s, "Text 6")
    left0, gap = 548640, 274320
    width = (11094415 - 2 * gap) // 3
    top, height = 1691640, 3337560
    inset = label.left - panel.left
    for i, (lab, lines) in enumerate(cards):
        if i == 0:
            p, l, b = panel, label, body
        else:
            p, l, b = (deepcopy(x._element) for x in (panel, label, body))
            for el in (p, l, b):
                s.shapes._spTree.append(el)
            p, l, b = s.shapes[-3], s.shapes[-2], s.shapes[-1]
        x = left0 + i * (width + gap)
        p.left, p.top, p.width, p.height = x, top, width, height
        l.left, l.top, l.width = x + inset, top + 320040, width - 2 * inset
        b.left, b.top, b.width, b.height = x + inset, top + 777240, width - 2 * inset, height - 1005840
        set_text(l, lab)
        set_text(b, *lines)
        stat, desc = b.text_frame.paragraphs[0].runs[0].font, b.text_frame.paragraphs[1].runs[0].font
        stat.size, stat.color.rgb = Pt(60), RGBColor(0xF0, 0x8A, 0x3C)
        desc.size = Pt(22)
    full_t = t_full
    for name in ("Shape 4", "Text 5"):
        el = deepcopy(shape(full_t, name)._element)
        s.shapes._spTree.append(el)
    set_text(s.shapes[-1], message)
    return s


def main():
    prs = Presentation(SRC)
    slides = list(prs.slides)
    t = {k: slides[k - 1] for k in (T_SECTION, T_DATA, T_FULL, T_SIDE, T_BIG)}
    y = S["2025"]
    base = S["base"]
    by = S["base_year"]
    wc = S["weighted_cost"]
    fc = S["forecast"]

    # ---- 모기 예시: 데이터셋 소개 추가, 기온 추이(17번) 삭제, 강수량 비교 추가
    mosq = MOSQ / "images"
    dataset = full(prs, slides[16 - 1], "먼저, 데이터를 열어보자", mosq / "08_dataset_overview.png",
                   "1년 내내가 아니라 4~11월에만 채집했다. 그래프의 빈 구간은 '모기 0마리'가 아니라 '기록 없음'이다.",
                   "서울 모기 관측자료(2008~2023) · 서울특별시 보건환경연구원 · 분석은 해마다 기록이 있는 5~10월만 사용")
    src_m = "서울 모기 관측자료(2008~2023) · 서울특별시 보건환경연구원 / 기상청"
    temp = side(prs, slides[18 - 1], "기온이 오르면 모기는 줄어들까", mosq / "09_mosquito_temperature_spans.png",
                ["2008~2010년엔 기온과", "모기가 같이 오르내렸다.",
                 "2019~2021년엔 10월", "기온이 6도 넘게 떨어져도", "모기는 늘었다.",
                 "", "기온만 보고 모기가", "늘지 줄지 알 수 없다."], src_m, size=16)
    rain = side(prs, slides[18 - 1], "비가 많이 오면 모기는 늘어날까", mosq / "10_mosquito_rainfall_spans.png",
                ["2008~2009년엔 비가", "가장 많은 7월에", "모기도 가장 많았다.",
                 "2020~2022년엔 비가", "가장 많은 8월에", "모기는 오히려 줄었다.",
                 "", "같은 달끼리 비교하면", "비와 모기는 거의 무관하다."], src_m, size=16)
    peak = big(prs, t[T_BIG], "많이 관측되는 시기는 달라졌을까", mosq / "03_monthly_counts.png", "2017년부터",
               "가을 모기", "기승",
               ["2016년까지 여름 모기가 기승을 부리고,", "2017년부터 가을 모기가 기승을 부린다."],
               "서울 모기 관측자료(2008~2023) · 서울특별시 보건환경연구원 · 가을 9~10월, 여름 6~8월 월평균")

    # ---- 우주 예시 (모든 배수는 기준 연도(2000년)와 2025년을 비교)
    b_l, b_p = base["launches"], base["people"]
    new = [
        section(prs, t[T_SECTION]),
        data_cards(prs, t[T_DATA], "사용 데이터", IMG / "src_gcat.png", "GCAT 발사·유인비행 목록",
                   IMG / "src_owid.png", "Our World in Data 발사 비용"),
        full(prs, t[T_FULL], "1년에 몇 번이나 우주로 쏘아 올릴까", IMG / "01_launches_per_year.png",
             f"50년 가까이 연 100회 안팎이던 발사가 2025년 {y['launches']}회로. 절반({y['spacex']}회)은 스페이스X 한 회사다.",
             SRC_GCAT + " · 궤도 발사, 실패 포함" + BY),
        side(prs, t[T_SIDE], "1kg을 우주로 보내는 데 드는 돈", IMG / "02_launch_cost_per_kg.png",
             ["40년 넘게 1kg당", "약 2만 달러로 제자리.", "",
              f"{by}년 약 {round(wc['base'], -2):,}달러", f"→ 2025년 약 {round(wc['2025'], -2):,}달러",
              f"{by}년의 {wc['2025'] / wc['base'] * 100:.0f}% 수준."],
             SRC_COST + f" · 가격이 공개된 로켓의 발사만 (2025년은 {wc['coverage_2025_pct']:.0f}%)" + BY, size=18),
        full(prs, t[T_FULL], "그럼 사람은 몇 명이나 갔을까", IMG / "03_people_per_year.png",
             f"2025년 우주에 간 {y['people']}명 중 {y['suborbital']}명은 몇 분짜리 준궤도 관광. 궤도에 간 사람은 {y['orbital']}명뿐이다.",
             SRC_GCAT + " · 80km 이상 도달, 연인원" + BY),
        side(prs, t[T_SIDE], "발사가 늘어난 만큼 사람도 늘었을까", IMG / "04_launches_vs_people_index.png",
             [f"{by}년 → 2025년",
              f"발사 {b_l:.0f}회 → {y['launches']}회 ({S['launch_ratio_vs_base']:.1f}배)",
              f"사람 {b_p:.0f}명 → {y['people']}명 ({S['people_ratio_vs_base']:.1f}배)",
              "", f"2025년 궤도 발사 {y['launches']}회 중", f"사람이 탄 건 {y['crewed_orbital_launches']}회뿐."],
             SRC_GCAT + " · 사람은 80km 이상 도달한 궤도+준궤도 연인원" + BY, size=18),
        big(prs, t[T_BIG], "이 속도라면 2030년에는?", IMG / "05_forecast_2030.png", "2030년 추세",
            f"발사 {round(fc['launches_2030'], -1):,}회", f"사람 {fc['people_2030']}명",
            "최근 5년 증가율을 그대로 늘린 단순 계산이다. 사람은 궤도 비행 기준.",
            SRC_GCAT + " · 2021~2025년 증가율 연장, 예측 모델 아님" + BY),
    ]

    # ---- 순서 정리: 1~15, 데이터셋, 16, 기온, 강수량, 정점 시기, 우주 슬라이드, 마지막(INSIGHT)
    # 요약 정리는 슬라이드 대신 space/analysis.py 실행 결과 끝에 출력된다.
    order = slides[:15] + [dataset, slides[15], temp, rain, peak] + new + slides[26:]
    for old in [slides[i - 1] for i in list(STOCK) + [17, 18, 19]]:
        delete(prs, old)
    for i, s in enumerate(order):
        move_to(prs, s, i)
    prs.save(DST)
    print("저장:", DST, "· 슬라이드", len(prs.slides), "장")


if __name__ == "__main__":
    main()
