CREATE TABLE fact.payment (
    payment_key           bigint        IDENTITY(1,1) NOT NULL,
    payment_src_id        varchar(30)   NOT NULL,
    order_src_id          varchar(20)   NOT NULL,
    payment_date_key      int           NOT NULL,
    customer_key          int           NOT NULL,
    method                varchar(20)   NULL,
    payment_type          varchar(20)   NOT NULL,   -- CAPTURE / REFUND / CHARGEBACK
    status                varchar(20)   NULL,
    currency_code         char(3)       NULL,
    amount_signed         decimal(18,2) NOT NULL,   -- refunds / chargebacks negative
    amount_signed_usd     decimal(18,2) NOT NULL,
    running_paid_usd      decimal(18,2) NOT NULL,   -- running total per order, in event order
    order_net_paid_usd    decimal(18,2) NOT NULL,   -- final net paid for the order across all events
    order_net_amount_usd  decimal(18,2) NULL,       -- order value from fact.order_line (NULL while order is missing)
    is_order_paid_in_full bit           NOT NULL,
    is_orphan             bit           NOT NULL,   -- order not loaded yet when payment arrived
    event_ts              datetime2     NULL,
    load_batch_id         int           NOT NULL,
    created_at            datetime2     NOT NULL CONSTRAINT df_fact_payment_created_at DEFAULT SYSDATETIME(),
    updated_at            datetime2     NOT NULL CONSTRAINT df_fact_payment_updated_at DEFAULT SYSDATETIME(),
    CONSTRAINT pk_fact_payment PRIMARY KEY CLUSTERED (payment_key),
    CONSTRAINT uq_fact_payment_nk UNIQUE (payment_src_id, order_src_id)
);
CREATE NONCLUSTERED INDEX ix_fact_payment_order ON fact.payment (order_src_id) INCLUDE (event_ts, payment_type, amount_signed_usd);
