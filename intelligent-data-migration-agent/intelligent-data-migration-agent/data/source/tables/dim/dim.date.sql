CREATE TABLE dim.date (
    date_key        int          NOT NULL,   -- yyyymmdd; -1 = unknown member
    full_date       date         NOT NULL,
    day_of_week     tinyint      NOT NULL,   -- 1 = Sunday (DATEFIRST 7)
    day_name        varchar(10)  NOT NULL,
    day_of_month    tinyint      NOT NULL,
    day_of_year     smallint     NOT NULL,
    iso_week        tinyint      NOT NULL,
    month_number    tinyint      NOT NULL,
    month_name      varchar(10)  NOT NULL,
    quarter_number  tinyint      NOT NULL,
    calendar_year   smallint     NOT NULL,
    is_weekend      bit          NOT NULL,
    is_holiday      bit          NOT NULL CONSTRAINT df_dim_date_is_holiday DEFAULT 0,
    fiscal_year     smallint     NOT NULL,   -- fiscal year starts 1 April, named for the year it ends
    fiscal_quarter  tinyint      NOT NULL,
    fiscal_period   tinyint      NOT NULL,
    CONSTRAINT pk_dim_date PRIMARY KEY CLUSTERED (date_key),
    CONSTRAINT uq_dim_date_full_date UNIQUE (full_date)
);
