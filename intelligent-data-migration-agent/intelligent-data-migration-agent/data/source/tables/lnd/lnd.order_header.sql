CREATE TABLE lnd.order_header (
    lnd_id             bigint       IDENTITY(1,1) NOT NULL,
    order_src_id       varchar(20)  NOT NULL,
    customer_src_id    varchar(20)  NULL,
    order_date         varchar(30)  NULL,   -- raw 'yyyy-mm-dd hh:mi:ss'
    order_status       varchar(20)  NULL,
    currency_code      varchar(10)  NULL,
    channel            varchar(30)  NULL,
    ship_country       varchar(10)  NULL,
    order_discount_amt varchar(30)  NULL,
    modified_at        datetime2    NOT NULL,
    extract_id         int          NOT NULL,
    CONSTRAINT pk_lnd_order_header PRIMARY KEY CLUSTERED (lnd_id)
);
CREATE NONCLUSTERED INDEX ix_lnd_order_header_modified ON lnd.order_header (modified_at) INCLUDE (order_src_id);
