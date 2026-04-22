#  Radar-based Patient Biosignal Analysis

레이더 기반 환자 생체신호(Heart Rate, Respiratory Rate)와 재실 상태를 분석하고,  
전처리 및 탐색적 데이터 분석(EDA) 파이프라인을 구축한 프로젝트입니다.

사내 스키마  
(timestamp, device_id, data_category, min_value, avg_value, max_value)를 반영한  
생체신호 데이터를 활용하여 분석부터 시각화, 배포까지 전체 흐름을 검증했습니다.

---

##  Project Objective

- 재실/부재 상태를 구분할 수 있는 전처리 절차 정립
- Heart / Breath의 시간대별 패턴 및 분포 분석
- 낙상(Drop) 이벤트 전후 생체신호 변화 탐색
- 향후 이상 탐지 및 위험도 분류 모델을 위한 feature 후보 정의

---

##  Project Structure


datamining_midterm_project
├── data/
biosignal_raw_long_simulated.csv # 원본 데이터 (long format)
biosignal_wide_before_cleaning.csv # pivot 변환 데이터
biosignal_processed_wide.csv # 전처리 완료 데이터
analysis_summary.json # 최종 결과 요약
preprocessing_summary.csv # 전처리 요약
descriptive_statistics.csv # 통계 정보
raw_sample_20rows.csv # 샘플 데이터
data_dictionary.csv # 컬럼 설명

├── figures/ # 시각화 결과
fig_01_preprocessing_funnel.png
fig_02_status_distribution.png
fig_03_timeline_72h.png
fig_04_distributions.png
fig_05_correlation_scatter.png
fig_06_drop_event_window.png
fig_07_hourly_pattern.png
src/
 analyze_biosignal.py # 전처리 + EDA 핵심 코드
 analyze_biosignal_full_presentation.ipynb # 발표용 노트북
 app_streamlit.py # Streamlit 대시보드
 build_report.py # 보고서 자동 생성
 extract_queries.sql # DB 조회 SQL 예시

├── docs/
datamining_midterm_report.docx
datamining_midterm_report.pdf
datamining_midterm_presentation.pptx

└── README.md


---

##  Data Pipeline


Raw Data (Long format)
→ Pivot (Wide format)
→ Preprocessing
→ EDA Analysis
→ Visualization (Streamlit Dashboard)


---

##  Key Preprocessing Steps

- Long format → Wide format 변환 (pivot)
- 결측값 및 중복 데이터 제거
- 재실 상태(Status = 1) 데이터만 유지
- 이상치 제거  
  - Heart: 45 ~ 130 bpm  
  - Breath: 8 ~ 30 rpm
- 파생 변수 생성  
  - Rolling mean (5분 이동평균)  
  - 변화량 (delta)  
  - 시간(hour), 날짜(date)

---

##  Risk Definition (Threshold-based)

다음 기준을 만족하면 위험 상태로 정의:

- Drop == 1 (낙상 발생)
- Heart > 100 bpm
- Breath > 25 rpm
- |ΔHeart| ≥ 15 (심박 급변)
- |ΔBreath| ≥ 5 (호흡 급변)

---

##  Key Results

- Raw rows: **80,600**
- Final analysis rows: **17,960**
- Risk rows: **3,193 (17.8%)**
- Heart–Breath correlation: **0.867 (strong positive)**

---

##  EDA Insights

- Heart와 Breath는 시간대에 따라 함께 변동
- 밤 시간대 → 평균 낮음
- 활동 시간대 → 동시 상승
- Drop 이벤트 전후에서 단기 변화 발생
- 강한 양의 상관관계 (r = 0.867)

---

##  Dashboard (Streamlit)

기능:

- 시간 범위 필터링 (Time Range Slider)
- 위험 상태 필터링 (Risk Only)
- Heart / Breath 시계열 그래프
- 상관관계 분석 (Scatter)
- 시간대별 평균 패턴

---

##  How to Run

### 1. 분석 실행
```bash
python src/analyze_biosignal.py
2. 대시보드 실행
python -m streamlit run src/app_streamlit.py
 Deployment (AWS EC2)
Python 분석 코드 및 Streamlit 서버를 EC2에 배포
server.address = 0.0.0.0 설정으로 외부 접근 가능
보안 그룹에서 8501 포트 개방
브라우저 접속:
http://비공개
 Research Basis

본 프로젝트의 threshold 기반 이상 탐지 방식은
다음 임상 연구를 참고함:

Subbe et al., 2001
Validation of a modified Early Warning Score in medical admissions
https://academic.oup.com/qjmed/article/94/10/521/1569607

 심박수와 호흡수를 기반으로 환자의 위험 상태를 판단하는
임상적 threshold 접근 방식

 Key Insight
의료 데이터 분석에서는 **해석 가능성(Interpretability)**이 중요
복잡한 모델 없이도 Rule-based 방식으로 위험 상태 설명 가능
분석 결과를 Streamlit으로 연결하면
실시간 모니터링 시스템으로 확장 가능
 Future Work
실제 데이터로 동일 파이프라인 재검증
Isolation Forest / One-Class SVM 비교
낙상 전조 패턴 기반 feature engineering
EC2 + 도메인 + HTTPS 배포 확장