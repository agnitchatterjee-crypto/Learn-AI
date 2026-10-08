CREATE TABLE stg.shipment (
    shipment_src_id varchar(30)  NOT NULL,
    order_src_id    varchar(20)  NOT NULL,   -- consolidated shipments carry several orders
    carrier         varchar(30)  NULL,
    shipped_ts      datetime2    NULL,
    delivered_ts    datetime2    NULL,
    promised_ts     datetime2    NULL,
    weight_kg       decimal(9,3) NULL,
    load_batch_id   int          NOT NULL,
    loaded_at       datetime2    NOT NULL CONSTRAINT df_stg_shipment_loaded_at DEFAULT SYSDATETIME(),
    CONSTRAINT pk_stg_shipment PRIMARY KEY CLUSTERED (shipment_src_id, order_src_id)
);
