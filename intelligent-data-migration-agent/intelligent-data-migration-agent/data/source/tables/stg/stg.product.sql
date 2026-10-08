CREATE TABLE stg.product (
    product_src_id     varchar(20)   NOT NULL,
    product_name       nvarchar(200) NULL,
    category           nvarchar(100) NOT NULL,
    subcategory        nvarchar(100) NOT NULL,
    brand              nvarchar(100) NOT NULL,
    list_price         decimal(18,2) NOT NULL,
    unit_cost          decimal(18,2) NOT NULL,
    status             varchar(20)   NOT NULL,
    source_modified_at datetime2     NULL,
    load_batch_id      int           NOT NULL,
    loaded_at          datetime2     NOT NULL CONSTRAINT df_stg_product_loaded_at DEFAULT SYSDATETIME(),
    CONSTRAINT pk_stg_product PRIMARY KEY CLUSTERED (product_src_id)
);
