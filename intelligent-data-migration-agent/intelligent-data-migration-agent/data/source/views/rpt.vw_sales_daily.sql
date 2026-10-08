CREATE OR ALTER VIEW rpt.vw_sales_daily
AS
WITH daily AS (
    SELECT
        d.full_date,
        p.category,
        f.ship_country,
        SUM(f.net_amount_usd)          AS net_revenue_usd,
        SUM(f.quantity)                AS units,
        COUNT(DISTINCT f.order_src_id) AS orders
    FROM fact.order_line AS f
    JOIN dim.date    AS d ON d.date_key    = f.order_date_key
    JOIN dim.product AS p ON p.product_key = f.product_key
    GROUP BY d.full_date, p.category, f.ship_country
)
SELECT
    full_date,
    category,
    ship_country,
    net_revenue_usd,
    units,
    orders,
    AVG(net_revenue_usd) OVER (
        PARTITION BY category, ship_country
        ORDER BY full_date
        ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) AS net_revenue_7row_avg_usd,
    SUM(net_revenue_usd) OVER (
        PARTITION BY category, ship_country, YEAR(full_date), MONTH(full_date)
        ORDER BY full_date
        ROWS UNBOUNDED PRECEDING)                 AS month_to_date_usd
FROM daily;
