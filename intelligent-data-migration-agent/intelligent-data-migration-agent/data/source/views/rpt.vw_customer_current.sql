CREATE OR ALTER VIEW rpt.vw_customer_current
AS
SELECT
    c.customer_key,
    c.customer_src_id,
    c.full_name,
    c.email,
    c.city,
    c.state_code,
    c.country_code,
    c.customer_segment,
    c.effective_from                                   AS current_since,
    ISNULL(r.lifetime_net_revenue_usd, 0)              AS lifetime_net_revenue_usd,
    dbo.fn_customer_tier(ISNULL(r.lifetime_net_revenue_usd, 0)) AS customer_tier,
    r.last_order_month
FROM dim.customer AS c
JOIN (
    SELECT customer_src_id, MIN(customer_key) AS anchor_key
    FROM dim.customer
    WHERE customer_key > 0
    GROUP BY customer_src_id
) AS anc
  ON anc.customer_src_id = c.customer_src_id
LEFT JOIN (
    SELECT customer_key,
           SUM(net_revenue_usd) AS lifetime_net_revenue_usd,
           MAX(month_start)     AS last_order_month
    FROM agg.customer_monthly_revenue
    GROUP BY customer_key
) AS r
  ON r.customer_key = anc.anchor_key
WHERE c.is_current = 1
  AND c.customer_key > 0;
