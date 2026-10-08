CREATE OR ALTER VIEW rpt.vw_customer_cohort_retention
AS
WITH order_months AS (
    SELECT DISTINCT
        cu.customer_src_id,
        DATEFROMPARTS(d.calendar_year, d.month_number, 1) AS order_month
    FROM fact.order_line AS f
    JOIN dim.date        AS d  ON d.date_key      = f.order_date_key
    JOIN dim.customer    AS cu ON cu.customer_key = f.customer_key
    WHERE f.line_type = 'SALE'
      AND f.customer_key > 0
),
cohorts AS (
    SELECT customer_src_id, MIN(order_month) AS cohort_month
    FROM order_months
    GROUP BY customer_src_id
),
cohort_size AS (
    SELECT cohort_month, COUNT(*) AS cohort_customers
    FROM cohorts
    GROUP BY cohort_month
),
activity AS (
    SELECT
        c.cohort_month,
        DATEDIFF(month, c.cohort_month, o.order_month) AS month_offset,
        COUNT(DISTINCT o.customer_src_id)              AS active_customers
    FROM order_months AS o
    JOIN cohorts      AS c ON c.customer_src_id = o.customer_src_id
    GROUP BY c.cohort_month, DATEDIFF(month, c.cohort_month, o.order_month)
)
SELECT
    a.cohort_month,
    a.month_offset,
    s.cohort_customers,
    a.active_customers,
    CAST(100.0 * a.active_customers / s.cohort_customers AS decimal(5,2)) AS retention_pct,
    a.active_customers
        - LAG(a.active_customers) OVER (PARTITION BY a.cohort_month ORDER BY a.month_offset) AS change_vs_prev_month,
    FIRST_VALUE(a.active_customers) OVER (PARTITION BY a.cohort_month ORDER BY a.month_offset) AS month0_customers
FROM activity    AS a
JOIN cohort_size AS s ON s.cohort_month = a.cohort_month;
