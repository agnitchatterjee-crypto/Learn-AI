CREATE TABLE lnd.product (
    lnd_id          bigint        IDENTITY(1,1) NOT NULL,
    product_src_id  varchar(20)   NOT NULL,
    product_name    nvarchar(200) NULL,
    category        nvarchar(100) NULL,
    subcategory     nvarchar(100) NULL,
    brand           nvarchar(100) NULL,
    list_price      varchar(30)   NULL,
    unit_cost       varchar(30)   NULL,
    status          varchar(20)   NULL,
    modified_at     varchar(30)   NULL,
    extract_id      int           NOT NULL,
    extracted_at    datetime2     NOT NULL CONSTRAINT df_lnd_product_extracted_at DEFAULT SYSDATETIME(),
    CONSTRAINT pk_lnd_product PRIMARY KEY CLUSTERED (lnd_id)
);
