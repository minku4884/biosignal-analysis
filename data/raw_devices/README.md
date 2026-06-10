# data/raw_devices

여기에 device별 Excel 또는 CSV export 파일을 넣고 `python src/run_pipeline.py`를 실행하면 됩니다.

지원 형식:

1. Long format: `timestamp, device_id, data_category, avg_value`
2. Wide format: `datetime, device_id, Heart, Breath, Drop, Status`

컬럼명이 다르면 `configs/schema_mapping.json`에 alias를 추가하세요.
현재 들어있는 `synthetic_device_*.csv` 파일들은 제출/시연용 realistic synthetic demo data입니다.
