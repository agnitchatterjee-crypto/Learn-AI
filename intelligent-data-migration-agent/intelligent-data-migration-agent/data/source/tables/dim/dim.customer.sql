/* SCD Type 2. First version of a customer is effective from 1900-01-01 so that
   late-arriving facts always find a version; open versions end at 9999-12-31. */
CREATE TABLE dim.customer (
    customer_key     int           IDENTITY(1,1) NOT NULL,   -- -1 = unknown member
    customer_src_id  varchar(20)   NOT NULL,
    first_name       nvarchar(100) NULL,
    last_name        nvarchar(100) NULL,
    full_name        nvarchar(200) NULL,
    email            varchar(255)  NULL,
    phone            varchar(50)   NULL,
    address_line     nvarchar(255) NULL,
    city             nvarchar(100) NULL,
    state_code       varchar(10)   NULL,
    country_code     char(2)       NULL,
    customer_segment varchar(30)   NULL,
    row_hash         binary(32)    NOT NULL,
    effective_from   date          NOT NULL,
    effective_to     date          NOT NULL CONSTRAINT df_dim_customer_effective_to DEFAULT '9999-12-31',
    is_current       bit           NOT NULL CONSTRAINT df_dim_customer_is_current DEFAULT 1,
    created_at       datetime2     NOT NULL CONSTRAINT df_dim_customer_created_at DEFAULT SYSDATETIME(),
    updated_at       datetime2     NOT NULL CONSTRAINT df_dim_customer_updated_at DEFAULT SYSDATETIME(),
    CONSTRAINT pk_dim_customer PRIMARY KEY CLUSTERED (customer_key)
);
CREATE UNIQUE NONCLUSTERED INDEX ux_dim_customer_current ON dim.customer (customer_src_id) WHERE is_current = 1;
CREATE NONCLUSTERED INDEX ix_dim_customer_pit ON dim.customer (customer_src_id, effective_from, effective_to) INCLUDE (customer_key);
