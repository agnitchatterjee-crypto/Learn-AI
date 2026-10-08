CREATE TABLE lnd.payment (
    lnd_id          bigint        IDENTITY(1,1) NOT NULL,
    payment_src_id  varchar(30)   NOT NULL,
    payload         nvarchar(max) NULL,   -- JSON document from the payment gateway
    received_at     datetime2     NOT NULL CONSTRAINT df_lnd_payment_received_at DEFAULT SYSDATETIME(),
    CONSTRAINT pk_lnd_payment PRIMARY KEY CLUSTERED (lnd_id)
);
CREATE NONCLUSTERED INDEX ix_lnd_payment_received ON lnd.payment (received_at);
