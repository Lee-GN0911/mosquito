# mosquito

분석 내용은 [report.md](report.md)에 있다. 현재 배포본은 **업데이트 1: 모기 관측량 분석**이다. 기상 자료와의 관계 분석은 포함되지 않는다.

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

`analysis.py`는 원본 엑셀에서 CSV 4개·검사 기록·그래프 3개를 다시 만든다. `report.md`의 해석 문장은 덮어쓰지 않는다. 원본이 바뀌면 수치와 해석을 검토하여 보고서도 함께 수정해야 한다.

## 파일

| 파일/폴더 | 내용 |
|---|---|
| analysis.py | 정제, 집계, 시각화 |
| collect_data.py | 포함된 원본이 없을 때 공식 파일 재수집 |
| data/raw/ | 공식 원본과 출처 기록 |
| data/processed/ | 원본 전체 주차·5~10월 주차·월별·연도별 CSV와 정제 검사 |
| images/ | 보고서에 포함한 그래프 3개 |
| assets/ | 한글 그래프용 나눔고딕과 OFL 라이선스 |

원본 엑셀을 이미 포함했으므로 일반 실행에는 인터넷이 필요 없다(최초 라이브러리 설치 제외). 원본 파일을 잃어버렸을 때만 `collect_data.py`를 실행한다. 제공 사이트 연결 실패 또는 파일 변경 시 오류를 알리고 중단한다.

## 업데이트 적용

다운로드한 ZIP을 임시 폴더에 풀고, 그 안의 내용을 기존 `mosquito` 폴더에 복사한다. 같은 이름의 파일은 교체한다. 기존 Git 연결 폴더는 유지된다. 개인적으로 수정한 파일은 교체 전 사본을 남긴다.

## 출처와 이용 조건

서울특별시 보건환경연구원, [서울시 감염병매개 모기 개체수 및 종별 분류 결과](https://data.seoul.go.kr/dataList/OA-22301/F/1/datasetView.do), 공공누리 제1유형(출처표시). 원본과 재수집 요청 정보·SHA256은 `data/raw/sources.json`에 기록했다.

한글 글꼴은 Google Fonts에서 배포하는 Nanum Gothic이다. 재배포 조건은 `assets/OFL.txt`를 참고한다.
