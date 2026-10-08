CREATE TABLE etl.watermark (
    source_name  varchar(100) NOT NULL,
    last_value   datetime2    NOT NULL CONSTRAINT df_etl_watermark_last_value DEFAULT '1900-01-01',
    updated_at   datetime2    NOT NULL CONSTRAINT df_etl_watermark_updated_at DEFAULT SYSDATETIME(),
    CONSTRAINT pk_etl_watermark PRIMARY KEY CLUSTERED (source_name)
);
