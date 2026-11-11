"""사용자가 직접 손본 발표자료 위에 필요한 부분만 고쳐 새 버전으로 저장한다.

build_slides.py는 v5에서 처음부터 다시 만들기 때문에, 사용자가 PowerPoint에서 고친 내용을 잃는다.
v8부터는 사용자가 저장한 파일이 기준이므로 이 스크립트처럼 '필요한 슬라이드만' 고친다.

실행: python patch_deck.py   (SRC를 읽어 DST로 저장, SRC는 건드리지 않음)
"""
from pathlib import Path

from pptx import Presentation
from pptx.util import Emu
from PIL import Image

ROOT = Path(__file__).resolve().parent
from paths import DECK
SRC = DECK / "2시간데이터분석맛보기_v8.pptx"   # 사용자가 저장한 최신본
DST = DECK / "2시간데이터분석맛보기_v10.pptx"


def find_slide(prs, title):
    for s in prs.slides:
        if any(sh.has_text_frame and sh.text_frame.text.strip() == title for sh in s.shapes):
            return s
    raise LookupError(f"제목이 '{title}'인 슬라이드가 없습니다")


def shape(slide, name):
    return next(s for s in slide.shapes if s.name == name)


def set_paras(shp, *texts):
    """문단 수는 그대로 두고, 각 문단 첫 run의 서식을 살려 글자만 바꾼다."""
    paras = shp.text_frame.paragraphs
    assert len(paras) == len(texts), f"{shp.name}: 문단 {len(paras)}개, 바꿀 글 {len(texts)}개"
    for p, text in zip(paras, texts):
        p.runs[0].text = text
        for r in p.runs[1:]:
            r._r.getparent().remove(r._r)


def swap_picture(slide, box_name, image, pad=.02):
    """box 안에 있는 그림을 지우고 새 그림을 비율 그대로 가운데에 넣는다."""
    box = shape(slide, box_name)
    for pic in [s for s in slide.shapes if s.shape_type == 13]:
        cx, cy = pic.left + pic.width // 2, pic.top + pic.height // 2
        if box.left <= cx <= box.left + box.width and box.top <= cy <= box.top + box.height:
            pic._element.getparent().remove(pic._element)
    w, h = Image.open(image).size
    scale = min(box.width * (1 - 2 * pad) / w, box.height * (1 - 2 * pad) / h)
    pw, ph = int(w * scale), int(h * scale)
    slide.shapes.add_picture(str(image), Emu(box.left + (box.width - pw) // 2),
                             Emu(box.top + (box.height - ph) // 2), Emu(pw), Emu(ph))


def main():
    prs = Presentation(SRC)

    # 20번: 키워드를 '2017년부터 가을 모기 기승'으로 (설명 글과 그래프는 사용자가 고친 그대로)
    s = find_slide(prs, "많이 관측되는 시기는 달라졌을까")
    set_paras(shape(s, "Text 5"), "2017년부터")
    set_paras(shape(s, "Text 6"), "가을 모기", "기승")

    # 26번: 지수 그래프 → 발사 횟수·사람 수를 실제 단위로 위아래에 나눈 그래프
    s = find_slide(prs, "발사가 늘어난 만큼 사람도 늘었을까")
    swap_picture(s, "Shape 3", ROOT / "images/slide/04_launches_vs_people_index.png")
    src = shape(s, "Text 7")
    set_paras(src, src.text_frame.text.replace("2000년 = 100, 사람은 궤도+준궤도 연인원",
                                               "사람은 80km 이상 도달한 궤도+준궤도 연인원"))

    prs.save(DST)
    print("저장:", DST)


if __name__ == "__main__":
    main()
