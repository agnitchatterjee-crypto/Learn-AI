/* Revenue per customer, attributed to the customer's current name regardless of
   which SCD2 version was in force when the order was placed. */
CREATE OR ALTER VIEW rpt.vw_customer_revenue
AS
SELECT
    cur.customer_src_id                                          AS customer_id,
    cur.full_name                                                AS customer_name,
    SUM(f.net_amount_usd)                                        AS revenue,
    SUM(CASE WHEN f.is_return = 0 THEN f.net_amount_usd ELSE 0 END) AS sales_revenue,
    SUM(CASE WHEN f.is_return = 1 THEN f.net_amount_usd ELSE 0 END) AS returns_value,
    COUNT(DISTINCT f.order_src_id)                               AS order_count
FROM fact.order_line AS f
JOIN dim.customer    AS ver ON ver.customer_key    = f.customer_key
JOIN dim.customer    AS cur ON cur.customer_src_id = ver.customer_src_id
                           AND cur.is_current = 1
WHERE f.customer_key > 0
GROUP BY cur.customer_src_id, cur.full_name;
