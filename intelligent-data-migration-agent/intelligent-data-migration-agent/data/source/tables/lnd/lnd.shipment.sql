CREATE TABLE lnd.shipment (
    lnd_id           bigint      IDENTITY(1,1) NOT NULL,
    shipment_src_id  varchar(30) NOT NULL,
    payload_xml      xml         NOT NULL,   -- carrier feed document
    received_at      datetime2   NOT NULL CONSTRAINT df_lnd_shipment_received_at DEFAULT SYSDATETIME(),
    CONSTRAINT pk_lnd_shipment PRIMARY KEY CLUSTERED (lnd_id)
);
CREATE NONCLUSTERED INDEX ix_lnd_shipment_received ON lnd.shipment (received_at);
