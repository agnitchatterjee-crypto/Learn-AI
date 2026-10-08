CREATE TABLE ref.currency_rate (
    rate_date     date          NOT NULL,
    from_currency char(3)       NOT NULL,
    to_currency   char(3)       NOT NULL,
    rate          decimal(18,8) NOT NULL,
    CONSTRAINT pk_ref_currency_rate PRIMARY KEY CLUSTERED (from_currency, to_currency, rate_date)
);
