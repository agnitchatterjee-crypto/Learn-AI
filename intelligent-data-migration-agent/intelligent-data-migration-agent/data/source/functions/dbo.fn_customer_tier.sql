CREATE OR ALTER FUNCTION dbo.fn_customer_tier (@net_revenue_usd decimal(18,2))
RETURNS varchar(10)
AS
BEGIN
    RETURN CASE
               WHEN @net_revenue_usd >= 10000 THEN 'PLATINUM'
               WHEN @net_revenue_usd >=  5000 THEN 'GOLD'
               WHEN @net_revenue_usd >=  1000 THEN 'SILVER'
               WHEN @net_revenue_usd >      0 THEN 'BRONZE'
               ELSE 'NONE'
           END;
END
