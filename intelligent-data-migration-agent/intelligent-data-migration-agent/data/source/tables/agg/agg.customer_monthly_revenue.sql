/* NOTE: agg.customer_revenue_trailing is created dynamically (SELECT INTO) by
   agg.usp_refresh_customer_monthly_revenue and therefore has no static DDL. */
CREATE TABLE agg.customer_monthly_revenue (
    customer_key                int           NOT NULL,
    month_start                 date          NOT NULL,
    order_count                 int           NOT NULL,
    sales_revenue_usd           decimal(18,2) NOT NULL,
    returns_usd                 decimal(18,2) NOT NULL,   -- negative
    net_revenue_usd             decimal(18,2) NOT NULL,
    cumulative_net_revenue_usd  decimal(18,2) NOT NULL,   -- running lifetime value
    cumulative_order_count      int           NOT NULL,
    customer_tier               varchar(10)   NOT NULL,
    load_batch_id               int           NOT NULL,
    updated_at                  datetime2     NOT NULL CONSTRAINT df_agg_cmr_updated_at DEFAULT SYSDATETIME(),
    CONSTRAINT pk_agg_customer_monthly_revenue PRIMARY KEY CLUSTERED (customer_key, month_start)
);
