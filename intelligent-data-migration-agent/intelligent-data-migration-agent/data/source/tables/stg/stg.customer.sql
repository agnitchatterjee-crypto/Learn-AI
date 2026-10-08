CREATE TABLE stg.customer (
    customer_src_id     varchar(20)   NOT NULL,
    first_name          nvarchar(100) NULL,
    last_name           nvarchar(100) NULL,
    full_name           nvarchar(200) NULL,
    email               varchar(255)  NULL,
    phone               varchar(50)   NULL,
    address_line        nvarchar(255) NULL,
    city                nvarchar(100) NULL,
    state_code          varchar(10)   NULL,
    country_code        char(2)       NULL,
    customer_segment    varchar(30)   NOT NULL,
    source_created_date date          NULL,
    source_modified_at  datetime2     NULL,
    load_batch_id       int           NOT NULL,
    loaded_at           datetime2     NOT NULL CONSTRAINT df_stg_customer_loaded_at DEFAULT SYSDATETIME(),
    CONSTRAINT pk_stg_customer PRIMARY KEY CLUSTERED (customer_src_id)
);
