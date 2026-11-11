# mosquito

분석 내용은 [report.md](report.md)에 있다. 현재 배포본은 **업데이트 2: 모기 관측량과 날씨의 관계 분석**이다.

## 먼저 결과 보기

VS Code에서 `report.md`를 열고 `Ctrl + Shift + V`를 누르면 그래프와 본문을 볼 수 있다. 결과 이미지와 CSV를 포함했으므로 보기만 할 때는 Python 실행이 필요 없다.

## 설치와 실행

Python 3.11 이상을 사용한다. VS Code 터미널에서 프로젝트 폴더를 연 뒤 실행한다.

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe analysis.py
```

macOS/Linux에서는 다음과 같이 실행한다.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python analysis.py
```

`analysis.py`는 모기 원본 엑셀과 기상청 ASOS 일자료에서 정제 CSV·검사 기록·그래프 6개를 다시 만든다. `report.md`의 해석 문장은 덮어쓰지 않는다. 원본이 바뀌면 수치와 해석을 검토하여 보고서도 함께 수정해야 한다.

## 파일

| 파일/폴더 | 내용 |
|---|---|
| analysis.py | 정제, 집계, 시각화 |
| collect_data.py | 포함된 원본이 없을 때 공식 파일 재수집 |
| collect_weather.py | `.env` 인증키로 기상청 서울 일자료 재수집 |
| run_weather.bat | Windows용 기상자료 수집 실행 파일 |
| data/raw/ | 공식 원본과 출처 기록 |
| data/processed/ | 모기·기상 정제자료, 월별 결합자료와 상관 계산 결과 |
| images/ | 보고서에 포함한 그래프 6개 |
| assets/ | 한글 그래프용 나눔고딕과 OFL 라이선스 |

두 원본을 이미 포함했으므로 일반 실행에는 인터넷이 필요 없다(최초 라이브러리 설치 제외). 재수집할 때만 `collect_data.py` 또는 `collect_weather.py`를 실행한다. 기상청 인증키는 `.env`에 `KMA_AUTH_KEY=...` 형식으로 저장하며 Git에 포함하지 않는다.

## 업데이트 적용

다운로드한 ZIP을 임시 폴더에 풀고, 그 안의 내용을 기존 `mosquito` 폴더에 복사한다. 같은 이름의 파일은 교체한다. 기존 Git 연결 폴더는 유지된다. 개인적으로 수정한 파일은 교체 전 사본을 남긴다.

## 출처와 이용 조건

서울특별시 보건환경연구원, [서울시 감염병매개 모기 개체수 및 종별 분류 결과](https://data.seoul.go.kr/dataList/OA-22301/F/1/datasetView.do), 공공누리 제1유형(출처표시). 기상자료는 [기상청 API허브 종관기상관측(ASOS)](https://apihub.kma.go.kr/apiList.do?seqApi=2)의 서울(108) 일자료다. 출처와 재수집 방법은 `data/raw/sources.json`에 기록했다.

한글 글꼴은 Google Fonts에서 배포하는 Nanum Gothic이다. 재배포 조건은 `assets/OFL.txt`를 참고한다.

## 추가 작업: 발표자료와 우주 발사 분석

### 모기 분석 추가 그래프 (`analysis.py`)

| 파일 | 내용 |
|---|---|
| images/07_mosquito_rainfall_timeline.png | 같은 달의 모기 관측량과 강수량 |
| images/08_dataset_overview.png | 원본 엑셀 일부와 연도·월별 기록 유무 (4~11월만 채집) |
| images/09_mosquito_temperature_spans.png | 기온과 같이/따로 움직인 구간 표시 |
| images/10_mosquito_rainfall_spans.png | 강수량과 같이/따로 움직인 구간 표시 |
| images/11_peak_shift.png | 해마다 가장 많았던 달, 가을÷여름 비율 |

### 우주 발사 분석 (`space/`)

"발사가 늘고 비용이 줄었다면, 사람도 우주에 많이 가고 있을까?"를 확인한다.

```
cd space
python collect_data.py    # 원자료 다시 받기 (data/raw 에 이미 포함, 선택)
python analysis.py        # 집계표와 그래프 생성, 끝에 발표용 요약 출력
```

- 발사·유인비행: Jonathan McDowell, GCAT 발사 목록과 유인비행 목록 (planet4589.org, 2026.11.9 갱신)
- 발사 비용: Our World in Data / CSIS Aerospace Security Project, 로켓별 저궤도 1kg당 비용 (2021년 달러)
- 출처와 받은 시각은 `space/data/raw/sources.json`에 기록했다.

### 발표자료 (`slides/`)

- `2시간데이터분석맛보기_v5.pptx` ~ `v10.pptx`: 버전별 발표자료. 최신은 v10
- `발표대본_v10.md`: v10 기준 페이지별 발표 대본과 데이터 출처
- `space/build_slides.py`(v5에서 새로 만들기), `space/patch_deck.py`(직접 고친 파일 위에 일부만 수정)로 슬라이드를 만들었다.
