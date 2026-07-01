-- Populate dim_date for 2023-2025
INSERT INTO dim_date (date_key, year, quarter, month, month_name, week, day_of_week, day_name, is_weekend)
SELECT
    d::DATE                                                AS date_key,
    EXTRACT(YEAR  FROM d)::INT                             AS year,
    EXTRACT(QUARTER FROM d)::INT                           AS quarter,
    EXTRACT(MONTH  FROM d)::INT                            AS month,
    TO_CHAR(d, 'Month')                                    AS month_name,
    EXTRACT(WEEK   FROM d)::INT                            AS week,
    EXTRACT(DOW    FROM d)::INT                            AS day_of_week,
    TO_CHAR(d, 'Day')                                      AS day_name,
    EXTRACT(DOW FROM d) IN (0, 6)                          AS is_weekend
FROM GENERATE_SERIES('2023-01-01'::DATE, '2025-12-31'::DATE, '1 day'::INTERVAL) AS d;
