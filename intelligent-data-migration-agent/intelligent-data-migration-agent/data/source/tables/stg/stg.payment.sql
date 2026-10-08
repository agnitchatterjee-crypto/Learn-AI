CREATE TABLE stg.payment (
    payment_src_id  varchar(30)   NOT NULL,
    order_src_id    varchar(20)   NOT NULL,   -- one row per payment x order allocation
    method          varchar(20)   NULL,
    payment_type    varchar(20)   NULL,       -- CAPTURE / REFUND / CHARGEBACK
    amount          decimal(18,2) NOT NULL,
    currency_code   char(3)       NULL,
    status          varchar(20)   NULL,
    event_ts        datetime2     NULL,
    gateway_ref     varchar(50)   NULL,
    load_batch_id   int           NOT NULL,
    loaded_at       datetime2     NOT NULL CONSTRAINT df_stg_payment_loaded_at DEFAULT SYSDATETIME(),
    CONSTRAINT pk_stg_payment PRIMARY KEY CLUSTERED (payment_src_id, order_src_id)
);
