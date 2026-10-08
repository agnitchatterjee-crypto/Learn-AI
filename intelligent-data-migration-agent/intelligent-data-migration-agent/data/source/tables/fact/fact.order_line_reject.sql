CREATE TABLE fact.order_line_reject (
    reject_id       bigint        IDENTITY(1,1) NOT NULL,
    load_batch_id   int           NOT NULL,
    order_src_id    varchar(20)   NOT NULL,
    line_no         int           NOT NULL,
    order_date      date          NULL,
    product_src_id  varchar(20)   NULL,
    reject_code     varchar(30)   NOT NULL,   -- BAD_QUANTITY / UNKNOWN_PRODUCT / RETURN_NO_ORIGINAL / BAD_PRICE / NO_FX_RATE
    reject_reason   varchar(500)  NULL,
    rejected_at     datetime2     NOT NULL CONSTRAINT df_fact_order_line_reject_at DEFAULT SYSDATETIME(),
    CONSTRAINT pk_fact_order_line_reject PRIMARY KEY CLUSTERED (reject_id)
);
CREATE NONCLUSTERED INDEX ix_fact_order_line_reject_nk ON fact.order_line_reject (order_src_id, line_no);
