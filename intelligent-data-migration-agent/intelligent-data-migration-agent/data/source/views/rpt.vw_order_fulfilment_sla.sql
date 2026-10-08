CREATE OR ALTER VIEW rpt.vw_order_fulfilment_sla
AS
SELECT
    s.shipment_src_id,
    s.order_src_id,
    s.carrier,
    ds.full_date                              AS ship_date,
    dp.full_date                              AS promised_date,
    CASE WHEN s.delivered_date_key > 0 THEN dd.full_date END AS delivered_date,
    s.transit_business_days,
    s.promised_business_days,
    s.delivery_status,
    s.is_sla_breach,
    CASE
        WHEN s.delivered_date_key > 0 AND dd.full_date > dp.full_date
            THEN dbo.fn_business_days(dp.full_date, dd.full_date)
        ELSE 0
    END                                       AS business_days_late,
    CASE
        WHEN s.delivery_status = 'LATE_UNDELIVERED'                       THEN 'OPEN - LATE'
        WHEN s.delivery_status IN ('IN_TRANSIT', 'PENDING')               THEN 'OPEN'
        WHEN s.is_sla_breach = 0                                          THEN 'ON TIME'
        WHEN dbo.fn_business_days(dp.full_date, dd.full_date) <= 2        THEN '1-2 DAYS LATE'
        ELSE '3+ DAYS LATE'
    END                                       AS sla_bucket,
    AVG(CAST(s.is_sla_breach AS decimal(5,4))) OVER (
        PARTITION BY s.carrier, ds.calendar_year, ds.month_number) AS carrier_month_breach_rate
FROM fact.shipment AS s
JOIN dim.date      AS ds ON ds.date_key = s.ship_date_key
JOIN dim.date      AS dp ON dp.date_key = s.promised_date_key
JOIN dim.date      AS dd ON dd.date_key = s.delivered_date_key;
