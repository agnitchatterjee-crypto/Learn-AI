CREATE TABLE lnd.order_line (
    lnd_id            bigint        IDENTITY(1,1) NOT NULL,
    order_src_id      varchar(20)   NOT NULL,
    line_no           int           NOT NULL,
    product_src_id    varchar(20)   NULL,
    quantity          int           NULL,
    unit_price        decimal(18,4) NULL,
    line_discount_pct decimal(5,2)  NULL,
    line_type         varchar(10)   NULL,   -- SALE / RETURN / CANCEL
    modified_at       datetime2     NOT NULL,
    extract_id        int           NOT NULL,
    CONSTRAINT pk_lnd_order_line PRIMARY KEY CLUSTERED (lnd_id)
);
CREATE NONCLUSTERED INDEX ix_lnd_order_line_order ON lnd.order_line (order_src_id, line_no);
