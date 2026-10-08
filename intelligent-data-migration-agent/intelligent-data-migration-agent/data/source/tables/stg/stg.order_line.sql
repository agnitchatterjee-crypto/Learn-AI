CREATE TABLE stg.order_line (
    order_src_id       varchar(20)   NOT NULL,
    line_no            int           NOT NULL,
    product_src_id     varchar(20)   NULL,
    quantity           int           NOT NULL,
    unit_price         decimal(18,4) NULL,
    line_discount_pct  decimal(5,2)  NOT NULL CONSTRAINT df_stg_order_line_disc DEFAULT 0,
    line_type          varchar(10)   NOT NULL,
    source_modified_at datetime2     NOT NULL,
    load_batch_id      int           NOT NULL,
    loaded_at          datetime2     NOT NULL CONSTRAINT df_stg_order_line_loaded_at DEFAULT SYSDATETIME(),
    CONSTRAINT pk_stg_order_line PRIMARY KEY CLUSTERED (order_src_id, line_no)
);
