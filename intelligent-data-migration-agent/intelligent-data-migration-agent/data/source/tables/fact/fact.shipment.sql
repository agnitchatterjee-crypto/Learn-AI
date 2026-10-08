CREATE TABLE fact.shipment (
    shipment_key             bigint       IDENTITY(1,1) NOT NULL,
    shipment_src_id          varchar(30)  NOT NULL,
    order_src_id             varchar(20)  NOT NULL,
    customer_key             int          NOT NULL,
    carrier                  varchar(30)  NULL,
    ship_date_key            int          NOT NULL,   -- -1 = unknown / not applicable
    delivered_date_key       int          NOT NULL,
    promised_date_key        int          NOT NULL,
    weight_kg                decimal(9,3) NULL,
    transit_business_days    int          NULL,
    promised_business_days   int          NULL,
    delivery_status          varchar(20)  NOT NULL,   -- DELIVERED / IN_TRANSIT / LATE_UNDELIVERED / PENDING
    is_sla_breach            bit          NOT NULL,
    load_batch_id            int          NOT NULL,
    created_at               datetime2    NOT NULL CONSTRAINT df_fact_shipment_created_at DEFAULT SYSDATETIME(),
    updated_at               datetime2    NOT NULL CONSTRAINT df_fact_shipment_updated_at DEFAULT SYSDATETIME(),
    CONSTRAINT pk_fact_shipment PRIMARY KEY CLUSTERED (shipment_key),
    CONSTRAINT uq_fact_shipment_nk UNIQUE (shipment_src_id, order_src_id)
);
