# 레이더 기반 환자 생체신호 및 재실 상태 분석

내부 테이블 스키마(`timestamp`, `device_id`, `data_category`, `min_value`, `avg_value`, `max_value`)를 반영한 **생체신호 데이터**를 사용해 전처리 및 EDA 파이프라인을 검증했다.

## 프로젝트 구성

- `data/`
  - `biosignal_raw_long_simulated.csv`: raw long-format 데이터
  - `biosignal_wide_before_cleaning.csv`: pivot 후 데이터
  - `biosignal_processed_wide.csv`: 전처리 완료 데이터
  - `analysis_summary.json`: 핵심 통계 요약
- `figures/`
  - 전처리 퍼널, 재실/부재 분포, 시계열, 분포, 상관관계, 낙상 이벤트 시각화
- `src/`
  - `analyze_biosignal.py`: 전처리 및 EDA 수행
  - `app_streamlit.py` : 분석 결과를 시각화하고 사용자 인터페이스를 제공하는 Streamlit 웹 애플리케이션
  - `extract_queries.sql`: 내부 DB 조회용 SQL 예시
- `docs/`
  - `datamining_midterm_report.docx`
  - `datamining_midterm_report.pdf`
  - `datamining_midterm_presentation.pptx`

## 분석 목표

1. 재실/부재 상태를 분리할 수 있는 전처리 절차 정립
2. Heart / Breath의 시간대별 패턴과 분포 파악
3. 낙상 이벤트 전후 변화 탐색
4. 향후 이상 탐지 및 위험도 분류 모델의 feature 후보 정의

## 실행 방법

```bash
python src/analyze_biosignal.py
python python -m streamlit run app_streamlit.py
```

## 핵심 전처리

- long format → wide format pivot
- 결측 row 제거
- Status = 0 제거
- Heart 45~130, Breath 8~30 범위 기반 이상치 제거
- 5분 이동평균 및 변화량 생성

