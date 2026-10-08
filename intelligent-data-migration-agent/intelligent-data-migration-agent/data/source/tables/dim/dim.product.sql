CREATE TABLE dim.product (
    product_key     int           IDENTITY(1,1) NOT NULL,   -- -1 = unknown member
    product_src_id  varchar(20)   NOT NULL,
    product_name    nvarchar(200) NULL,
    category        nvarchar(100) NULL,
    subcategory     nvarchar(100) NULL,
    brand           nvarchar(100) NULL,
    list_price      decimal(18,2) NULL,
    unit_cost       decimal(18,2) NULL,
    status          varchar(20)   NULL,
    is_active       bit           NOT NULL CONSTRAINT df_dim_product_is_active DEFAULT 1,
    created_at      datetime2     NOT NULL CONSTRAINT df_dim_product_created_at DEFAULT SYSDATETIME(),
    updated_at      datetime2     NOT NULL CONSTRAINT df_dim_product_updated_at DEFAULT SYSDATETIME(),
    CONSTRAINT pk_dim_product PRIMARY KEY CLUSTERED (product_key),
    CONSTRAINT uq_dim_product_src UNIQUE (product_src_id)
);
