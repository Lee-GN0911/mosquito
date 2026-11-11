"""폴더 위치를 한곳에서 정한다. 두 가지 배치를 모두 지원한다.

- GitHub 저장소: 모기 분석 코드가 이 폴더의 상위(저장소 루트)에, 발표자료는 루트의 slides/ 에 있다.
- 처음 작업한 PC 폴더: 모기 분석 코드가 ../mosquito-main/ 에, 발표자료는 상위 폴더에 바로 있다.
"""
from pathlib import Path

SPACE = Path(__file__).resolve().parent
MOSQ = SPACE.parent if (SPACE.parent / "analysis.py").exists() else SPACE.parent / "mosquito-main"
DECK = SPACE.parent / "slides" if (SPACE.parent / "slides").is_dir() else SPACE.parent
FONT = MOSQ / "assets/NanumGothic-Regular.ttf"
