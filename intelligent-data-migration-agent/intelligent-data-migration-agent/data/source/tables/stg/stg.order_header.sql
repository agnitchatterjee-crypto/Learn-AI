CREATE TABLE stg.order_header (
    order_src_id       varchar(20)   NOT NULL,
    customer_src_id    varchar(20)   NULL,
    order_date         datetime2     NOT NULL,
    order_status       varchar(20)   NOT NULL,
    currency_code      char(3)       NOT NULL,
    channel            varchar(30)   NOT NULL,
    ship_country       char(2)       NULL,
    order_discount_amt decimal(18,2) NOT NULL CONSTRAINT df_stg_order_header_disc DEFAULT 0,
    days_to_land       int           NULL,   -- days between order date and the extract that carried it
    is_late_arriving   bit           NOT NULL CONSTRAINT df_stg_order_header_late DEFAULT 0,
    source_modified_at datetime2     NOT NULL,
    load_batch_id      int           NOT NULL,
    loaded_at          datetime2     NOT NULL CONSTRAINT df_stg_order_header_loaded_at DEFAULT SYSDATETIME(),
    CONSTRAINT pk_stg_order_header PRIMARY KEY CLUSTERED (order_src_id)
);
