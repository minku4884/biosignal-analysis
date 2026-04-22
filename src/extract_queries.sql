-- 1) Raw long-format extraction from the internal table
SELECT
    timestamp,
    device_id,
    data_category,
    min_value,
    avg_value,
    max_value
FROM bullscare_db.acq_data_1e
WHERE device_id = 661
  AND data_category IN (14211, 14215, 14221, 14223)
ORDER BY timestamp;

-- 2) Example query to find usable non-zero intervals
SELECT
    timestamp,
    device_id,
    data_category,
    avg_value
FROM bullscare_db.acq_data_1e
WHERE device_id = 661
  AND data_category IN (14221, 14223)
  AND avg_value > 0
ORDER BY timestamp;

-- 3) Example aggregation query for visualization
SELECT
    FROM_UNIXTIME(timestamp) AS dt,
    AVG(CASE WHEN data_category = 14223 THEN avg_value END) AS heart_avg,
    AVG(CASE WHEN data_category = 14221 THEN avg_value END) AS breath_avg
FROM bullscare_db.acq_data_1e
WHERE device_id = 661
  AND data_category IN (14221, 14223)
GROUP BY FLOOR(timestamp / 300)
ORDER BY dt;
