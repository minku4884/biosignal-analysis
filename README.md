# Radar Biosignal Multi-device Risk Detection Project

이 프로젝트는 레이더 기반 환자 생체신호 데이터의 **다중 device 확장형 분석 파이프라인**입니다.  
현재 실측 데이터가 충분하지 않은 상황을 반영하여, 제출용 데모 결과는 **실측 환경을 모사한 realistic synthetic dataset**으로 생성했습니다. 단순 랜덤 데이터가 아니라 환자별 baseline, device offset, 시간대별 변동, 센서 노이즈, 결측, 낙상 전후 window를 반영합니다.

> 중요한 원칙: synthetic demo data를 실제 임상 실측 데이터라고 주장하지 않습니다. 보고서에서는 "실측 환경 모사 데이터"라고 명확히 설명합니다.

## 핵심 기능

1. `data/raw_devices/` 폴더에 CSV/XLSX device export 파일을 여러 개 넣으면 자동 통합
2. long format `timestamp, device_id, data_category, avg_value`와 wide format `datetime, device_id, Heart, Breath, Drop, Status` 모두 지원
3. 컬럼명이 다르면 `configs/schema_mapping.json`에서 alias만 추가하면 됨
4. Fixed threshold, personalized threshold, Isolation Forest, One-Class SVM 비교
5. device별 risk rate, Heart-Breath correlation, data quality, anomaly score 자동 산출
6. Streamlit dashboard와 보고서/PPT 제출자료 포함

## 폴더 구조

```text
configs/                  # schema, threshold, pipeline 설정
data/raw_devices/          # 앞으로 네가 가져올 device Excel/CSV 파일 넣는 곳
data/templates/            # Excel 업로드 템플릿
data/processed/            # 파이프라인 실행 결과 CSV/JSON
figures/                   # 보고서/PPT용 시각화
models/                    # Isolation Forest, One-Class SVM 모델 파일
docs/                      # 최종 보고서, 발표자료, 제출 체크리스트
src/                       # 데이터 생성, import, 분석, dashboard 코드
```

## 실행 방법

```bash
pip install -r requirements.txt
python src/generate_realistic_synthetic_data.py
python src/run_pipeline.py
streamlit run src/app_streamlit.py
```

## 나중에 실제 device Excel 파일을 추가하는 방법

1. 장비에서 Excel 또는 CSV로 export한다.
2. 파일을 `data/raw_devices/`에 넣는다.
3. 컬럼명이 다르면 `configs/schema_mapping.json`에 alias를 추가한다.
4. 아래 명령 실행:

```bash
python src/run_pipeline.py
```

5. 결과는 `data/processed/`, 그림은 `figures/`, dashboard는 Streamlit에서 확인한다.

## 입력 파일 형식

### Long format - 기존 565.csv와 같은 방식

| timestamp | device_id | data_category | min_value | avg_value | max_value |
|---:|---|---:|---:|---:|---:|
| 1740787200 | D701 | 14223 | 72.1 | 72.8 | 73.5 |
| 1740787200 | D701 | 14221 | 14.2 | 14.5 | 14.8 |

Category code:

| code | metric |
|---:|---|
| 14211 | Status |
| 14215 | Drop |
| 14221 | Breath |
| 14223 | Heart |

### Wide format - 엑셀에서 직접 보기 편한 방식

| datetime | device_id | patient_id | Heart | Breath | Drop | Status |
|---|---|---|---:|---:|---:|---:|
| 2026-03-01 00:00 | D701 | P001 | 72.8 | 14.5 | 0 | 1 |

## 제출용 포인트

- 단순 threshold가 아니라 fixed threshold와 personalized threshold를 비교함
- 낙상 Drop은 학습 label로 과장하지 않고, 이벤트 전후 window feature로 해석함
- MEWS는 full MEWS가 아니라 MEWS-inspired threshold라고 명시함
- 실측 데이터 부족 상황에서 realistic synthetic data로 pipeline feasibility를 검증했다고 설명함
- 나중에 device Excel이 늘어나도 구조 변경 없이 확장 가능함
