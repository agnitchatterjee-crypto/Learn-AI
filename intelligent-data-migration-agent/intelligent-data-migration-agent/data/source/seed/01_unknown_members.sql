-- Unknown-member rows so facts never carry NULL surrogate keys.
SET IDENTITY_INSERT dim.customer ON;
IF NOT EXISTS (SELECT 1 FROM dim.customer WHERE customer_key = -1)
    INSERT INTO dim.customer (customer_key, customer_src_id, full_name, customer_segment, row_hash, effective_from, effective_to, is_current)
    VALUES (-1, 'UNKNOWN', N'Unknown Customer', 'OTHER', CAST(0 AS binary(32)), '1900-01-01', '9999-12-31', 1);
SET IDENTITY_INSERT dim.customer OFF;

SET IDENTITY_INSERT dim.product ON;
IF NOT EXISTS (SELECT 1 FROM dim.product WHERE product_key = -1)
    INSERT INTO dim.product (product_key, product_src_id, product_name, category, subcategory, brand, status, is_active)
    VALUES (-1, 'UNKNOWN', N'Unknown Product', N'UNCATEGORISED', N'UNCATEGORISED', N'UNKNOWN', 'UNKNOWN', 0);
SET IDENTITY_INSERT dim.product OFF;

IF NOT EXISTS (SELECT 1 FROM dim.date WHERE date_key = -1)
    INSERT INTO dim.date (date_key, full_date, day_of_week, day_name, day_of_month, day_of_year, iso_week,
                          month_number, month_name, quarter_number, calendar_year, is_weekend, is_holiday,
                          fiscal_year, fiscal_quarter, fiscal_period)
    VALUES (-1, '1900-01-01', 0, 'Unknown', 0, 0, 0, 0, 'Unknown', 0, 1900, 0, 0, 0, 0, 0);
