CREATE TABLE lnd.customer (
    lnd_id           bigint        IDENTITY(1,1) NOT NULL,
    customer_src_id  varchar(20)   NULL,
    full_name        nvarchar(200) NULL,
    email            varchar(255)  NULL,
    phone            varchar(50)   NULL,
    address_line     nvarchar(255) NULL,
    city             nvarchar(100) NULL,
    state_code       varchar(10)   NULL,
    country_code     varchar(10)   NULL,
    customer_segment varchar(50)   NULL,
    created_date     varchar(30)   NULL,   -- raw string, mixed formats (yyyy-mm-dd / dd/mm/yyyy)
    modified_at      varchar(30)   NULL,   -- raw string
    extract_id       int           NOT NULL,
    extracted_at     datetime2     NOT NULL CONSTRAINT df_lnd_customer_extracted_at DEFAULT SYSDATETIME(),
    CONSTRAINT pk_lnd_customer PRIMARY KEY CLUSTERED (lnd_id)
);
