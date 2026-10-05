-- Monthly net sales, margin and return rate by department
SELECT d.year, d.month_num, p.department,
       SUM(s.net_sales) AS net_sales, SUM(s.gross_margin) AS margin,
       ROUND(100.0 * SUM(s.gross_margin) / NULLIF(SUM(s.net_sales), 0), 1) AS margin_pct
FROM fact_sales s JOIN dim_date d ON d.date_key = s.date_key JOIN dim_product p ON p.product_key = s.product_key
GROUP BY d.year, d.month_num, p.department ORDER BY 1, 2, 3;

-- Top 10 products by revenue with their average review rating
SELECT p.product_name, SUM(s.net_sales) AS revenue,
       (SELECT ROUND(AVG(rating), 2) FROM fact_product_reviews r WHERE r.product_key = p.product_key) AS avg_rating
FROM fact_sales s JOIN dim_product p ON p.product_key = s.product_key
GROUP BY p.product_key, p.product_name ORDER BY revenue DESC LIMIT 10;

-- Customer lifetime value by loyalty tier AS OF the order date (uses the SCD2 key)
SELECT c.loyalty_tier, COUNT(DISTINCT c.customer_id) AS customers, ROUND(SUM(s.net_sales), 2) AS revenue
FROM fact_sales s JOIN dim_customer c ON c.customer_key = s.customer_key
GROUP BY c.loyalty_tier ORDER BY revenue DESC;

-- Promotion lift: share of discounted lines and average discount by promotion
SELECT pr.promo_name, COUNT(*) AS lines, ROUND(SUM(s.discount_amount), 2) AS discount_given, ROUND(SUM(s.net_sales), 2) AS net_sales
FROM fact_sales s JOIN dim_promotion pr ON pr.promo_key = s.promo_key WHERE pr.promo_key <> 0
GROUP BY pr.promo_name ORDER BY net_sales DESC LIMIT 15;

-- Return rate and top reasons by department
SELECT p.department, COUNT(DISTINCT s.sales_line_key) AS lines, COUNT(DISTINCT r.return_key) AS returns,
       ROUND(100.0 * COUNT(DISTINCT r.return_key) / COUNT(DISTINCT s.sales_line_key), 2) AS return_rate_pct
FROM fact_sales s JOIN dim_product p ON p.product_key = s.product_key LEFT JOIN fact_returns r ON r.sales_line_key = s.sales_line_key
GROUP BY p.department ORDER BY return_rate_pct DESC;

-- Stock-outs and open purchase orders by store
SELECT st.store_name, SUM(i.stockout_flag) AS stockout_weeks, SUM(i.inventory_value) AS inventory_value
FROM fact_inventory_snapshot i JOIN dim_store st ON st.store_key = i.store_key
GROUP BY st.store_name ORDER BY stockout_weeks DESC LIMIT 10;
