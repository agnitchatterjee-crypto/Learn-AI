CREATE TABLE fact.order_line (
    order_line_key      bigint        IDENTITY(1,1) NOT NULL,
    order_src_id        varchar(20)   NOT NULL,
    line_no             int           NOT NULL,
    order_date_key      int           NOT NULL,
    customer_key        int           NOT NULL,
    product_key         int           NOT NULL,
    channel             varchar(30)   NULL,
    ship_country        char(2)       NULL,
    currency_code       char(3)       NOT NULL,
    order_status        varchar(20)   NULL,
    line_type           varchar(10)   NOT NULL,   -- SALE / RETURN
    quantity            int           NOT NULL,   -- signed: returns are negative
    unit_price          decimal(18,4) NOT NULL,
    gross_amount        decimal(18,2) NOT NULL,   -- signed, local currency
    discount_amount     decimal(18,2) NOT NULL,   -- line + allocated header discount, signed
    net_amount          decimal(18,2) NOT NULL,
    net_amount_usd      decimal(18,2) NOT NULL,
    is_return           bit           NOT NULL,
    is_unknown_customer bit           NOT NULL CONSTRAINT df_fact_order_line_unk_cust DEFAULT 0,
    source_modified_at  datetime2     NOT NULL,
    load_batch_id       int           NOT NULL,
    created_at          datetime2     NOT NULL CONSTRAINT df_fact_order_line_created_at DEFAULT SYSDATETIME(),
    updated_at          datetime2     NOT NULL CONSTRAINT df_fact_order_line_updated_at DEFAULT SYSDATETIME(),
    CONSTRAINT pk_fact_order_line PRIMARY KEY CLUSTERED (order_line_key),
    CONSTRAINT uq_fact_order_line_nk UNIQUE (order_src_id, line_no)
);
CREATE NONCLUSTERED INDEX ix_fact_order_line_date ON fact.order_line (order_date_key) INCLUDE (customer_key, product_key, net_amount_usd);
CREATE NONCLUSTERED INDEX ix_fact_order_line_customer ON fact.order_line (customer_key, order_date_key);
