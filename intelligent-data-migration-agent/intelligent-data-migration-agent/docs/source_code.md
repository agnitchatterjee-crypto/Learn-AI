# Source Code Bundle

- **Source folder:** `data/source`
- **Generated:** 2026-10-09 00:15
- **Total files:** 55

## Contents

- [SCHEMAS](#schemas) (1 files)
- [SEQUENCES](#sequences) (1 files)
- [TABLES](#tables) (24 files)
- [CONSTRAINTS](#constraints) (1 files)
- [VIEWS](#views) (5 files)
- [FUNCTIONS](#functions) (5 files)
- [PROCEDURES](#procedures) (16 files)
- [SEED](#seed) (2 files)

---

# SCHEMAS

_1 file(s)_

## 00_schemas.sql

**Path:** `schemas/00_schemas.sql`

```sql
/* Synthetic retail order-to-cash platform (SQL Server 2017+).
   lnd  = landing (raw extracts, loaded by upstream ingestion)
   stg  = cleansed staging
   ref  = reference data
   dim / fact / agg = warehouse layers
   rpt  = reporting views
   etl  = control tables and orchestration                      */
IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = 'lnd')  EXEC('CREATE SCHEMA lnd');
IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = 'stg')  EXEC('CREATE SCHEMA stg');
IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = 'ref')  EXEC('CREATE SCHEMA ref');
IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = 'dim')  EXEC('CREATE SCHEMA dim');
IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = 'fact') EXEC('CREATE SCHEMA fact');
IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = 'agg')  EXEC('CREATE SCHEMA agg');
IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = 'rpt')  EXEC('CREATE SCHEMA rpt');
IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = 'etl')  EXEC('CREATE SCHEMA etl');
```

---

# SEQUENCES

_1 file(s)_

## etl.seq_batch_id.sql

**Path:** `sequences/etl.seq_batch_id.sql`

```sql
CREATE SEQUENCE etl.seq_batch_id AS int START WITH 1 INCREMENT BY 1 NO CYCLE;
```

---

# TABLES

_24 file(s)_

## agg.customer_monthly_revenue.sql

**Path:** `tables/agg/agg.customer_monthly_revenue.sql`

```sql
/* NOTE: agg.customer_revenue_trailing is created dynamically (SELECT INTO) by
   agg.usp_refresh_customer_monthly_revenue and therefore has no static DDL. */
CREATE TABLE agg.customer_monthly_revenue (
    customer_key                int           NOT NULL,
    month_start                 date          NOT NULL,
    order_count                 int           NOT NULL,
    sales_revenue_usd           decimal(18,2) NOT NULL,
    returns_usd                 decimal(18,2) NOT NULL,   -- negative
    net_revenue_usd             decimal(18,2) NOT NULL,
    cumulative_net_revenue_usd  decimal(18,2) NOT NULL,   -- running lifetime value
    cumulative_order_count      int           NOT NULL,
    customer_tier               varchar(10)   NOT NULL,
    load_batch_id               int           NOT NULL,
    updated_at                  datetime2     NOT NULL CONSTRAINT df_agg_cmr_updated_at DEFAULT SYSDATETIME(),
    CONSTRAINT pk_agg_customer_monthly_revenue PRIMARY KEY CLUSTERED (customer_key, month_start)
);
```

## dim.customer.sql

**Path:** `tables/dim/dim.customer.sql`

```sql
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
```

## dim.date.sql

**Path:** `tables/dim/dim.date.sql`

```sql
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
```

## dim.product.sql

**Path:** `tables/dim/dim.product.sql`

```sql
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
```

## etl.load_audit.sql

**Path:** `tables/etl/etl.load_audit.sql`

```sql
CREATE TABLE etl.load_audit (
    audit_id          bigint         IDENTITY(1,1) NOT NULL,
    batch_id          int            NOT NULL,
    procedure_name    sysname        NOT NULL,
    step_name         varchar(100)   NOT NULL,
    start_time        datetime2      NOT NULL,
    end_time          datetime2      NOT NULL,
    status            varchar(20)    NOT NULL,   -- SUCCESS / FAILED / SKIPPED / ATTEMPT_FAILED
    rows_read         int            NULL,
    rows_inserted     int            NULL,
    rows_updated      int            NULL,
    rows_rejected     int            NULL,
    target_row_count  bigint         NULL,
    error_number      int            NULL,
    error_message     nvarchar(4000) NULL,
    CONSTRAINT pk_etl_load_audit PRIMARY KEY CLUSTERED (audit_id)
);
CREATE NONCLUSTERED INDEX ix_etl_load_audit_batch ON etl.load_audit (batch_id, start_time);
```

## etl.pipeline_step.sql

**Path:** `tables/etl/etl.pipeline_step.sql`

```sql
CREATE TABLE etl.pipeline_step (
    step_order        int           NOT NULL,
    step_name         varchar(100)  NOT NULL,
    proc_name         nvarchar(300) NOT NULL,   -- invoked dynamically by etl.usp_run_daily_load
    target_table      nvarchar(300) NULL,       -- used for the post-step row-count check
    is_enabled        bit           NOT NULL CONSTRAINT df_etl_pipeline_step_enabled DEFAULT 1,
    max_retries       int           NOT NULL CONSTRAINT df_etl_pipeline_step_retries DEFAULT 2,
    continue_on_error bit           NOT NULL CONSTRAINT df_etl_pipeline_step_coe DEFAULT 0,
    CONSTRAINT pk_etl_pipeline_step PRIMARY KEY CLUSTERED (step_order),
    CONSTRAINT uq_etl_pipeline_step_name UNIQUE (step_name)
);
```

## etl.watermark.sql

**Path:** `tables/etl/etl.watermark.sql`

```sql
CREATE TABLE etl.watermark (
    source_name  varchar(100) NOT NULL,
    last_value   datetime2    NOT NULL CONSTRAINT df_etl_watermark_last_value DEFAULT '1900-01-01',
    updated_at   datetime2    NOT NULL CONSTRAINT df_etl_watermark_updated_at DEFAULT SYSDATETIME(),
    CONSTRAINT pk_etl_watermark PRIMARY KEY CLUSTERED (source_name)
);
```

## fact.order_line.sql

**Path:** `tables/fact/fact.order_line.sql`

```sql
CREATE TABLE fact.order_line (
    order_line_key      bigint        IDENTITY(1,1) NOT NULL,
    order_src_id        varchar(20)   NOT NULL,
    line_no             int           NOT NULL,
    order_date_key      int           NOT NULL,
    customer_key        int           NOT NULL,
    product_key         int           NOT NULL,
    channel             varchar(30)   NULL,
    ship_country        char(2)       NULL,
    currency_code       char(3)       NOT NULL,
    order_status        varchar(20)   NULL,
    line_type           varchar(10)   NOT NULL,   -- SALE / RETURN
    quantity            int           NOT NULL,   -- signed: returns are negative
    unit_price          decimal(18,4) NOT NULL,
    gross_amount        decimal(18,2) NOT NULL,   -- signed, local currency
    discount_amount     decimal(18,2) NOT NULL,   -- line + allocated header discount, signed
    net_amount          decimal(18,2) NOT NULL,
    net_amount_usd      decimal(18,2) NOT NULL,
    is_return           bit           NOT NULL,
    is_unknown_customer bit           NOT NULL CONSTRAINT df_fact_order_line_unk_cust DEFAULT 0,
    source_modified_at  datetime2     NOT NULL,
    load_batch_id       int           NOT NULL,
    created_at          datetime2     NOT NULL CONSTRAINT df_fact_order_line_created_at DEFAULT SYSDATETIME(),
    updated_at          datetime2     NOT NULL CONSTRAINT df_fact_order_line_updated_at DEFAULT SYSDATETIME(),
    CONSTRAINT pk_fact_order_line PRIMARY KEY CLUSTERED (order_line_key),
    CONSTRAINT uq_fact_order_line_nk UNIQUE (order_src_id, line_no)
);
CREATE NONCLUSTERED INDEX ix_fact_order_line_date ON fact.order_line (order_date_key) INCLUDE (customer_key, product_key, net_amount_usd);
CREATE NONCLUSTERED INDEX ix_fact_order_line_customer ON fact.order_line (customer_key, order_date_key);
```

## fact.order_line_reject.sql

**Path:** `tables/fact/fact.order_line_reject.sql`

```sql
CREATE TABLE fact.order_line_reject (
    reject_id       bigint        IDENTITY(1,1) NOT NULL,
    load_batch_id   int           NOT NULL,
    order_src_id    varchar(20)   NOT NULL,
    line_no         int           NOT NULL,
    order_date      date          NULL,
    product_src_id  varchar(20)   NULL,
    reject_code     varchar(30)   NOT NULL,   -- BAD_QUANTITY / UNKNOWN_PRODUCT / RETURN_NO_ORIGINAL / BAD_PRICE / NO_FX_RATE
    reject_reason   varchar(500)  NULL,
    rejected_at     datetime2     NOT NULL CONSTRAINT df_fact_order_line_reject_at DEFAULT SYSDATETIME(),
    CONSTRAINT pk_fact_order_line_reject PRIMARY KEY CLUSTERED (reject_id)
);
CREATE NONCLUSTERED INDEX ix_fact_order_line_reject_nk ON fact.order_line_reject (order_src_id, line_no);
```

## fact.payment.sql

**Path:** `tables/fact/fact.payment.sql`

```sql
CREATE TABLE fact.payment (
    payment_key           bigint        IDENTITY(1,1) NOT NULL,
    payment_src_id        varchar(30)   NOT NULL,
    order_src_id          varchar(20)   NOT NULL,
    payment_date_key      int           NOT NULL,
    customer_key          int           NOT NULL,
    method                varchar(20)   NULL,
    payment_type          varchar(20)   NOT NULL,   -- CAPTURE / REFUND / CHARGEBACK
    status                varchar(20)   NULL,
    currency_code         char(3)       NULL,
    amount_signed         decimal(18,2) NOT NULL,   -- refunds / chargebacks negative
    amount_signed_usd     decimal(18,2) NOT NULL,
    running_paid_usd      decimal(18,2) NOT NULL,   -- running total per order, in event order
    order_net_paid_usd    decimal(18,2) NOT NULL,   -- final net paid for the order across all events
    order_net_amount_usd  decimal(18,2) NULL,       -- order value from fact.order_line (NULL while order is missing)
    is_order_paid_in_full bit           NOT NULL,
    is_orphan             bit           NOT NULL,   -- order not loaded yet when payment arrived
    event_ts              datetime2     NULL,
    load_batch_id         int           NOT NULL,
    created_at            datetime2     NOT NULL CONSTRAINT df_fact_payment_created_at DEFAULT SYSDATETIME(),
    updated_at            datetime2     NOT NULL CONSTRAINT df_fact_payment_updated_at DEFAULT SYSDATETIME(),
    CONSTRAINT pk_fact_payment PRIMARY KEY CLUSTERED (payment_key),
    CONSTRAINT uq_fact_payment_nk UNIQUE (payment_src_id, order_src_id)
);
CREATE NONCLUSTERED INDEX ix_fact_payment_order ON fact.payment (order_src_id) INCLUDE (event_ts, payment_type, amount_signed_usd);
```

## fact.shipment.sql

**Path:** `tables/fact/fact.shipment.sql`

```sql
CREATE TABLE fact.shipment (
    shipment_key             bigint       IDENTITY(1,1) NOT NULL,
    shipment_src_id          varchar(30)  NOT NULL,
    order_src_id             varchar(20)  NOT NULL,
    customer_key             int          NOT NULL,
    carrier                  varchar(30)  NULL,
    ship_date_key            int          NOT NULL,   -- -1 = unknown / not applicable
    delivered_date_key       int          NOT NULL,
    promised_date_key        int          NOT NULL,
    weight_kg                decimal(9,3) NULL,
    transit_business_days    int          NULL,
    promised_business_days   int          NULL,
    delivery_status          varchar(20)  NOT NULL,   -- DELIVERED / IN_TRANSIT / LATE_UNDELIVERED / PENDING
    is_sla_breach            bit          NOT NULL,
    load_batch_id            int          NOT NULL,
    created_at               datetime2    NOT NULL CONSTRAINT df_fact_shipment_created_at DEFAULT SYSDATETIME(),
    updated_at               datetime2    NOT NULL CONSTRAINT df_fact_shipment_updated_at DEFAULT SYSDATETIME(),
    CONSTRAINT pk_fact_shipment PRIMARY KEY CLUSTERED (shipment_key),
    CONSTRAINT uq_fact_shipment_nk UNIQUE (shipment_src_id, order_src_id)
);
```

## lnd.customer.sql

**Path:** `tables/lnd/lnd.customer.sql`

```sql
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
```

## lnd.order_header.sql

**Path:** `tables/lnd/lnd.order_header.sql`

```sql
CREATE TABLE lnd.order_header (
    lnd_id             bigint       IDENTITY(1,1) NOT NULL,
    order_src_id       varchar(20)  NOT NULL,
    customer_src_id    varchar(20)  NULL,
    order_date         varchar(30)  NULL,   -- raw 'yyyy-mm-dd hh:mi:ss'
    order_status       varchar(20)  NULL,
    currency_code      varchar(10)  NULL,
    channel            varchar(30)  NULL,
    ship_country       varchar(10)  NULL,
    order_discount_amt varchar(30)  NULL,
    modified_at        datetime2    NOT NULL,
    extract_id         int          NOT NULL,
    CONSTRAINT pk_lnd_order_header PRIMARY KEY CLUSTERED (lnd_id)
);
CREATE NONCLUSTERED INDEX ix_lnd_order_header_modified ON lnd.order_header (modified_at) INCLUDE (order_src_id);
```

## lnd.order_line.sql

**Path:** `tables/lnd/lnd.order_line.sql`

```sql
CREATE TABLE lnd.order_line (
    lnd_id            bigint        IDENTITY(1,1) NOT NULL,
    order_src_id      varchar(20)   NOT NULL,
    line_no           int           NOT NULL,
    product_src_id    varchar(20)   NULL,
    quantity          int           NULL,
    unit_price        decimal(18,4) NULL,
    line_discount_pct decimal(5,2)  NULL,
    line_type         varchar(10)   NULL,   -- SALE / RETURN / CANCEL
    modified_at       datetime2     NOT NULL,
    extract_id        int           NOT NULL,
    CONSTRAINT pk_lnd_order_line PRIMARY KEY CLUSTERED (lnd_id)
);
CREATE NONCLUSTERED INDEX ix_lnd_order_line_order ON lnd.order_line (order_src_id, line_no);
```

## lnd.payment.sql

**Path:** `tables/lnd/lnd.payment.sql`

```sql
CREATE TABLE lnd.payment (
    lnd_id          bigint        IDENTITY(1,1) NOT NULL,
    payment_src_id  varchar(30)   NOT NULL,
    payload         nvarchar(max) NULL,   -- JSON document from the payment gateway
    received_at     datetime2     NOT NULL CONSTRAINT df_lnd_payment_received_at DEFAULT SYSDATETIME(),
    CONSTRAINT pk_lnd_payment PRIMARY KEY CLUSTERED (lnd_id)
);
CREATE NONCLUSTERED INDEX ix_lnd_payment_received ON lnd.payment (received_at);
```

## lnd.product.sql

**Path:** `tables/lnd/lnd.product.sql`

```sql
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
```

## lnd.shipment.sql

**Path:** `tables/lnd/lnd.shipment.sql`

```sql
CREATE TABLE lnd.shipment (
    lnd_id           bigint      IDENTITY(1,1) NOT NULL,
    shipment_src_id  varchar(30) NOT NULL,
    payload_xml      xml         NOT NULL,   -- carrier feed document
    received_at      datetime2   NOT NULL CONSTRAINT df_lnd_shipment_received_at DEFAULT SYSDATETIME(),
    CONSTRAINT pk_lnd_shipment PRIMARY KEY CLUSTERED (lnd_id)
);
CREATE NONCLUSTERED INDEX ix_lnd_shipment_received ON lnd.shipment (received_at);
```

## ref.currency_rate.sql

**Path:** `tables/ref/ref.currency_rate.sql`

```sql
CREATE TABLE ref.currency_rate (
    rate_date     date          NOT NULL,
    from_currency char(3)       NOT NULL,
    to_currency   char(3)       NOT NULL,
    rate          decimal(18,8) NOT NULL,
    CONSTRAINT pk_ref_currency_rate PRIMARY KEY CLUSTERED (from_currency, to_currency, rate_date)
);
```

## stg.customer.sql

**Path:** `tables/stg/stg.customer.sql`

```sql
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
```

## stg.order_header.sql

**Path:** `tables/stg/stg.order_header.sql`

```sql
CREATE TABLE stg.order_header (
    order_src_id       varchar(20)   NOT NULL,
    customer_src_id    varchar(20)   NULL,
    order_date         datetime2     NOT NULL,
    order_status       varchar(20)   NOT NULL,
    currency_code      char(3)       NOT NULL,
    channel            varchar(30)   NOT NULL,
    ship_country       char(2)       NULL,
    order_discount_amt decimal(18,2) NOT NULL CONSTRAINT df_stg_order_header_disc DEFAULT 0,
    days_to_land       int           NULL,   -- days between order date and the extract that carried it
    is_late_arriving   bit           NOT NULL CONSTRAINT df_stg_order_header_late DEFAULT 0,
    source_modified_at datetime2     NOT NULL,
    load_batch_id      int           NOT NULL,
    loaded_at          datetime2     NOT NULL CONSTRAINT df_stg_order_header_loaded_at DEFAULT SYSDATETIME(),
    CONSTRAINT pk_stg_order_header PRIMARY KEY CLUSTERED (order_src_id)
);
```

## stg.order_line.sql

**Path:** `tables/stg/stg.order_line.sql`

```sql
CREATE TABLE stg.order_line (
    order_src_id       varchar(20)   NOT NULL,
    line_no            int           NOT NULL,
    product_src_id     varchar(20)   NULL,
    quantity           int           NOT NULL,
    unit_price         decimal(18,4) NULL,
    line_discount_pct  decimal(5,2)  NOT NULL CONSTRAINT df_stg_order_line_disc DEFAULT 0,
    line_type          varchar(10)   NOT NULL,
    source_modified_at datetime2     NOT NULL,
    load_batch_id      int           NOT NULL,
    loaded_at          datetime2     NOT NULL CONSTRAINT df_stg_order_line_loaded_at DEFAULT SYSDATETIME(),
    CONSTRAINT pk_stg_order_line PRIMARY KEY CLUSTERED (order_src_id, line_no)
);
```

## stg.payment.sql

**Path:** `tables/stg/stg.payment.sql`

```sql
CREATE TABLE stg.payment (
    payment_src_id  varchar(30)   NOT NULL,
    order_src_id    varchar(20)   NOT NULL,   -- one row per payment x order allocation
    method          varchar(20)   NULL,
    payment_type    varchar(20)   NULL,       -- CAPTURE / REFUND / CHARGEBACK
    amount          decimal(18,2) NOT NULL,
    currency_code   char(3)       NULL,
    status          varchar(20)   NULL,
    event_ts        datetime2     NULL,
    gateway_ref     varchar(50)   NULL,
    load_batch_id   int           NOT NULL,
    loaded_at       datetime2     NOT NULL CONSTRAINT df_stg_payment_loaded_at DEFAULT SYSDATETIME(),
    CONSTRAINT pk_stg_payment PRIMARY KEY CLUSTERED (payment_src_id, order_src_id)
);
```

## stg.product.sql

**Path:** `tables/stg/stg.product.sql`

```sql
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
```

## stg.shipment.sql

**Path:** `tables/stg/stg.shipment.sql`

```sql
CREATE TABLE stg.shipment (
    shipment_src_id varchar(30)  NOT NULL,
    order_src_id    varchar(20)  NOT NULL,   -- consolidated shipments carry several orders
    carrier         varchar(30)  NULL,
    shipped_ts      datetime2    NULL,
    delivered_ts    datetime2    NULL,
    promised_ts     datetime2    NULL,
    weight_kg       decimal(9,3) NULL,
    load_batch_id   int          NOT NULL,
    loaded_at       datetime2    NOT NULL CONSTRAINT df_stg_shipment_loaded_at DEFAULT SYSDATETIME(),
    CONSTRAINT pk_stg_shipment PRIMARY KEY CLUSTERED (shipment_src_id, order_src_id)
);
```

---

# CONSTRAINTS

_1 file(s)_

## foreign_keys.sql

**Path:** `constraints/foreign_keys.sql`

```sql
ALTER TABLE fact.order_line ADD CONSTRAINT fk_fact_order_line_date     FOREIGN KEY (order_date_key) REFERENCES dim.date (date_key);
ALTER TABLE fact.order_line ADD CONSTRAINT fk_fact_order_line_customer FOREIGN KEY (customer_key)   REFERENCES dim.customer (customer_key);
ALTER TABLE fact.order_line ADD CONSTRAINT fk_fact_order_line_product  FOREIGN KEY (product_key)    REFERENCES dim.product (product_key);

ALTER TABLE fact.payment ADD CONSTRAINT fk_fact_payment_date     FOREIGN KEY (payment_date_key) REFERENCES dim.date (date_key);
ALTER TABLE fact.payment ADD CONSTRAINT fk_fact_payment_customer FOREIGN KEY (customer_key)     REFERENCES dim.customer (customer_key);

ALTER TABLE fact.shipment ADD CONSTRAINT fk_fact_shipment_customer  FOREIGN KEY (customer_key)       REFERENCES dim.customer (customer_key);
ALTER TABLE fact.shipment ADD CONSTRAINT fk_fact_shipment_ship_date FOREIGN KEY (ship_date_key)      REFERENCES dim.date (date_key);
ALTER TABLE fact.shipment ADD CONSTRAINT fk_fact_shipment_deliv_dt  FOREIGN KEY (delivered_date_key) REFERENCES dim.date (date_key);
ALTER TABLE fact.shipment ADD CONSTRAINT fk_fact_shipment_prom_dt   FOREIGN KEY (promised_date_key)  REFERENCES dim.date (date_key);

ALTER TABLE agg.customer_monthly_revenue ADD CONSTRAINT fk_agg_cmr_customer FOREIGN KEY (customer_key) REFERENCES dim.customer (customer_key);
```

---

# VIEWS

_5 file(s)_

## rpt.vw_customer_cohort_retention.sql

**Path:** `views/rpt.vw_customer_cohort_retention.sql`

```sql
CREATE OR ALTER VIEW rpt.vw_customer_cohort_retention
AS
WITH order_months AS (
    SELECT DISTINCT
        cu.customer_src_id,
        DATEFROMPARTS(d.calendar_year, d.month_number, 1) AS order_month
    FROM fact.order_line AS f
    JOIN dim.date        AS d  ON d.date_key      = f.order_date_key
    JOIN dim.customer    AS cu ON cu.customer_key = f.customer_key
    WHERE f.line_type = 'SALE'
      AND f.customer_key > 0
),
cohorts AS (
    SELECT customer_src_id, MIN(order_month) AS cohort_month
    FROM order_months
    GROUP BY customer_src_id
),
cohort_size AS (
    SELECT cohort_month, COUNT(*) AS cohort_customers
    FROM cohorts
    GROUP BY cohort_month
),
activity AS (
    SELECT
        c.cohort_month,
        DATEDIFF(month, c.cohort_month, o.order_month) AS month_offset,
        COUNT(DISTINCT o.customer_src_id)              AS active_customers
    FROM order_months AS o
    JOIN cohorts      AS c ON c.customer_src_id = o.customer_src_id
    GROUP BY c.cohort_month, DATEDIFF(month, c.cohort_month, o.order_month)
)
SELECT
    a.cohort_month,
    a.month_offset,
    s.cohort_customers,
    a.active_customers,
    CAST(100.0 * a.active_customers / s.cohort_customers AS decimal(5,2)) AS retention_pct,
    a.active_customers
        - LAG(a.active_customers) OVER (PARTITION BY a.cohort_month ORDER BY a.month_offset) AS change_vs_prev_month,
    FIRST_VALUE(a.active_customers) OVER (PARTITION BY a.cohort_month ORDER BY a.month_offset) AS month0_customers
FROM activity    AS a
JOIN cohort_size AS s ON s.cohort_month = a.cohort_month;
```

## rpt.vw_customer_current.sql

**Path:** `views/rpt.vw_customer_current.sql`

```sql
CREATE OR ALTER VIEW rpt.vw_customer_current
AS
SELECT
    c.customer_key,
    c.customer_src_id,
    c.full_name,
    c.email,
    c.city,
    c.state_code,
    c.country_code,
    c.customer_segment,
    c.effective_from                                   AS current_since,
    ISNULL(r.lifetime_net_revenue_usd, 0)              AS lifetime_net_revenue_usd,
    dbo.fn_customer_tier(ISNULL(r.lifetime_net_revenue_usd, 0)) AS customer_tier,
    r.last_order_month
FROM dim.customer AS c
JOIN (
    SELECT customer_src_id, MIN(customer_key) AS anchor_key
    FROM dim.customer
    WHERE customer_key > 0
    GROUP BY customer_src_id
) AS anc
  ON anc.customer_src_id = c.customer_src_id
LEFT JOIN (
    SELECT customer_key,
           SUM(net_revenue_usd) AS lifetime_net_revenue_usd,
           MAX(month_start)     AS last_order_month
    FROM agg.customer_monthly_revenue
    GROUP BY customer_key
) AS r
  ON r.customer_key = anc.anchor_key
WHERE c.is_current = 1
  AND c.customer_key > 0;
```

## rpt.vw_customer_revenue.sql

**Path:** `views/rpt.vw_customer_revenue.sql`

```sql
/* Revenue per customer, attributed to the customer's current name regardless of
   which SCD2 version was in force when the order was placed. */
CREATE OR ALTER VIEW rpt.vw_customer_revenue
AS
SELECT
    cur.customer_src_id                                          AS customer_id,
    cur.full_name                                                AS customer_name,
    SUM(f.net_amount_usd)                                        AS revenue,
    SUM(CASE WHEN f.is_return = 0 THEN f.net_amount_usd ELSE 0 END) AS sales_revenue,
    SUM(CASE WHEN f.is_return = 1 THEN f.net_amount_usd ELSE 0 END) AS returns_value,
    COUNT(DISTINCT f.order_src_id)                               AS order_count
FROM fact.order_line AS f
JOIN dim.customer    AS ver ON ver.customer_key    = f.customer_key
JOIN dim.customer    AS cur ON cur.customer_src_id = ver.customer_src_id
                           AND cur.is_current = 1
WHERE f.customer_key > 0
GROUP BY cur.customer_src_id, cur.full_name;
```

## rpt.vw_order_fulfilment_sla.sql

**Path:** `views/rpt.vw_order_fulfilment_sla.sql`

```sql
CREATE OR ALTER VIEW rpt.vw_order_fulfilment_sla
AS
SELECT
    s.shipment_src_id,
    s.order_src_id,
    s.carrier,
    ds.full_date                              AS ship_date,
    dp.full_date                              AS promised_date,
    CASE WHEN s.delivered_date_key > 0 THEN dd.full_date END AS delivered_date,
    s.transit_business_days,
    s.promised_business_days,
    s.delivery_status,
    s.is_sla_breach,
    CASE
        WHEN s.delivered_date_key > 0 AND dd.full_date > dp.full_date
            THEN dbo.fn_business_days(dp.full_date, dd.full_date)
        ELSE 0
    END                                       AS business_days_late,
    CASE
        WHEN s.delivery_status = 'LATE_UNDELIVERED'                       THEN 'OPEN - LATE'
        WHEN s.delivery_status IN ('IN_TRANSIT', 'PENDING')               THEN 'OPEN'
        WHEN s.is_sla_breach = 0                                          THEN 'ON TIME'
        WHEN dbo.fn_business_days(dp.full_date, dd.full_date) <= 2        THEN '1-2 DAYS LATE'
        ELSE '3+ DAYS LATE'
    END                                       AS sla_bucket,
    AVG(CAST(s.is_sla_breach AS decimal(5,4))) OVER (
        PARTITION BY s.carrier, ds.calendar_year, ds.month_number) AS carrier_month_breach_rate
FROM fact.shipment AS s
JOIN dim.date      AS ds ON ds.date_key = s.ship_date_key
JOIN dim.date      AS dp ON dp.date_key = s.promised_date_key
JOIN dim.date      AS dd ON dd.date_key = s.delivered_date_key;
```

## rpt.vw_sales_daily.sql

**Path:** `views/rpt.vw_sales_daily.sql`

```sql
CREATE OR ALTER VIEW rpt.vw_sales_daily
AS
WITH daily AS (
    SELECT
        d.full_date,
        p.category,
        f.ship_country,
        SUM(f.net_amount_usd)          AS net_revenue_usd,
        SUM(f.quantity)                AS units,
        COUNT(DISTINCT f.order_src_id) AS orders
    FROM fact.order_line AS f
    JOIN dim.date    AS d ON d.date_key    = f.order_date_key
    JOIN dim.product AS p ON p.product_key = f.product_key
    GROUP BY d.full_date, p.category, f.ship_country
)
SELECT
    full_date,
    category,
    ship_country,
    net_revenue_usd,
    units,
    orders,
    AVG(net_revenue_usd) OVER (
        PARTITION BY category, ship_country
        ORDER BY full_date
        ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) AS net_revenue_7row_avg_usd,
    SUM(net_revenue_usd) OVER (
        PARTITION BY category, ship_country, YEAR(full_date), MONTH(full_date)
        ORDER BY full_date
        ROWS UNBOUNDED PRECEDING)                 AS month_to_date_usd
FROM daily;
```

---

# FUNCTIONS

_5 file(s)_

## dbo.fn_business_days.sql

**Path:** `functions/dbo.fn_business_days.sql`

```sql
/* Business days elapsed after @start_date up to and including @end_date,
   excluding weekends and rows flagged is_holiday in dim.date.
   Same day = 0. Returns NULL when @end_date < @start_date.
   Migration notes: relies on DATENAME/DATEFIRST (language dependent) and a table lookup
   inside a scalar UDF (row-by-row cost on SQL Server). */
CREATE OR ALTER FUNCTION dbo.fn_business_days (@start_date date, @end_date date)
RETURNS int
AS
BEGIN
    IF @start_date IS NULL OR @end_date IS NULL OR @end_date < @start_date
        RETURN NULL;

    DECLARE @s date = DATEADD(day, 1, @start_date);
    IF @s > @end_date
        RETURN 0;

    DECLARE @days int = DATEDIFF(day, @s, @end_date) + 1;
    DECLARE @weekend_days int =
          (DATEDIFF(week, @s, @end_date) * 2)
        + CASE WHEN DATENAME(weekday, @s)        = 'Sunday'   THEN 1 ELSE 0 END
        + CASE WHEN DATENAME(weekday, @end_date) = 'Saturday' THEN 1 ELSE 0 END;

    DECLARE @holidays int;
    SELECT @holidays = COUNT(*)
    FROM dim.date d
    WHERE d.full_date BETWEEN @s AND @end_date
      AND d.is_holiday = 1
      AND d.is_weekend = 0;

    RETURN @days - @weekend_days - ISNULL(@holidays, 0);
END
```

## dbo.fn_clean_name.sql

**Path:** `functions/dbo.fn_clean_name.sql`

```sql
/* Trims, collapses repeated spaces and proper-cases a person name.
   Migration notes: WHILE loop character processing in a scalar UDF. */
CREATE OR ALTER FUNCTION dbo.fn_clean_name (@name nvarchar(200))
RETURNS nvarchar(200)
AS
BEGIN
    IF @name IS NULL
        RETURN NULL;

    DECLARE @s nvarchar(200) = LTRIM(RTRIM(@name));
    WHILE CHARINDEX('  ', @s) > 0
        SET @s = REPLACE(@s, '  ', ' ');

    DECLARE @i int = 1;
    DECLARE @len int = LEN(@s);
    DECLARE @out nvarchar(200) = N'';
    DECLARE @c nchar(1);
    DECLARE @prev nchar(1) = N' ';

    WHILE @i <= @len
    BEGIN
        SET @c = SUBSTRING(@s, @i, 1);
        SET @out = @out + CASE WHEN @prev IN (N' ', N'-', N'''') THEN UPPER(@c) ELSE LOWER(@c) END;
        SET @prev = @c;
        SET @i += 1;
    END

    RETURN NULLIF(@out, N'');
END
```

## dbo.fn_convert_currency.sql

**Path:** `functions/dbo.fn_convert_currency.sql`

```sql
/* Converts an amount to USD using the latest rate on or before @rate_date.
   Returns NULL when no rate exists (callers treat that as a reject). */
CREATE OR ALTER FUNCTION dbo.fn_convert_currency (@amount decimal(18,4), @from_currency char(3), @rate_date date)
RETURNS decimal(18,4)
AS
BEGIN
    IF @amount IS NULL
        RETURN NULL;
    IF @from_currency = 'USD'
        RETURN @amount;

    DECLARE @rate decimal(18,8);
    SELECT TOP (1) @rate = r.rate
    FROM ref.currency_rate r
    WHERE r.from_currency = @from_currency
      AND r.to_currency   = 'USD'
      AND r.rate_date    <= @rate_date
    ORDER BY r.rate_date DESC;

    RETURN CASE WHEN @rate IS NULL THEN NULL ELSE ROUND(@amount * @rate, 4) END;
END
```

## dbo.fn_customer_tier.sql

**Path:** `functions/dbo.fn_customer_tier.sql`

```sql
CREATE OR ALTER FUNCTION dbo.fn_customer_tier (@net_revenue_usd decimal(18,2))
RETURNS varchar(10)
AS
BEGIN
    RETURN CASE
               WHEN @net_revenue_usd >= 10000 THEN 'PLATINUM'
               WHEN @net_revenue_usd >=  5000 THEN 'GOLD'
               WHEN @net_revenue_usd >=  1000 THEN 'SILVER'
               WHEN @net_revenue_usd >      0 THEN 'BRONZE'
               ELSE 'NONE'
           END;
END
```

## dbo.fn_fiscal_period.sql

**Path:** `functions/dbo.fn_fiscal_period.sql`

```sql
/* Inline table-valued function. Fiscal year starts 1 April and is named for the
   calendar year in which it ends (April 2025 -> FY2026, period 1). */
CREATE OR ALTER FUNCTION dbo.fn_fiscal_period (@d date)
RETURNS TABLE
AS
RETURN
(
    SELECT
        CAST(YEAR(@d) + CASE WHEN MONTH(@d) >= 4 THEN 1 ELSE 0 END AS smallint) AS fiscal_year,
        CAST(((MONTH(@d) + 8) % 12) / 3 + 1 AS tinyint)                          AS fiscal_quarter,
        CAST(((MONTH(@d) + 8) % 12) + 1 AS tinyint)                              AS fiscal_period
);
```

---

# PROCEDURES

_16 file(s)_

## agg.usp_refresh_customer_monthly_revenue.sql

**Path:** `procedures/agg/agg.usp_refresh_customer_monthly_revenue.sql`

```sql
/* ============================================================================
   agg.usp_refresh_customer_monthly_revenue   (EXTREME)
   1. Rebuilds a rolling window of customer x month revenue (delete + reinsert).
   2. Walks the monthly rows with a CURSOR, maintaining a running lifetime value per customer
      (seeded from the last month before the window) and inserting one row at a time.
      A set-based rewrite is SUM() OVER (PARTITION BY customer ORDER BY month).
   3. Builds a trailing-N-month pivot with DYNAMIC SQL (column list derived from the data),
      lands it in a GLOBAL temp table, then materialises agg.customer_revenue_trailing via SELECT INTO.
   ============================================================================ */
CREATE OR ALTER PROCEDURE agg.usp_refresh_customer_monthly_revenue
    @batch_id      int,
    @months_back   int = 24,
    @pivot_months  int = 12
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    DECLARE @proc sysname = OBJECT_SCHEMA_NAME(@@PROCID) + N'.' + OBJECT_NAME(@@PROCID);
    DECLARE @start datetime2 = SYSDATETIME();
    DECLARE @today date = CAST(SYSDATETIME() AS date);
    DECLARE @window_start date = DATEFROMPARTS(YEAR(DATEADD(month, -@months_back, @today)),
                                               MONTH(DATEADD(month, -@months_back, @today)), 1);
    DECLARE @pivot_from date  = DATEADD(month, -(@pivot_months - 1), DATEFROMPARTS(YEAR(@today), MONTH(@today), 1));

    DECLARE @cust int, @month date, @orders int, @sales decimal(18,2), @ret decimal(18,2), @net decimal(18,2);
    DECLARE @prev_cust int = NULL, @run_net decimal(18,2) = 0, @run_orders int = 0;
    DECLARE @rows_read int, @rows_ins int = 0;
    DECLARE @cols nvarchar(max), @select_cols nvarchar(max), @sql nvarchar(max);
    DECLARE @err_no int, @err_msg nvarchar(4000);

    BEGIN TRY
        CREATE TABLE #monthly (
            customer_key      int           NOT NULL,
            month_start       date          NOT NULL,
            order_count       int           NOT NULL,
            sales_revenue_usd decimal(18,2) NOT NULL,
            returns_usd       decimal(18,2) NOT NULL,
            net_revenue_usd   decimal(18,2) NOT NULL,
            PRIMARY KEY (customer_key, month_start)
        );

        -- customer_key in the aggregate is the customer's ANCHOR key: the first surrogate key issued for the
        -- customer_src_id. It never changes, so revenue and lifetime value follow the customer across SCD2 versions.
        INSERT INTO #monthly
        SELECT anc.anchor_key,
               DATEFROMPARTS(d.calendar_year, d.month_number, 1),
               COUNT(DISTINCT CASE WHEN f.line_type = 'SALE' THEN f.order_src_id END),
               SUM(CASE WHEN f.line_type = 'SALE'   THEN f.net_amount_usd ELSE 0 END),
               SUM(CASE WHEN f.line_type = 'RETURN' THEN f.net_amount_usd ELSE 0 END),
               SUM(f.net_amount_usd)
        FROM fact.order_line AS f
        JOIN dim.date        AS d   ON d.date_key      = f.order_date_key
        JOIN dim.customer    AS ver ON ver.customer_key = f.customer_key
        JOIN (SELECT customer_src_id, MIN(customer_key) AS anchor_key
              FROM dim.customer
              WHERE customer_key > 0
              GROUP BY customer_src_id) AS anc
          ON anc.customer_src_id = ver.customer_src_id
        WHERE f.customer_key > 0
          AND d.full_date >= @window_start
        GROUP BY anc.anchor_key, DATEFROMPARTS(d.calendar_year, d.month_number, 1);

        SET @rows_read = @@ROWCOUNT;

        DECLARE cur_monthly CURSOR LOCAL FAST_FORWARD FOR
            SELECT customer_key, month_start, order_count, sales_revenue_usd, returns_usd, net_revenue_usd
            FROM #monthly
            ORDER BY customer_key, month_start;

        BEGIN TRANSACTION;

            DELETE FROM agg.customer_monthly_revenue WHERE month_start >= @window_start;

            OPEN cur_monthly;
            FETCH NEXT FROM cur_monthly INTO @cust, @month, @orders, @sales, @ret, @net;

            WHILE @@FETCH_STATUS = 0
            BEGIN
                IF @prev_cust IS NULL OR @prev_cust <> @cust
                BEGIN
                    SET @prev_cust  = @cust;
                    SET @run_net    = 0;
                    SET @run_orders = 0;

                    -- opening balance = last month before the rebuilt window
                    SELECT TOP (1) @run_net = a.cumulative_net_revenue_usd, @run_orders = a.cumulative_order_count
                    FROM agg.customer_monthly_revenue AS a
                    WHERE a.customer_key = @cust
                      AND a.month_start < @window_start
                    ORDER BY a.month_start DESC;
                END

                SET @run_net    = @run_net + @net;
                SET @run_orders = @run_orders + @orders;

                INSERT INTO agg.customer_monthly_revenue
                    (customer_key, month_start, order_count, sales_revenue_usd, returns_usd, net_revenue_usd,
                     cumulative_net_revenue_usd, cumulative_order_count, customer_tier, load_batch_id)
                VALUES
                    (@cust, @month, @orders, @sales, @ret, @net,
                     @run_net, @run_orders, dbo.fn_customer_tier(@run_net), @batch_id);

                SET @rows_ins = @rows_ins + 1;

                FETCH NEXT FROM cur_monthly INTO @cust, @month, @orders, @sales, @ret, @net;
            END

            CLOSE cur_monthly;
            DEALLOCATE cur_monthly;

        COMMIT TRANSACTION;

        ---------------------------------------------------------------- dynamic pivot
        SELECT @cols = STRING_AGG(CAST(QUOTENAME(m.ym) AS nvarchar(max)), N',') WITHIN GROUP (ORDER BY m.ym),
               @select_cols = STRING_AGG(CAST(N'ISNULL(pv.' + QUOTENAME(m.ym) + N', 0) AS ' + QUOTENAME(m.ym) AS nvarchar(max)), N',')
                              WITHIN GROUP (ORDER BY m.ym)
        FROM (SELECT DISTINCT CONVERT(char(7), month_start, 120) AS ym
              FROM agg.customer_monthly_revenue
              WHERE month_start >= @pivot_from) AS m;

        IF @cols IS NOT NULL
        BEGIN
            SET @sql = N'SELECT pv.customer_key, ' + @select_cols + N'
                         INTO ##customer_revenue_pivot
                         FROM (SELECT customer_key, CONVERT(char(7), month_start, 120) AS ym, net_revenue_usd
                               FROM agg.customer_monthly_revenue
                               WHERE month_start >= @pivot_from) AS src
                         PIVOT (SUM(net_revenue_usd) FOR ym IN (' + @cols + N')) AS pv;';

            IF OBJECT_ID('tempdb..##customer_revenue_pivot') IS NOT NULL
                DROP TABLE ##customer_revenue_pivot;

            EXEC sp_executesql @sql, N'@pivot_from date', @pivot_from = @pivot_from;

            IF OBJECT_ID('agg.customer_revenue_trailing', 'U') IS NOT NULL
                DROP TABLE agg.customer_revenue_trailing;

            SELECT * INTO agg.customer_revenue_trailing FROM ##customer_revenue_pivot;

            DROP TABLE ##customer_revenue_pivot;
        END

        EXEC etl.usp_write_audit @batch_id = @batch_id, @procedure_name = @proc, @step_name = 'refresh agg.customer_monthly_revenue',
             @start_time = @start, @status = 'SUCCESS', @rows_read = @rows_read, @rows_inserted = @rows_ins;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        IF CURSOR_STATUS('local', 'cur_monthly') > -3
        BEGIN
            IF CURSOR_STATUS('local', 'cur_monthly') >= 0 CLOSE cur_monthly;
            DEALLOCATE cur_monthly;
        END
        SET @err_no = ERROR_NUMBER();
        SET @err_msg = ERROR_MESSAGE();
        EXEC etl.usp_write_audit @batch_id = @batch_id, @procedure_name = @proc, @step_name = 'refresh agg.customer_monthly_revenue',
             @start_time = @start, @status = 'FAILED', @error_number = @err_no, @error_message = @err_msg;
        THROW;
    END CATCH
END
```

## dim.usp_load_dim_customer.sql

**Path:** `procedures/dim/dim.usp_load_dim_customer.sql`

```sql
/* SCD Type 2 using the MERGE ... OUTPUT INTO #changes + follow-up INSERT pattern.
   - New customers get effective_from = 1900-01-01 (history-safe for late-arriving facts).
   - Changed customers: the open row is closed at @as_of_date - 1 and a new open row starts at @as_of_date.
   - A change detected on the same day the open row started is picked up on the next run
     (closing it would produce effective_to < effective_from). */
CREATE OR ALTER PROCEDURE dim.usp_load_dim_customer
    @batch_id   int,
    @as_of_date date = NULL
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    DECLARE @proc sysname = OBJECT_SCHEMA_NAME(@@PROCID) + N'.' + OBJECT_NAME(@@PROCID);
    DECLARE @start datetime2 = SYSDATETIME();
    DECLARE @rows_read int, @ins int, @upd int, @err_no int, @err_msg nvarchar(4000);

    SET @as_of_date = ISNULL(@as_of_date, CAST(SYSDATETIME() AS date));

    BEGIN TRY
        CREATE TABLE #src (
            customer_src_id  varchar(20)   NOT NULL PRIMARY KEY,
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
            row_hash         binary(32)    NOT NULL
        );

        CREATE TABLE #changes (
            action_name      nvarchar(10)  NOT NULL,
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
            row_hash         binary(32)    NOT NULL
        );

        -- CONCAT with explicit ISNULL: CONCAT_WS would silently drop NULLs and weaken the hash.
        INSERT INTO #src
        SELECT s.customer_src_id, s.first_name, s.last_name, s.full_name, s.email, s.phone, s.address_line,
               s.city, s.state_code, s.country_code, s.customer_segment,
               HASHBYTES('SHA2_256', CONCAT(
                   ISNULL(s.first_name, N''), N'|', ISNULL(s.last_name, N''), N'|', ISNULL(s.full_name, N''), N'|',
                   ISNULL(s.email, ''), N'|', ISNULL(s.phone, ''), N'|', ISNULL(s.address_line, N''), N'|',
                   ISNULL(s.city, N''), N'|', ISNULL(s.state_code, ''), N'|', ISNULL(s.country_code, ''), N'|',
                   ISNULL(s.customer_segment, '')))
        FROM stg.customer AS s;

        SET @rows_read = @@ROWCOUNT;

        BEGIN TRANSACTION;

            MERGE dim.customer AS t
            USING #src AS s
               ON t.customer_src_id = s.customer_src_id
              AND t.is_current = 1
            WHEN MATCHED AND t.row_hash <> s.row_hash AND t.effective_from < @as_of_date THEN
                UPDATE SET
                    t.effective_to = DATEADD(day, -1, @as_of_date),
                    t.is_current   = 0,
                    t.updated_at   = SYSDATETIME()
            WHEN NOT MATCHED BY TARGET THEN
                INSERT (customer_src_id, first_name, last_name, full_name, email, phone, address_line, city,
                        state_code, country_code, customer_segment, row_hash, effective_from, effective_to, is_current)
                VALUES (s.customer_src_id, s.first_name, s.last_name, s.full_name, s.email, s.phone, s.address_line, s.city,
                        s.state_code, s.country_code, s.customer_segment, s.row_hash, '1900-01-01', '9999-12-31', 1)
            OUTPUT $action, s.customer_src_id, s.first_name, s.last_name, s.full_name, s.email, s.phone, s.address_line,
                   s.city, s.state_code, s.country_code, s.customer_segment, s.row_hash
            INTO #changes (action_name, customer_src_id, first_name, last_name, full_name, email, phone, address_line,
                           city, state_code, country_code, customer_segment, row_hash);

            -- Second half of SCD2: open a new version for every customer whose current row was just closed.
            INSERT INTO dim.customer
                (customer_src_id, first_name, last_name, full_name, email, phone, address_line, city,
                 state_code, country_code, customer_segment, row_hash, effective_from, effective_to, is_current)
            SELECT c.customer_src_id, c.first_name, c.last_name, c.full_name, c.email, c.phone, c.address_line, c.city,
                   c.state_code, c.country_code, c.customer_segment, c.row_hash, @as_of_date, '9999-12-31', 1
            FROM #changes AS c
            WHERE c.action_name = 'UPDATE';

        COMMIT TRANSACTION;

        SELECT @ins = COUNT(*) FROM #changes WHERE action_name = 'INSERT';
        SELECT @upd = COUNT(*) FROM #changes WHERE action_name = 'UPDATE';

        EXEC etl.usp_write_audit @batch_id = @batch_id, @procedure_name = @proc, @step_name = 'merge dim.customer (SCD2)',
             @start_time = @start, @status = 'SUCCESS', @rows_read = @rows_read, @rows_inserted = @ins, @rows_updated = @upd;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        SET @err_no = ERROR_NUMBER();
        SET @err_msg = ERROR_MESSAGE();
        EXEC etl.usp_write_audit @batch_id = @batch_id, @procedure_name = @proc, @step_name = 'merge dim.customer (SCD2)',
             @start_time = @start, @status = 'FAILED', @error_number = @err_no, @error_message = @err_msg;
        THROW;
    END CATCH
END
```

## dim.usp_load_dim_date.sql

**Path:** `procedures/dim/dim.usp_load_dim_date.sql`

```sql
/* Generates the calendar with a recursive CTE, then flags US Thanksgiving with a WHILE loop.
   Migration notes: SET DATEFIRST dependence, MAXRECURSION hint, procedural holiday loop. */
CREATE OR ALTER PROCEDURE dim.usp_load_dim_date
    @batch_id   int,
    @start_date date = '2015-01-01',
    @end_date   date = '2035-12-31'
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    SET DATEFIRST 7;   -- Sunday = 1; day_of_week and is_weekend depend on this

    DECLARE @proc sysname = OBJECT_SCHEMA_NAME(@@PROCID) + N'.' + OBJECT_NAME(@@PROCID);
    DECLARE @start datetime2 = SYSDATETIME();
    DECLARE @rows_ins int, @err_no int, @err_msg nvarchar(4000);
    DECLARE @y int = YEAR(@start_date), @last_y int = YEAR(@end_date);
    DECLARE @first_of_nov date, @offset int, @thanksgiving date;

    BEGIN TRY
        IF @end_date < @start_date
            THROW 50040, 'end_date must not be earlier than start_date.', 1;

        ;WITH cal AS (
            SELECT @start_date AS dt
            UNION ALL
            SELECT DATEADD(day, 1, dt) FROM cal WHERE dt < @end_date
        )
        INSERT INTO dim.date
            (date_key, full_date, day_of_week, day_name, day_of_month, day_of_year, iso_week,
             month_number, month_name, quarter_number, calendar_year, is_weekend, is_holiday,
             fiscal_year, fiscal_quarter, fiscal_period)
        SELECT
            CONVERT(int, CONVERT(char(8), cal.dt, 112)),
            cal.dt,
            DATEPART(weekday, cal.dt),
            DATENAME(weekday, cal.dt),
            DAY(cal.dt),
            DATEPART(dayofyear, cal.dt),
            DATEPART(iso_week, cal.dt),
            MONTH(cal.dt),
            DATENAME(month, cal.dt),
            DATEPART(quarter, cal.dt),
            YEAR(cal.dt),
            CASE WHEN DATEPART(weekday, cal.dt) IN (1, 7) THEN 1 ELSE 0 END,
            CASE WHEN (MONTH(cal.dt) = 1 AND DAY(cal.dt) = 1) OR (MONTH(cal.dt) = 12 AND DAY(cal.dt) = 25) THEN 1 ELSE 0 END,
            fp.fiscal_year,
            fp.fiscal_quarter,
            fp.fiscal_period
        FROM cal
        CROSS APPLY dbo.fn_fiscal_period(cal.dt) AS fp
        WHERE NOT EXISTS (SELECT 1 FROM dim.date AS x WHERE x.full_date = cal.dt)
        OPTION (MAXRECURSION 0);

        SET @rows_ins = @@ROWCOUNT;

        WHILE @y <= @last_y
        BEGIN
            SET @first_of_nov = DATEFROMPARTS(@y, 11, 1);
            SET @offset       = (5 - DATEPART(weekday, @first_of_nov) + 7) % 7;   -- days until first Thursday
            SET @thanksgiving = DATEADD(day, @offset + 21, @first_of_nov);        -- fourth Thursday

            UPDATE dim.date
            SET is_holiday = 1
            WHERE full_date = @thanksgiving
              AND is_holiday = 0;

            SET @y += 1;
        END

        EXEC etl.usp_write_audit @batch_id = @batch_id, @procedure_name = @proc, @step_name = 'load dim.date',
             @start_time = @start, @status = 'SUCCESS', @rows_inserted = @rows_ins;
    END TRY
    BEGIN CATCH
        SET @err_no = ERROR_NUMBER();
        SET @err_msg = ERROR_MESSAGE();
        EXEC etl.usp_write_audit @batch_id = @batch_id, @procedure_name = @proc, @step_name = 'load dim.date',
             @start_time = @start, @status = 'FAILED', @error_number = @err_no, @error_message = @err_msg;
        THROW;
    END CATCH
END
```

## dim.usp_load_dim_product.sql

**Path:** `procedures/dim/dim.usp_load_dim_product.sql`

```sql
/* SCD Type 1 via MERGE, with soft delete for products that disappear from the source. */
CREATE OR ALTER PROCEDURE dim.usp_load_dim_product
    @batch_id int
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    DECLARE @proc sysname = OBJECT_SCHEMA_NAME(@@PROCID) + N'.' + OBJECT_NAME(@@PROCID);
    DECLARE @start datetime2 = SYSDATETIME();
    DECLARE @rows_read int, @ins int, @upd int, @err_no int, @err_msg nvarchar(4000);

    BEGIN TRY
        SELECT @rows_read = COUNT(*) FROM stg.product;

        -- Guard: an empty staging table would otherwise soft-delete the whole dimension.
        IF @rows_read = 0
            THROW 50020, 'stg.product is empty; refusing to deactivate the entire product dimension.', 1;

        CREATE TABLE #merge_log (
            action_name nvarchar(10) NOT NULL,
            product_key int          NOT NULL
        );

        MERGE dim.product AS t
        USING stg.product AS s
           ON t.product_src_id = s.product_src_id
        WHEN MATCHED AND (
                   ISNULL(t.product_name, '') <> ISNULL(s.product_name, '')
                OR ISNULL(t.category, '')     <> ISNULL(s.category, '')
                OR ISNULL(t.subcategory, '')  <> ISNULL(s.subcategory, '')
                OR ISNULL(t.brand, '')        <> ISNULL(s.brand, '')
                OR ISNULL(t.list_price, -1)   <> ISNULL(s.list_price, -1)
                OR ISNULL(t.unit_cost, -1)    <> ISNULL(s.unit_cost, -1)
                OR ISNULL(t.status, '')       <> ISNULL(s.status, '')
                OR t.is_active                <> IIF(s.status = 'ACTIVE', 1, 0)
             ) THEN
            UPDATE SET
                t.product_name = s.product_name,
                t.category     = s.category,
                t.subcategory  = s.subcategory,
                t.brand        = s.brand,
                t.list_price   = s.list_price,
                t.unit_cost    = s.unit_cost,
                t.status       = s.status,
                t.is_active    = IIF(s.status = 'ACTIVE', 1, 0),
                t.updated_at   = SYSDATETIME()
        WHEN NOT MATCHED BY TARGET THEN
            INSERT (product_src_id, product_name, category, subcategory, brand, list_price, unit_cost, status, is_active)
            VALUES (s.product_src_id, s.product_name, s.category, s.subcategory, s.brand, s.list_price, s.unit_cost,
                    s.status, IIF(s.status = 'ACTIVE', 1, 0))
        WHEN NOT MATCHED BY SOURCE AND t.product_key > 0 AND t.is_active = 1 THEN
            UPDATE SET t.is_active = 0, t.updated_at = SYSDATETIME()
        OUTPUT $action, inserted.product_key INTO #merge_log (action_name, product_key);

        SELECT @ins = COUNT(*) FROM #merge_log WHERE action_name = 'INSERT';
        SELECT @upd = COUNT(*) FROM #merge_log WHERE action_name = 'UPDATE';

        EXEC etl.usp_write_audit @batch_id = @batch_id, @procedure_name = @proc, @step_name = 'merge dim.product (SCD1)',
             @start_time = @start, @status = 'SUCCESS', @rows_read = @rows_read, @rows_inserted = @ins, @rows_updated = @upd;
    END TRY
    BEGIN CATCH
        SET @err_no = ERROR_NUMBER();
        SET @err_msg = ERROR_MESSAGE();
        EXEC etl.usp_write_audit @batch_id = @batch_id, @procedure_name = @proc, @step_name = 'merge dim.product (SCD1)',
             @start_time = @start, @status = 'FAILED', @error_number = @err_no, @error_message = @err_msg;
        THROW;
    END CATCH
END
```

## etl.usp_get_set_watermark.sql

**Path:** `procedures/etl/etl.usp_get_set_watermark.sql`

```sql
CREATE OR ALTER PROCEDURE etl.usp_get_set_watermark
    @source_name   varchar(100),
    @new_value     datetime2 = NULL,
    @current_value datetime2 = NULL OUTPUT
AS
BEGIN
    SET NOCOUNT ON;

    IF NOT EXISTS (SELECT 1 FROM etl.watermark WHERE source_name = @source_name)
        INSERT INTO etl.watermark (source_name, last_value) VALUES (@source_name, '1900-01-01');

    SELECT @current_value = last_value
    FROM etl.watermark
    WHERE source_name = @source_name;

    IF @new_value IS NOT NULL AND @new_value > @current_value
    BEGIN
        UPDATE etl.watermark
        SET last_value = @new_value,
            updated_at = SYSDATETIME()
        WHERE source_name = @source_name;

        IF @@ROWCOUNT <> 1
            THROW 50010, 'Watermark update did not affect exactly one row.', 1;

        SET @current_value = @new_value;
    END
END
```

## etl.usp_rebuild_indexes.sql

**Path:** `procedures/etl/etl.usp_rebuild_indexes.sql`

```sql
/* Index maintenance driven by sys.dm_db_index_physical_stats, executed through a cursor and dynamic ALTER INDEX.
   Intended as a "retire, do not migrate" case: Snowflake has no user-managed indexes. */
CREATE OR ALTER PROCEDURE etl.usp_rebuild_indexes
    @reorganize_pct float = 10.0,
    @rebuild_pct    float = 30.0,
    @min_pages      int   = 1000,
    @dry_run        bit   = 1
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @schema_name sysname, @table_name sysname, @index_name sysname, @frag float, @sql nvarchar(max);

    DECLARE cur_idx CURSOR LOCAL FAST_FORWARD FOR
        SELECT s.name, t.name, i.name, ps.avg_fragmentation_in_percent
        FROM sys.dm_db_index_physical_stats(DB_ID(), NULL, NULL, NULL, 'LIMITED') AS ps
        JOIN sys.indexes AS i ON i.object_id = ps.object_id AND i.index_id = ps.index_id
        JOIN sys.tables  AS t ON t.object_id = ps.object_id
        JOIN sys.schemas AS s ON s.schema_id = t.schema_id
        WHERE ps.index_id > 0
          AND ps.page_count >= @min_pages
          AND ps.avg_fragmentation_in_percent >= @reorganize_pct
        ORDER BY ps.avg_fragmentation_in_percent DESC;

    OPEN cur_idx;
    FETCH NEXT FROM cur_idx INTO @schema_name, @table_name, @index_name, @frag;

    WHILE @@FETCH_STATUS = 0
    BEGIN
        SET @sql = N'ALTER INDEX ' + QUOTENAME(@index_name) + N' ON ' + QUOTENAME(@schema_name) + N'.' + QUOTENAME(@table_name)
                 + CASE WHEN @frag >= @rebuild_pct THEN N' REBUILD WITH (ONLINE = ON, SORT_IN_TEMPDB = ON);'
                        ELSE N' REORGANIZE;' END;

        IF @dry_run = 1
            PRINT @sql;
        ELSE
            EXEC sp_executesql @sql;

        FETCH NEXT FROM cur_idx INTO @schema_name, @table_name, @index_name, @frag;
    END

    CLOSE cur_idx;
    DEALLOCATE cur_idx;
END
```

## etl.usp_run_daily_load.sql

**Path:** `procedures/etl/etl.usp_run_daily_load.sql`

```sql
/* ============================================================================
   etl.usp_run_daily_load   (EXTREME - orchestration, not transformation)
   - Single-instance guard via sp_getapplock.
   - Steps come from etl.pipeline_step and are invoked through dynamic SQL; @only_steps / @skip_steps
     (comma lists of step_name) filter them at run time.
   - Per-step retry loop for transient errors (deadlock, lock timeout, timeout) using WAITFOR DELAY.
   - Nested TRY/CATCH, XACT_STATE handling, INSERT ... EXEC to capture a post-step row count.
   - Every exit path writes a RUN_SUMMARY audit row and releases the applock.
   ============================================================================ */
CREATE OR ALTER PROCEDURE etl.usp_run_daily_load
    @only_steps    varchar(500) = NULL,
    @skip_steps    varchar(500) = NULL,
    @max_retries   int          = NULL,      -- overrides etl.pipeline_step.max_retries when supplied
    @retry_delay   char(8)      = '00:00:30',
    @stop_on_error bit          = 1
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @proc sysname = OBJECT_SCHEMA_NAME(@@PROCID) + N'.' + OBJECT_NAME(@@PROCID);
    DECLARE @start datetime2 = SYSDATETIME();
    DECLARE @batch_id int = NEXT VALUE FOR etl.seq_batch_id;
    DECLARE @lock_result int, @lock_held bit = 0;
    DECLARE @final_status varchar(20) = 'SUCCESS', @failed_steps int = 0, @steps_run int = 0;
    DECLARE @step_order int, @step_name varchar(100), @proc_name nvarchar(300), @target_table nvarchar(300);
    DECLARE @step_retries int, @continue_on_error bit;
    DECLARE @attempt int, @max_attempts int, @ok bit, @step_start datetime2;
    DECLARE @sql nvarchar(max), @cnt_sql nvarchar(max), @target_rows bigint;
    DECLARE @err_no int, @err_msg nvarchar(4000);

    CREATE TABLE #steps (
        step_order        int           NOT NULL PRIMARY KEY,
        step_name         varchar(100)  NOT NULL,
        proc_name         nvarchar(300) NOT NULL,
        target_table      nvarchar(300) NULL,
        max_retries       int           NOT NULL,
        continue_on_error bit           NOT NULL,
        processed         bit           NOT NULL DEFAULT 0
    );
    CREATE TABLE #row_counts (row_count bigint NOT NULL);

    BEGIN TRY
        EXEC @lock_result = sp_getapplock @Resource = 'etl.usp_run_daily_load', @LockMode = 'Exclusive',
                                          @LockOwner = 'Session', @LockTimeout = 0;
        IF @lock_result < 0
            THROW 50100, 'Another daily load is already running.', 1;
        SET @lock_held = 1;

        INSERT INTO #steps (step_order, step_name, proc_name, target_table, max_retries, continue_on_error)
        SELECT s.step_order, s.step_name, s.proc_name, s.target_table, s.max_retries, s.continue_on_error
        FROM etl.pipeline_step AS s
        WHERE s.is_enabled = 1
          AND (@only_steps IS NULL OR s.step_name IN (SELECT LTRIM(RTRIM(value)) FROM STRING_SPLIT(@only_steps, ',')))
          AND (@skip_steps IS NULL OR s.step_name NOT IN (SELECT LTRIM(RTRIM(value)) FROM STRING_SPLIT(@skip_steps, ',')));

        IF EXISTS (SELECT 1 FROM #steps WHERE OBJECT_ID(proc_name, 'P') IS NULL)
            THROW 50101, 'pipeline_step references a procedure that does not exist.', 1;

        WHILE EXISTS (SELECT 1 FROM #steps WHERE processed = 0)
        BEGIN
            SELECT TOP (1)
                   @step_order = step_order, @step_name = step_name, @proc_name = proc_name,
                   @target_table = target_table, @step_retries = max_retries, @continue_on_error = continue_on_error
            FROM #steps
            WHERE processed = 0
            ORDER BY step_order;

            UPDATE #steps SET processed = 1 WHERE step_order = @step_order;

            SET @steps_run     = @steps_run + 1;
            SET @max_attempts  = ISNULL(@max_retries, @step_retries) + 1;
            SET @attempt       = 0;
            SET @ok            = 0;
            SET @step_start    = SYSDATETIME();
            SET @sql           = N'EXEC ' + @proc_name + N' @batch_id = @batch_id;';

            WHILE @attempt < @max_attempts AND @ok = 0
            BEGIN
                SET @attempt = @attempt + 1;

                BEGIN TRY
                    EXEC sp_executesql @sql, N'@batch_id int', @batch_id = @batch_id;
                    SET @ok = 1;
                END TRY
                BEGIN CATCH
                    SET @err_no  = ERROR_NUMBER();
                    SET @err_msg = LEFT(ERROR_MESSAGE(), 4000);

                    IF XACT_STATE() <> 0
                        ROLLBACK TRANSACTION;

                    EXEC etl.usp_write_audit @batch_id = @batch_id, @procedure_name = @proc, @step_name = @step_name,
                         @start_time = @step_start, @status = 'ATTEMPT_FAILED',
                         @error_number = @err_no, @error_message = @err_msg;

                    IF @err_no IN (1205, 1222, -2, 40001) AND @attempt < @max_attempts   -- deadlock / lock timeout / timeout
                        WAITFOR DELAY @retry_delay;
                    ELSE
                        SET @attempt = @max_attempts;   -- not transient (or out of attempts): stop retrying
                END CATCH
            END

            IF @ok = 0
            BEGIN
                SET @failed_steps = @failed_steps + 1;
                SET @final_status = 'FAILED';

                EXEC etl.usp_write_audit @batch_id = @batch_id, @procedure_name = @proc, @step_name = @step_name,
                     @start_time = @step_start, @status = 'FAILED', @error_number = @err_no, @error_message = @err_msg;

                IF @stop_on_error = 1 AND @continue_on_error = 0
                    BREAK;
            END
            ELSE IF @target_table IS NOT NULL
            BEGIN
                DELETE FROM #row_counts;
                SET @cnt_sql = N'SELECT COUNT_BIG(*) FROM ' + @target_table + N';';
                INSERT INTO #row_counts (row_count) EXEC sp_executesql @cnt_sql;
                SELECT @target_rows = row_count FROM #row_counts;

                EXEC etl.usp_write_audit @batch_id = @batch_id, @procedure_name = @proc, @step_name = @step_name,
                     @start_time = @step_start, @status = 'SUCCESS', @target_row_count = @target_rows;
            END
        END
    END TRY
    BEGIN CATCH
        SET @final_status = 'FAILED';
        SET @err_no  = ERROR_NUMBER();
        SET @err_msg = LEFT(ERROR_MESSAGE(), 4000);
        IF @@TRANCOUNT > 0
            ROLLBACK TRANSACTION;
    END CATCH

    -- Single exit path: release the lock, write the summary, then surface failure to the caller.
    IF @lock_held = 1
        EXEC sp_releaseapplock @Resource = 'etl.usp_run_daily_load', @LockOwner = 'Session';

    IF @final_status = 'SUCCESS'
    BEGIN
        SET @err_no  = NULL;     -- clear errors from attempts that succeeded on retry
        SET @err_msg = NULL;
    END

    EXEC etl.usp_write_audit @batch_id = @batch_id, @procedure_name = @proc, @step_name = 'RUN_SUMMARY',
         @start_time = @start, @status = @final_status, @rows_read = @steps_run, @rows_rejected = @failed_steps,
         @error_number = @err_no, @error_message = @err_msg;

    IF @final_status = 'FAILED'
        RAISERROR('Daily load failed for batch %d. See etl.load_audit for details.', 16, 1, @batch_id);
END
```

## etl.usp_write_audit.sql

**Path:** `procedures/etl/etl.usp_write_audit.sql`

```sql
CREATE OR ALTER PROCEDURE etl.usp_write_audit
    @batch_id         int,
    @procedure_name   sysname,
    @step_name        varchar(100),
    @start_time       datetime2,
    @status           varchar(20),
    @rows_read        int            = NULL,
    @rows_inserted    int            = NULL,
    @rows_updated     int            = NULL,
    @rows_rejected    int            = NULL,
    @target_row_count bigint         = NULL,
    @error_number     int            = NULL,
    @error_message    nvarchar(4000) = NULL,
    @audit_id         bigint         = NULL OUTPUT
AS
BEGIN
    SET NOCOUNT ON;

    INSERT INTO etl.load_audit
        (batch_id, procedure_name, step_name, start_time, end_time, status,
         rows_read, rows_inserted, rows_updated, rows_rejected, target_row_count,
         error_number, error_message)
    VALUES
        (@batch_id, @procedure_name, @step_name, @start_time, SYSDATETIME(), @status,
         @rows_read, @rows_inserted, @rows_updated, @rows_rejected, @target_row_count,
         @error_number, @error_message);

    SET @audit_id = SCOPE_IDENTITY();
END
```

## fact.usp_load_fact_order_line.sql

**Path:** `procedures/fact/fact.usp_load_fact_order_line.sql`

```sql
/* ============================================================================
   fact.usp_load_fact_order_line   (EXTREME)
   ----------------------------------------------------------------------------
   Grain: one row per order line (SALE or RETURN). CANCEL lines are excluded.
   Processing is order-grain: any order with a changed header or line (relative to the
   'fact.order_line' watermark) is reprocessed in full, because header-level discounts
   are allocated across all sale lines of the order.

   Business rules
   1. Point-in-time SCD2 customer lookup on order date; unknown member (-1) when no version exists.
   2. Product lookup against the current SCD1 dimension; missing product => reject.
   3. Header discount is allocated across SALE lines pro rata to line net value, rounded to 2dp,
      with the rounding remainder assigned to the last SALE line so allocations always sum exactly.
   4. RETURN lines take the unit price of the original SALE line (same order + product) when
      they carry no price of their own; a return without an original sale => reject.
   5. Amounts are signed (returns negative) and converted to USD at the latest rate on/before order date.
   6. Rejected lines go to fact.order_line_reject with a reason code; lines that previously loaded
      but are now invalid are removed from the fact.
   7. Work is done in order_date windows of @window_days, one transaction per window.
   ============================================================================ */
CREATE OR ALTER PROCEDURE fact.usp_load_fact_order_line
    @batch_id    int,
    @from_date   date = NULL,
    @to_date     date = NULL,
    @window_days int  = 31,
    @reprocess   bit  = 0
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    DECLARE @proc sysname = OBJECT_SCHEMA_NAME(@@PROCID) + N'.' + OBJECT_NAME(@@PROCID);
    DECLARE @start datetime2 = SYSDATETIME();
    DECLARE @wm datetime2, @max_modified datetime2;
    DECLARE @advance_watermark bit = IIF(@from_date IS NULL AND @to_date IS NULL, 1, 0);
    DECLARE @win_from date, @win_to date;
    DECLARE @tot_read int = 0, @tot_ins int = 0, @tot_upd int = 0, @tot_rej int = 0;
    DECLARE @n_read int, @n_ins int, @n_upd int, @n_rej int;
    DECLARE @err_no int, @err_msg nvarchar(4000);

    BEGIN TRY
        IF @window_days < 1 OR @window_days > 366
            THROW 50030, 'window_days must be between 1 and 366.', 1;

        EXEC etl.usp_get_set_watermark @source_name = 'fact.order_line', @current_value = @wm OUTPUT;
        IF @reprocess = 1
            SET @wm = '1900-01-01';

        -- Work out the order-date range that has pending changes.
        SELECT @from_date    = ISNULL(@from_date, MIN(CAST(h.order_date AS date))),
               @to_date      = ISNULL(@to_date,   MAX(CAST(h.order_date AS date))),
               @max_modified = MAX(h.source_modified_at)
        FROM stg.order_header AS h
        WHERE h.source_modified_at > @wm
           OR EXISTS (SELECT 1 FROM stg.order_line AS l
                      WHERE l.order_src_id = h.order_src_id AND l.source_modified_at > @wm);

        IF @from_date IS NULL
        BEGIN
            EXEC etl.usp_write_audit @batch_id = @batch_id, @procedure_name = @proc, @step_name = 'load fact.order_line',
                 @start_time = @start, @status = 'SKIPPED', @rows_read = 0;
            RETURN;
        END

        CREATE TABLE #work (
            order_src_id       varchar(20)   NOT NULL,
            line_no            int           NOT NULL,
            order_date         date          NOT NULL,
            customer_src_id    varchar(20)   NULL,
            product_src_id     varchar(20)   NULL,
            channel            varchar(30)   NULL,
            ship_country       char(2)       NULL,
            currency_code      char(3)       NOT NULL,
            order_status       varchar(20)   NULL,
            order_discount_amt decimal(18,2) NOT NULL,
            line_type          varchar(10)   NOT NULL,
            quantity           int           NOT NULL,
            unit_price         decimal(18,4) NULL,
            line_discount_pct  decimal(5,2)  NOT NULL,
            source_modified_at datetime2     NOT NULL,
            PRIMARY KEY (order_src_id, line_no)
        );

        CREATE TABLE #calc (
            order_src_id        varchar(20)   NOT NULL,
            line_no             int           NOT NULL,
            order_date          date          NOT NULL,
            order_date_key      int           NOT NULL,
            customer_key        int           NOT NULL,
            product_key         int           NULL,
            product_src_id      varchar(20)   NULL,
            channel             varchar(30)   NULL,
            ship_country        char(2)       NULL,
            currency_code       char(3)       NOT NULL,
            order_status        varchar(20)   NULL,
            line_type           varchar(10)   NOT NULL,
            quantity            int           NOT NULL,
            unit_price          decimal(18,4) NULL,
            gross_amount        decimal(18,2) NULL,
            discount_amount     decimal(18,2) NULL,
            net_amount          decimal(18,2) NULL,
            net_amount_usd      decimal(18,2) NULL,
            is_return           bit           NOT NULL,
            is_unknown_customer bit           NOT NULL,
            source_modified_at  datetime2     NOT NULL,
            reject_code         varchar(30)   NULL,
            PRIMARY KEY (order_src_id, line_no)
        );

        SET @win_from = @from_date;

        WHILE @win_from <= @to_date
        BEGIN
            SET @win_to = DATEADD(day, @window_days - 1, @win_from);
            IF @win_to > @to_date SET @win_to = @to_date;

            TRUNCATE TABLE #work;
            TRUNCATE TABLE #calc;

            ---------------------------------------------------------------- 1. extract changed orders in window
            INSERT INTO #work
                (order_src_id, line_no, order_date, customer_src_id, product_src_id, channel, ship_country,
                 currency_code, order_status, order_discount_amt, line_type, quantity, unit_price,
                 line_discount_pct, source_modified_at)
            SELECT h.order_src_id, l.line_no, CAST(h.order_date AS date), h.customer_src_id, l.product_src_id,
                   h.channel, h.ship_country, h.currency_code, h.order_status, h.order_discount_amt,
                   l.line_type, l.quantity, l.unit_price, l.line_discount_pct,
                   CASE WHEN l.source_modified_at > h.source_modified_at THEN l.source_modified_at ELSE h.source_modified_at END
            FROM stg.order_header AS h
            JOIN stg.order_line   AS l ON l.order_src_id = h.order_src_id
            WHERE CAST(h.order_date AS date) BETWEEN @win_from AND @win_to
              AND l.line_type IN ('SALE', 'RETURN')
              AND h.order_status <> 'CANCELLED'
              AND (h.source_modified_at > @wm
                   OR EXISTS (SELECT 1 FROM stg.order_line AS cl
                              WHERE cl.order_src_id = h.order_src_id AND cl.source_modified_at > @wm));

            SET @n_read = @@ROWCOUNT;

            ---------------------------------------------------------------- 2. amounts, discount allocation, keys, FX
            ;WITH base AS (
                SELECT w.*,
                       CASE w.line_type WHEN 'SALE' THEN 1 WHEN 'RETURN' THEN -1 ELSE 0 END AS sign_factor,
                       o.orig_line_no,
                       ISNULL(NULLIF(w.unit_price, 0), o.orig_unit_price)                  AS eff_unit_price
                FROM #work AS w
                OUTER APPLY (
                    SELECT TOP (1) s.line_no AS orig_line_no, s.unit_price AS orig_unit_price
                    FROM #work AS s
                    WHERE w.line_type = 'RETURN'
                      AND s.order_src_id   = w.order_src_id
                      AND s.product_src_id = w.product_src_id
                      AND s.line_type      = 'SALE'
                    ORDER BY s.line_no
                ) AS o
            ),
            amounts AS (
                SELECT b.*,
                       CAST(b.quantity * b.eff_unit_price AS decimal(18,2))                                   AS gross_abs,
                       CAST(b.quantity * b.eff_unit_price * b.line_discount_pct / 100.0 AS decimal(18,2))     AS line_disc_abs
                FROM base AS b
            ),
            ranked AS (
                SELECT a.*,
                       SUM(CASE WHEN a.line_type = 'SALE' THEN a.gross_abs - a.line_disc_abs ELSE 0 END)
                           OVER (PARTITION BY a.order_src_id)                                                   AS order_sale_net,
                       ROW_NUMBER() OVER (PARTITION BY a.order_src_id
                                          ORDER BY CASE WHEN a.line_type = 'SALE' THEN 0 ELSE 1 END, a.line_no DESC) AS last_sale_rank
                FROM amounts AS a
            ),
            alloc_raw AS (
                SELECT r.*,
                       CASE WHEN r.line_type = 'SALE' AND r.order_sale_net > 0
                            THEN CAST(ROUND(r.order_discount_amt * (r.gross_abs - r.line_disc_abs) / r.order_sale_net, 2) AS decimal(18,2))
                            ELSE CAST(0 AS decimal(18,2)) END                                                   AS hdr_alloc_raw
                FROM ranked AS r
            ),
            alloc AS (
                SELECT x.*,
                       x.hdr_alloc_raw
                       + CASE WHEN x.last_sale_rank = 1 AND x.line_type = 'SALE' AND x.order_sale_net > 0
                              THEN x.order_discount_amt - SUM(x.hdr_alloc_raw) OVER (PARTITION BY x.order_src_id)
                              ELSE 0 END                                                                        AS hdr_alloc
                FROM alloc_raw AS x
            )
            INSERT INTO #calc
                (order_src_id, line_no, order_date, order_date_key, customer_key, product_key, product_src_id,
                 channel, ship_country, currency_code, order_status, line_type, quantity, unit_price,
                 gross_amount, discount_amount, net_amount, net_amount_usd, is_return, is_unknown_customer,
                 source_modified_at, reject_code)
            SELECT
                a.order_src_id,
                a.line_no,
                a.order_date,
                CONVERT(int, CONVERT(char(8), a.order_date, 112)),
                ISNULL(c.customer_key, -1),
                p.product_key,
                a.product_src_id,
                a.channel,
                a.ship_country,
                a.currency_code,
                a.order_status,
                a.line_type,
                a.sign_factor * a.quantity,
                a.eff_unit_price,
                g.gross_amount,
                g.discount_amount,
                g.gross_amount - g.discount_amount,
                dbo.fn_convert_currency(g.gross_amount - g.discount_amount, a.currency_code, a.order_date),
                IIF(a.line_type = 'RETURN', 1, 0),
                IIF(c.customer_key IS NULL, 1, 0),
                a.source_modified_at,
                CASE WHEN a.quantity <= 0                                      THEN 'BAD_QUANTITY'
                     WHEN p.product_key IS NULL                                THEN 'UNKNOWN_PRODUCT'
                     WHEN a.line_type = 'RETURN' AND a.orig_line_no IS NULL    THEN 'RETURN_NO_ORIGINAL'
                     WHEN a.eff_unit_price IS NULL OR a.eff_unit_price < 0     THEN 'BAD_PRICE'
                     WHEN dbo.fn_convert_currency(1, a.currency_code, a.order_date) IS NULL THEN 'NO_FX_RATE'
                END
            FROM alloc AS a
            CROSS APPLY (SELECT a.sign_factor * a.gross_abs                      AS gross_amount,
                                a.sign_factor * (a.line_disc_abs + a.hdr_alloc)  AS discount_amount) AS g
            LEFT JOIN dim.customer AS c
                   ON c.customer_src_id = a.customer_src_id
                  AND a.order_date >= c.effective_from
                  AND a.order_date <= c.effective_to
            LEFT JOIN dim.product  AS p
                   ON p.product_src_id = a.product_src_id
                  AND p.product_key > 0;

            ---------------------------------------------------------------- 3. persist (one transaction per window)
            BEGIN TRANSACTION;

                DELETE r
                FROM fact.order_line_reject AS r
                JOIN #calc AS c ON c.order_src_id = r.order_src_id AND c.line_no = r.line_no;

                INSERT INTO fact.order_line_reject
                    (load_batch_id, order_src_id, line_no, order_date, product_src_id, reject_code, reject_reason)
                SELECT @batch_id, c.order_src_id, c.line_no, c.order_date, c.product_src_id, c.reject_code,
                       CASE c.reject_code
                            WHEN 'BAD_QUANTITY'       THEN 'Quantity must be greater than zero.'
                            WHEN 'UNKNOWN_PRODUCT'    THEN 'Product not found in dim.product.'
                            WHEN 'RETURN_NO_ORIGINAL' THEN 'Return line has no matching sale line on the same order.'
                            WHEN 'BAD_PRICE'          THEN 'Unit price missing or negative.'
                            WHEN 'NO_FX_RATE'         THEN 'No currency rate on or before the order date.'
                       END
                FROM #calc AS c
                WHERE c.reject_code IS NOT NULL;

                SET @n_rej = @@ROWCOUNT;

                -- Lines that were valid before but are rejected now, or no longer exist on a reprocessed order.
                DELETE f
                FROM fact.order_line AS f
                JOIN #calc AS c ON c.order_src_id = f.order_src_id AND c.line_no = f.line_no
                WHERE c.reject_code IS NOT NULL;

                DELETE f
                FROM fact.order_line AS f
                WHERE EXISTS (SELECT 1 FROM #work AS o WHERE o.order_src_id = f.order_src_id)
                  AND NOT EXISTS (SELECT 1 FROM #work AS w WHERE w.order_src_id = f.order_src_id AND w.line_no = f.line_no);

                UPDATE f
                SET f.order_date_key      = c.order_date_key,
                    f.customer_key        = c.customer_key,
                    f.product_key         = c.product_key,
                    f.channel             = c.channel,
                    f.ship_country        = c.ship_country,
                    f.currency_code       = c.currency_code,
                    f.order_status        = c.order_status,
                    f.line_type           = c.line_type,
                    f.quantity            = c.quantity,
                    f.unit_price          = c.unit_price,
                    f.gross_amount        = c.gross_amount,
                    f.discount_amount     = c.discount_amount,
                    f.net_amount          = c.net_amount,
                    f.net_amount_usd      = c.net_amount_usd,
                    f.is_return           = c.is_return,
                    f.is_unknown_customer = c.is_unknown_customer,
                    f.source_modified_at  = c.source_modified_at,
                    f.load_batch_id       = @batch_id,
                    f.updated_at          = SYSDATETIME()
                FROM fact.order_line AS f
                JOIN #calc AS c ON c.order_src_id = f.order_src_id AND c.line_no = f.line_no
                WHERE c.reject_code IS NULL;

                SET @n_upd = @@ROWCOUNT;

                INSERT INTO fact.order_line
                    (order_src_id, line_no, order_date_key, customer_key, product_key, channel, ship_country,
                     currency_code, order_status, line_type, quantity, unit_price, gross_amount, discount_amount,
                     net_amount, net_amount_usd, is_return, is_unknown_customer, source_modified_at, load_batch_id)
                SELECT c.order_src_id, c.line_no, c.order_date_key, c.customer_key, c.product_key, c.channel, c.ship_country,
                       c.currency_code, c.order_status, c.line_type, c.quantity, c.unit_price, c.gross_amount, c.discount_amount,
                       c.net_amount, c.net_amount_usd, c.is_return, c.is_unknown_customer, c.source_modified_at, @batch_id
                FROM #calc AS c
                WHERE c.reject_code IS NULL
                  AND NOT EXISTS (SELECT 1 FROM fact.order_line AS f
                                  WHERE f.order_src_id = c.order_src_id AND f.line_no = c.line_no);

                SET @n_ins = @@ROWCOUNT;

            COMMIT TRANSACTION;

            SET @tot_read = @tot_read + @n_read;
            SET @tot_ins  = @tot_ins  + @n_ins;
            SET @tot_upd  = @tot_upd  + @n_upd;
            SET @tot_rej  = @tot_rej  + @n_rej;

            SET @win_from = DATEADD(day, 1, @win_to);
        END

        IF @advance_watermark = 1 AND @max_modified IS NOT NULL
            EXEC etl.usp_get_set_watermark @source_name = 'fact.order_line', @new_value = @max_modified, @current_value = @wm OUTPUT;

        EXEC etl.usp_write_audit @batch_id = @batch_id, @procedure_name = @proc, @step_name = 'load fact.order_line',
             @start_time = @start, @status = 'SUCCESS', @rows_read = @tot_read, @rows_inserted = @tot_ins,
             @rows_updated = @tot_upd, @rows_rejected = @tot_rej;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        SET @err_no = ERROR_NUMBER();
        SET @err_msg = ERROR_MESSAGE();
        EXEC etl.usp_write_audit @batch_id = @batch_id, @procedure_name = @proc, @step_name = 'load fact.order_line',
             @start_time = @start, @status = 'FAILED', @rows_read = @tot_read, @rows_inserted = @tot_ins,
             @rows_updated = @tot_upd, @rows_rejected = @tot_rej, @error_number = @err_no, @error_message = @err_msg;
        THROW;
    END CATCH
END
```

## fact.usp_load_fact_payment.sql

**Path:** `procedures/fact/fact.usp_load_fact_payment.sql`

```sql
/* ============================================================================
   fact.usp_load_fact_payment   (HIGH)
   - Signs amounts by type (REFUND / CHARGEBACK negative), converts to USD.
   - Resolves the customer through fact.order_line; payments for orders that have not loaded yet
     are kept as orphans (customer -1) and reconciled on a later run.
   - Recomputes per-order running totals across NEW and already-loaded payments, in event order.
   - PIVOT of payment types gives the final net paid per order, compared with the order value.
   ============================================================================ */
CREATE OR ALTER PROCEDURE fact.usp_load_fact_payment
    @batch_id  int,
    @reprocess bit = 0
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    DECLARE @proc sysname = OBJECT_SCHEMA_NAME(@@PROCID) + N'.' + OBJECT_NAME(@@PROCID);
    DECLARE @start datetime2 = SYSDATETIME();
    DECLARE @rows_read int, @rows_rej int, @ins int, @upd int, @reconciled int;
    DECLARE @paid_tolerance_usd decimal(9,2) = 0.10;   -- per-line USD rounding can add up to a few cents per order
    DECLARE @err_no int, @err_msg nvarchar(4000);

    BEGIN TRY
        CREATE TABLE #new (
            payment_src_id    varchar(30)   NOT NULL,
            order_src_id      varchar(20)   NOT NULL,
            payment_date_key  int           NOT NULL,
            customer_key      int           NOT NULL,
            method            varchar(20)   NULL,
            payment_type      varchar(20)   NOT NULL,
            status            varchar(20)   NULL,
            currency_code     char(3)       NULL,
            amount_signed     decimal(18,2) NOT NULL,
            amount_signed_usd decimal(18,2) NOT NULL,
            event_ts          datetime2     NULL,
            is_orphan         bit           NOT NULL,
            PRIMARY KEY (payment_src_id, order_src_id)
        );
        CREATE TABLE #recon (payment_src_id varchar(30) NOT NULL, order_src_id varchar(20) NOT NULL);
        CREATE TABLE #merge_log (action_name nvarchar(10) NOT NULL);

        SELECT @rows_read = COUNT(*)
        FROM stg.payment AS p
        WHERE p.load_batch_id = @batch_id OR @reprocess = 1;

        INSERT INTO #new
        SELECT p.payment_src_id,
               p.order_src_id,
               ISNULL(CONVERT(int, CONVERT(char(8), p.event_ts, 112)), -1),
               ISNULL(o.customer_key, -1),
               p.method,
               p.payment_type,
               p.status,
               p.currency_code,
               amt.amount_signed,
               dbo.fn_convert_currency(amt.amount_signed, p.currency_code, CAST(p.event_ts AS date)),
               p.event_ts,
               IIF(o.order_src_id IS NULL, 1, 0)
        FROM stg.payment AS p
        CROSS APPLY (SELECT CASE WHEN p.payment_type IN ('REFUND', 'CHARGEBACK')
                                 THEN -ABS(p.amount) ELSE ABS(p.amount) END AS amount_signed) AS amt
        OUTER APPLY (SELECT TOP (1) f.order_src_id, f.customer_key
                     FROM fact.order_line AS f
                     WHERE f.order_src_id = p.order_src_id) AS o
        WHERE (p.load_batch_id = @batch_id OR @reprocess = 1)
          AND p.status IN ('OK', 'SETTLED')
          AND p.payment_type IN ('CAPTURE', 'REFUND', 'CHARGEBACK')
          AND dbo.fn_convert_currency(amt.amount_signed, p.currency_code, CAST(p.event_ts AS date)) IS NOT NULL;

        SET @rows_rej = @rows_read - (SELECT COUNT(*) FROM #new);   -- failed status, unknown type, or no FX rate

        BEGIN TRANSACTION;

            -- Reconcile earlier orphans whose order has since arrived.
            UPDATE fp
            SET fp.customer_key = o.customer_key,
                fp.is_orphan    = 0,
                fp.updated_at   = SYSDATETIME()
            OUTPUT inserted.payment_src_id, inserted.order_src_id INTO #recon (payment_src_id, order_src_id)
            FROM fact.payment AS fp
            CROSS APPLY (SELECT TOP (1) f.customer_key
                         FROM fact.order_line AS f
                         WHERE f.order_src_id = fp.order_src_id) AS o
            WHERE fp.is_orphan = 1;

            SET @reconciled = @@ROWCOUNT;

            -- Every payment of every affected order: new rows plus rows already in the fact.
            SELECT a.payment_src_id, a.order_src_id, a.payment_type, a.event_ts, a.amount_signed_usd
            INTO #all
            FROM (
                SELECT n.payment_src_id, n.order_src_id, n.payment_type, n.event_ts, n.amount_signed_usd
                FROM #new AS n
                UNION ALL
                SELECT fp.payment_src_id, fp.order_src_id, fp.payment_type, fp.event_ts, fp.amount_signed_usd
                FROM fact.payment AS fp
                WHERE (fp.order_src_id IN (SELECT order_src_id FROM #new)
                       OR fp.order_src_id IN (SELECT order_src_id FROM #recon))
                  AND NOT EXISTS (SELECT 1 FROM #new AS n
                                  WHERE n.payment_src_id = fp.payment_src_id AND n.order_src_id = fp.order_src_id)
            ) AS a;

            SELECT x.payment_src_id, x.order_src_id,
                   SUM(x.amount_signed_usd) OVER (
                       PARTITION BY x.order_src_id
                       ORDER BY x.event_ts, x.payment_src_id
                       ROWS UNBOUNDED PRECEDING) AS running_paid_usd
            INTO #running
            FROM #all AS x;

            SELECT pv.order_src_id,
                   ISNULL(pv.[CAPTURE], 0) + ISNULL(pv.[REFUND], 0) + ISNULL(pv.[CHARGEBACK], 0) AS order_net_paid_usd
            INTO #order_paid
            FROM (SELECT order_src_id, payment_type, amount_signed_usd FROM #all) AS s
            PIVOT (SUM(amount_signed_usd) FOR payment_type IN ([CAPTURE], [REFUND], [CHARGEBACK])) AS pv;

            SELECT f.order_src_id, SUM(f.net_amount_usd) AS order_net_amount_usd
            INTO #order_value
            FROM fact.order_line AS f
            WHERE f.order_src_id IN (SELECT order_src_id FROM #all)
            GROUP BY f.order_src_id;

            MERGE fact.payment AS t
            USING (
                SELECT r.payment_src_id, r.order_src_id, r.running_paid_usd,
                       op.order_net_paid_usd, ov.order_net_amount_usd,
                       CASE WHEN ov.order_net_amount_usd IS NOT NULL
                             AND op.order_net_paid_usd >= ov.order_net_amount_usd - @paid_tolerance_usd THEN 1 ELSE 0 END AS is_paid_in_full,
                       n.payment_date_key, n.customer_key, n.method, n.payment_type, n.status, n.currency_code,
                       n.amount_signed, n.amount_signed_usd, n.event_ts, n.is_orphan
                FROM #running AS r
                JOIN #order_paid AS op ON op.order_src_id = r.order_src_id
                LEFT JOIN #order_value AS ov ON ov.order_src_id = r.order_src_id
                LEFT JOIN #new AS n ON n.payment_src_id = r.payment_src_id AND n.order_src_id = r.order_src_id
            ) AS s
               ON t.payment_src_id = s.payment_src_id AND t.order_src_id = s.order_src_id
            WHEN MATCHED THEN
                UPDATE SET
                    t.running_paid_usd        = s.running_paid_usd,
                    t.order_net_paid_usd      = s.order_net_paid_usd,
                    t.order_net_amount_usd    = s.order_net_amount_usd,
                    t.is_order_paid_in_full   = s.is_paid_in_full,
                    t.status                  = ISNULL(s.status, t.status),
                    t.updated_at              = SYSDATETIME()
            WHEN NOT MATCHED BY TARGET THEN
                INSERT (payment_src_id, order_src_id, payment_date_key, customer_key, method, payment_type, status,
                        currency_code, amount_signed, amount_signed_usd, running_paid_usd, order_net_paid_usd,
                        order_net_amount_usd, is_order_paid_in_full, is_orphan, event_ts, load_batch_id)
                VALUES (s.payment_src_id, s.order_src_id, s.payment_date_key, s.customer_key, s.method, s.payment_type,
                        s.status, s.currency_code, s.amount_signed, s.amount_signed_usd, s.running_paid_usd,
                        s.order_net_paid_usd, s.order_net_amount_usd, s.is_paid_in_full, s.is_orphan, s.event_ts, @batch_id)
            OUTPUT $action INTO #merge_log (action_name);

        COMMIT TRANSACTION;

        SELECT @ins = COUNT(*) FROM #merge_log WHERE action_name = 'INSERT';
        SELECT @upd = COUNT(*) FROM #merge_log WHERE action_name = 'UPDATE';

        EXEC etl.usp_write_audit @batch_id = @batch_id, @procedure_name = @proc, @step_name = 'load fact.payment',
             @start_time = @start, @status = 'SUCCESS', @rows_read = @rows_read, @rows_inserted = @ins,
             @rows_updated = @upd, @rows_rejected = @rows_rej;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        SET @err_no = ERROR_NUMBER();
        SET @err_msg = ERROR_MESSAGE();
        EXEC etl.usp_write_audit @batch_id = @batch_id, @procedure_name = @proc, @step_name = 'load fact.payment',
             @start_time = @start, @status = 'FAILED', @error_number = @err_no, @error_message = @err_msg;
        THROW;
    END CATCH
END
```

## fact.usp_load_fact_shipment.sql

**Path:** `procedures/fact/fact.usp_load_fact_shipment.sql`

```sql
/* Loads shipments with SLA measures. Uses the scalar UDF dbo.fn_business_days (row-by-row on SQL Server)
   and unknown-member date keys (-1) for missing delivery / promise dates. */
CREATE OR ALTER PROCEDURE fact.usp_load_fact_shipment
    @batch_id   int,
    @reprocess  bit  = 0,
    @as_of_date date = NULL
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    DECLARE @proc sysname = OBJECT_SCHEMA_NAME(@@PROCID) + N'.' + OBJECT_NAME(@@PROCID);
    DECLARE @start datetime2 = SYSDATETIME();
    DECLARE @rows_read int, @ins int, @upd int, @err_no int, @err_msg nvarchar(4000);

    SET @as_of_date = ISNULL(@as_of_date, CAST(SYSDATETIME() AS date));

    BEGIN TRY
        CREATE TABLE #src (
            shipment_src_id        varchar(30)  NOT NULL,
            order_src_id           varchar(20)  NOT NULL,
            customer_key           int          NOT NULL,
            carrier                varchar(30)  NULL,
            ship_date_key          int          NOT NULL,
            delivered_date_key     int          NOT NULL,
            promised_date_key      int          NOT NULL,
            weight_kg              decimal(9,3) NULL,
            transit_business_days  int          NULL,
            promised_business_days int          NULL,
            delivery_status        varchar(20)  NOT NULL,
            is_sla_breach          bit          NOT NULL,
            PRIMARY KEY (shipment_src_id, order_src_id)
        );
        CREATE TABLE #merge_log (action_name nvarchar(10) NOT NULL);

        INSERT INTO #src
        SELECT s.shipment_src_id,
               s.order_src_id,
               ISNULL(oc.customer_key, -1),
               s.carrier,
               ISNULL(dsh.date_key, -1),
               ISNULL(ddl.date_key, -1),
               ISNULL(dpr.date_key, -1),
               s.weight_kg,
               CASE WHEN s.delivered_ts IS NOT NULL
                    THEN dbo.fn_business_days(CAST(s.shipped_ts AS date), CAST(s.delivered_ts AS date)) END,
               CASE WHEN s.promised_ts IS NOT NULL
                    THEN dbo.fn_business_days(CAST(s.shipped_ts AS date), CAST(s.promised_ts AS date)) END,
               CASE WHEN s.delivered_ts IS NOT NULL                         THEN 'DELIVERED'
                    WHEN s.promised_ts  < @as_of_date                       THEN 'LATE_UNDELIVERED'
                    WHEN s.shipped_ts   IS NOT NULL                         THEN 'IN_TRANSIT'
                    ELSE 'PENDING' END,
               CASE WHEN s.delivered_ts IS NOT NULL AND CAST(s.delivered_ts AS date) > CAST(s.promised_ts AS date) THEN 1
                    WHEN s.delivered_ts IS NULL     AND CAST(s.promised_ts  AS date) < @as_of_date                THEN 1
                    ELSE 0 END
        FROM stg.shipment AS s
        LEFT JOIN dim.date AS dsh ON dsh.full_date = CAST(s.shipped_ts   AS date)
        LEFT JOIN dim.date AS ddl ON ddl.full_date = CAST(s.delivered_ts AS date)
        LEFT JOIN dim.date AS dpr ON dpr.full_date = CAST(s.promised_ts  AS date)
        OUTER APPLY (SELECT TOP (1) f.customer_key
                     FROM fact.order_line AS f
                     WHERE f.order_src_id = s.order_src_id) AS oc
        WHERE s.load_batch_id = @batch_id OR @reprocess = 1;

        SET @rows_read = @@ROWCOUNT;

        MERGE fact.shipment AS t
        USING #src AS s
           ON t.shipment_src_id = s.shipment_src_id AND t.order_src_id = s.order_src_id
        WHEN MATCHED THEN
            UPDATE SET
                t.customer_key           = s.customer_key,
                t.carrier                = s.carrier,
                t.ship_date_key          = s.ship_date_key,
                t.delivered_date_key     = s.delivered_date_key,
                t.promised_date_key      = s.promised_date_key,
                t.weight_kg              = s.weight_kg,
                t.transit_business_days  = s.transit_business_days,
                t.promised_business_days = s.promised_business_days,
                t.delivery_status        = s.delivery_status,
                t.is_sla_breach          = s.is_sla_breach,
                t.load_batch_id          = @batch_id,
                t.updated_at             = SYSDATETIME()
        WHEN NOT MATCHED BY TARGET THEN
            INSERT (shipment_src_id, order_src_id, customer_key, carrier, ship_date_key, delivered_date_key,
                    promised_date_key, weight_kg, transit_business_days, promised_business_days,
                    delivery_status, is_sla_breach, load_batch_id)
            VALUES (s.shipment_src_id, s.order_src_id, s.customer_key, s.carrier, s.ship_date_key, s.delivered_date_key,
                    s.promised_date_key, s.weight_kg, s.transit_business_days, s.promised_business_days,
                    s.delivery_status, s.is_sla_breach, @batch_id)
        OUTPUT $action INTO #merge_log (action_name);

        SELECT @ins = COUNT(*) FROM #merge_log WHERE action_name = 'INSERT';
        SELECT @upd = COUNT(*) FROM #merge_log WHERE action_name = 'UPDATE';

        EXEC etl.usp_write_audit @batch_id = @batch_id, @procedure_name = @proc, @step_name = 'load fact.shipment',
             @start_time = @start, @status = 'SUCCESS', @rows_read = @rows_read, @rows_inserted = @ins, @rows_updated = @upd;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        SET @err_no = ERROR_NUMBER();
        SET @err_msg = ERROR_MESSAGE();
        EXEC etl.usp_write_audit @batch_id = @batch_id, @procedure_name = @proc, @step_name = 'load fact.shipment',
             @start_time = @start, @status = 'FAILED', @error_number = @err_no, @error_message = @err_msg;
        THROW;
    END CATCH
END
```

## stg.usp_load_customer.sql

**Path:** `procedures/stg/stg.usp_load_customer.sql`

```sql
CREATE OR ALTER PROCEDURE stg.usp_load_customer
    @batch_id int
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    DECLARE @proc sysname = OBJECT_SCHEMA_NAME(@@PROCID) + N'.' + OBJECT_NAME(@@PROCID);
    DECLARE @start datetime2 = SYSDATETIME();
    DECLARE @rows_read int, @rows_ins int, @err_no int, @err_msg nvarchar(4000);

    BEGIN TRY
        SELECT @rows_read = COUNT(*) FROM lnd.customer;

        TRUNCATE TABLE stg.customer;

        ;WITH ranked AS (
            SELECT l.*,
                   ROW_NUMBER() OVER (
                       PARTITION BY UPPER(LTRIM(RTRIM(l.customer_src_id)))
                       ORDER BY TRY_CONVERT(datetime2, l.modified_at) DESC, l.lnd_id DESC) AS rn
            FROM lnd.customer AS l
            WHERE l.customer_src_id IS NOT NULL
              AND LTRIM(RTRIM(l.customer_src_id)) <> ''
        )
        INSERT INTO stg.customer
            (customer_src_id, first_name, last_name, full_name, email, phone, address_line, city,
             state_code, country_code, customer_segment, source_created_date, source_modified_at, load_batch_id)
        SELECT
            UPPER(LTRIM(RTRIM(r.customer_src_id))),
            LEFT(n.clean_name, CHARINDEX(' ', n.clean_name + ' ') - 1),
            NULLIF(LTRIM(SUBSTRING(n.clean_name, CHARINDEX(' ', n.clean_name + ' '), 200)), ''),
            n.clean_name,
            CASE WHEN CHARINDEX('@', r.email) > 1
                  AND CHARINDEX('.', r.email, CHARINDEX('@', r.email)) > 0
                 THEN LOWER(LTRIM(RTRIM(r.email))) END,
            REPLACE(REPLACE(REPLACE(REPLACE(LTRIM(RTRIM(r.phone)), ' ', ''), '-', ''), '(', ''), ')', ''),
            LTRIM(RTRIM(r.address_line)),
            LTRIM(RTRIM(r.city)),
            UPPER(LTRIM(RTRIM(r.state_code))),
            UPPER(LEFT(LTRIM(RTRIM(r.country_code)), 2)),
            IIF(UPPER(LTRIM(RTRIM(r.customer_segment))) IN ('RETAIL', 'WHOLESALE', 'CORPORATE'),
                UPPER(LTRIM(RTRIM(r.customer_segment))), 'OTHER'),
            COALESCE(TRY_CONVERT(date, r.created_date, 23), TRY_CONVERT(date, r.created_date, 103)),
            TRY_CONVERT(datetime2, r.modified_at),
            @batch_id
        FROM ranked AS r
        CROSS APPLY (SELECT dbo.fn_clean_name(r.full_name) AS clean_name) AS n
        WHERE r.rn = 1;

        SET @rows_ins = @@ROWCOUNT;

        EXEC etl.usp_write_audit @batch_id = @batch_id, @procedure_name = @proc, @step_name = 'load stg.customer',
             @start_time = @start, @status = 'SUCCESS', @rows_read = @rows_read, @rows_inserted = @rows_ins,
             @rows_rejected = @rows_read - @rows_ins;   -- duplicates and rows without a key
    END TRY
    BEGIN CATCH
        SET @err_no = ERROR_NUMBER();
        SET @err_msg = ERROR_MESSAGE();
        EXEC etl.usp_write_audit @batch_id = @batch_id, @procedure_name = @proc, @step_name = 'load stg.customer',
             @start_time = @start, @status = 'FAILED', @error_number = @err_no, @error_message = @err_msg;
        THROW;
    END CATCH
END
```

## stg.usp_load_orders.sql

**Path:** `procedures/stg/stg.usp_load_orders.sql`

```sql
/* Incremental, watermark-driven load of order headers and lines.
   A header's modified_at is assumed to be bumped whenever any of its lines change. */
CREATE OR ALTER PROCEDURE stg.usp_load_orders
    @batch_id        int,
    @lookback_hours  int = 2
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    DECLARE @proc sysname = OBJECT_SCHEMA_NAME(@@PROCID) + N'.' + OBJECT_NAME(@@PROCID);
    DECLARE @start datetime2 = SYSDATETIME();
    DECLARE @wm datetime2, @wm_from datetime2, @new_wm datetime2;
    DECLARE @rows_read int, @hdr_ins int, @line_ins int, @rejected int;
    DECLARE @err_no int, @err_msg nvarchar(4000);

    BEGIN TRY
        EXEC etl.usp_get_set_watermark @source_name = 'lnd.order_header', @current_value = @wm OUTPUT;
        SET @wm_from = DATEADD(hour, -@lookback_hours, @wm);   -- overlap window to catch late commits

        CREATE TABLE #hdr (
            order_src_id       varchar(20)   NOT NULL PRIMARY KEY,
            customer_src_id    varchar(20)   NULL,
            order_ts           datetime2     NOT NULL,
            order_status       varchar(20)   NOT NULL,
            currency_code      char(3)       NOT NULL,
            channel            varchar(30)   NOT NULL,
            ship_country       char(2)       NULL,
            order_discount_amt decimal(18,2) NOT NULL,
            days_to_land       int           NULL,
            is_late_arriving   bit           NOT NULL,
            modified_at        datetime2     NOT NULL
        );

        CREATE TABLE #lines (
            order_src_id      varchar(20)   NOT NULL,
            line_no           int           NOT NULL,
            product_src_id    varchar(20)   NULL,
            quantity          int           NOT NULL,
            unit_price        decimal(18,4) NULL,
            line_discount_pct decimal(5,2)  NOT NULL,
            line_type         varchar(10)   NOT NULL,
            modified_at       datetime2     NOT NULL,
            PRIMARY KEY (order_src_id, line_no)
        );

        SELECT @rows_read = COUNT(*) FROM lnd.order_header WHERE modified_at > @wm_from;

        INSERT INTO #hdr
        SELECT x.order_src_id, UPPER(LTRIM(RTRIM(x.customer_src_id))), x.order_ts,
               UPPER(ISNULL(NULLIF(LTRIM(RTRIM(x.order_status)), ''), 'OPEN')),
               UPPER(ISNULL(NULLIF(LTRIM(RTRIM(x.currency_code)), ''), 'USD')),
               UPPER(ISNULL(NULLIF(LTRIM(RTRIM(x.channel)), ''), 'WEB')),
               UPPER(LEFT(LTRIM(RTRIM(x.ship_country)), 2)),
               ISNULL(TRY_CONVERT(decimal(18,2), x.order_discount_amt), 0),
               DATEDIFF(day, x.order_ts, x.modified_at),
               IIF(DATEDIFF(day, x.order_ts, x.modified_at) > 3, 1, 0),
               x.modified_at
        FROM (
            SELECT h.*,
                   TRY_CONVERT(datetime2, h.order_date, 120) AS order_ts,
                   ROW_NUMBER() OVER (PARTITION BY h.order_src_id ORDER BY h.modified_at DESC, h.lnd_id DESC) AS rn
            FROM lnd.order_header AS h
            WHERE h.modified_at > @wm_from
        ) AS x
        WHERE x.rn = 1
          AND x.order_ts IS NOT NULL;

        SET @hdr_ins = @@ROWCOUNT;
        SET @rejected = @rows_read - @hdr_ins;   -- duplicates within the window + unparseable order dates

        INSERT INTO #lines
        SELECT y.order_src_id, y.line_no, UPPER(LTRIM(RTRIM(y.product_src_id))), ISNULL(y.quantity, 0),
               y.unit_price, ISNULL(y.line_discount_pct, 0), UPPER(ISNULL(y.line_type, 'SALE')), y.modified_at
        FROM (
            SELECT l.*,
                   ROW_NUMBER() OVER (PARTITION BY l.order_src_id, l.line_no ORDER BY l.modified_at DESC, l.lnd_id DESC) AS rn
            FROM lnd.order_line AS l
            JOIN #hdr AS h ON h.order_src_id = l.order_src_id
        ) AS y
        WHERE y.rn = 1;

        SET @line_ins = @@ROWCOUNT;

        BEGIN TRANSACTION;

            DELETE l FROM stg.order_line   AS l JOIN #hdr AS h ON h.order_src_id = l.order_src_id;
            DELETE o FROM stg.order_header AS o JOIN #hdr AS h ON h.order_src_id = o.order_src_id;

            INSERT INTO stg.order_header
                (order_src_id, customer_src_id, order_date, order_status, currency_code, channel, ship_country,
                 order_discount_amt, days_to_land, is_late_arriving, source_modified_at, load_batch_id)
            SELECT order_src_id, customer_src_id, order_ts, order_status, currency_code, channel, ship_country,
                   order_discount_amt, days_to_land, is_late_arriving, modified_at, @batch_id
            FROM #hdr;

            INSERT INTO stg.order_line
                (order_src_id, line_no, product_src_id, quantity, unit_price, line_discount_pct, line_type,
                 source_modified_at, load_batch_id)
            SELECT order_src_id, line_no, product_src_id, quantity, unit_price, line_discount_pct, line_type,
                   modified_at, @batch_id
            FROM #lines;

            SELECT @new_wm = MAX(modified_at) FROM #hdr;
            IF @new_wm IS NOT NULL
                EXEC etl.usp_get_set_watermark @source_name = 'lnd.order_header', @new_value = @new_wm, @current_value = @wm OUTPUT;

        COMMIT TRANSACTION;

        EXEC etl.usp_write_audit @batch_id = @batch_id, @procedure_name = @proc, @step_name = 'load stg.order_header/order_line',
             @start_time = @start, @status = 'SUCCESS', @rows_read = @rows_read,
             @rows_inserted = @hdr_ins, @rows_updated = @line_ins, @rows_rejected = @rejected;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        SET @err_no = ERROR_NUMBER();
        SET @err_msg = ERROR_MESSAGE();
        EXEC etl.usp_write_audit @batch_id = @batch_id, @procedure_name = @proc, @step_name = 'load stg.order_header/order_line',
             @start_time = @start, @status = 'FAILED', @error_number = @err_no, @error_message = @err_msg;
        THROW;
    END CATCH
END
```

## stg.usp_load_payments.sql

**Path:** `procedures/stg/stg.usp_load_payments.sql`

```sql
/* Parses gateway JSON. One landing document can allocate a payment across several orders. */
CREATE OR ALTER PROCEDURE stg.usp_load_payments
    @batch_id int
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    DECLARE @proc sysname = OBJECT_SCHEMA_NAME(@@PROCID) + N'.' + OBJECT_NAME(@@PROCID);
    DECLARE @start datetime2 = SYSDATETIME();
    DECLARE @wm datetime2, @new_wm datetime2;
    DECLARE @rows_read int, @rows_ins int, @rows_rej int, @err_no int, @err_msg nvarchar(4000);

    BEGIN TRY
        EXEC etl.usp_get_set_watermark @source_name = 'lnd.payment', @current_value = @wm OUTPUT;

        SELECT @rows_read = COUNT(*) FROM lnd.payment WHERE received_at > @wm;
        SELECT @rows_rej  = COUNT(*) FROM lnd.payment WHERE received_at > @wm AND ISJSON(payload) <> 1;

        BEGIN TRANSACTION;

            DELETE sp
            FROM stg.payment AS sp
            WHERE EXISTS (SELECT 1 FROM lnd.payment AS l
                          WHERE l.received_at > @wm AND l.payment_src_id = sp.payment_src_id);

            ;WITH latest AS (
                SELECT p.*,
                       ROW_NUMBER() OVER (PARTITION BY p.payment_src_id ORDER BY p.received_at DESC, p.lnd_id DESC) AS rn
                FROM lnd.payment AS p
                WHERE p.received_at > @wm
            )
            INSERT INTO stg.payment
                (payment_src_id, order_src_id, method, payment_type, amount, currency_code, status,
                 event_ts, gateway_ref, load_batch_id)
            SELECT l.payment_src_id,
                   a.order_id,
                   UPPER(j.method),
                   UPPER(j.payment_type),
                   a.amount,
                   UPPER(j.currency_code),
                   UPPER(j.status),
                   j.event_ts,
                   j.gateway_ref,
                   @batch_id
            FROM latest AS l
            CROSS APPLY OPENJSON(CASE WHEN ISJSON(l.payload) = 1 THEN l.payload END)
                WITH (
                    method        varchar(20)  '$.method',
                    payment_type  varchar(20)  '$.type',
                    currency_code char(3)      '$.currency',
                    status        varchar(20)  '$.status',
                    event_ts      datetime2    '$.event_ts',
                    gateway_ref   varchar(50)  '$.gateway.ref',
                    allocations   nvarchar(max) '$.allocations' AS JSON
                ) AS j
            CROSS APPLY OPENJSON(j.allocations)
                WITH (
                    order_id varchar(20)   '$.order_id',
                    amount   decimal(18,2) '$.amount'
                ) AS a
            WHERE l.rn = 1
              AND a.order_id IS NOT NULL
              AND a.amount IS NOT NULL;

            SET @rows_ins = @@ROWCOUNT;

            SELECT @new_wm = MAX(received_at) FROM lnd.payment WHERE received_at > @wm;
            IF @new_wm IS NOT NULL
                EXEC etl.usp_get_set_watermark @source_name = 'lnd.payment', @new_value = @new_wm, @current_value = @wm OUTPUT;

        COMMIT TRANSACTION;

        EXEC etl.usp_write_audit @batch_id = @batch_id, @procedure_name = @proc, @step_name = 'load stg.payment',
             @start_time = @start, @status = 'SUCCESS', @rows_read = @rows_read, @rows_inserted = @rows_ins,
             @rows_rejected = @rows_rej;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        SET @err_no = ERROR_NUMBER();
        SET @err_msg = ERROR_MESSAGE();
        EXEC etl.usp_write_audit @batch_id = @batch_id, @procedure_name = @proc, @step_name = 'load stg.payment',
             @start_time = @start, @status = 'FAILED', @error_number = @err_no, @error_message = @err_msg;
        THROW;
    END CATCH
END
```

## stg.usp_load_product.sql

**Path:** `procedures/stg/stg.usp_load_product.sql`

```sql
CREATE OR ALTER PROCEDURE stg.usp_load_product
    @batch_id int
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    DECLARE @proc sysname = OBJECT_SCHEMA_NAME(@@PROCID) + N'.' + OBJECT_NAME(@@PROCID);
    DECLARE @start datetime2 = SYSDATETIME();
    DECLARE @rows_read int, @rows_ins int, @err_no int, @err_msg nvarchar(4000);

    BEGIN TRY
        SELECT @rows_read = COUNT(*) FROM lnd.product;

        TRUNCATE TABLE stg.product;

        INSERT INTO stg.product
            (product_src_id, product_name, category, subcategory, brand,
             list_price, unit_cost, status, source_modified_at, load_batch_id)
        SELECT
            UPPER(LTRIM(RTRIM(product_src_id))),
            LTRIM(RTRIM(product_name)),
            ISNULL(NULLIF(LTRIM(RTRIM(category)), ''),    'UNCATEGORISED'),
            ISNULL(NULLIF(LTRIM(RTRIM(subcategory)), ''), 'UNCATEGORISED'),
            ISNULL(NULLIF(LTRIM(RTRIM(brand)), ''),       'UNKNOWN'),
            CONVERT(decimal(18,2), ISNULL(NULLIF(list_price, ''), '0')),
            CONVERT(decimal(18,2), ISNULL(NULLIF(unit_cost, ''),  '0')),
            UPPER(ISNULL(status, 'ACTIVE')),
            CONVERT(datetime2, NULLIF(modified_at, '')),
            @batch_id
        FROM lnd.product
        WHERE extract_id = (SELECT MAX(extract_id) FROM lnd.product)
          AND UPPER(ISNULL(status, '')) <> 'TEST';

        SET @rows_ins = @@ROWCOUNT;

        EXEC etl.usp_write_audit @batch_id = @batch_id, @procedure_name = @proc, @step_name = 'load stg.product',
             @start_time = @start, @status = 'SUCCESS', @rows_read = @rows_read, @rows_inserted = @rows_ins,
             @rows_rejected = 0;
    END TRY
    BEGIN CATCH
        SET @err_no = ERROR_NUMBER();
        SET @err_msg = ERROR_MESSAGE();
        EXEC etl.usp_write_audit @batch_id = @batch_id, @procedure_name = @proc, @step_name = 'load stg.product',
             @start_time = @start, @status = 'FAILED', @error_number = @err_no, @error_message = @err_msg;
        THROW;
    END CATCH
END
```

## stg.usp_load_shipments.sql

**Path:** `procedures/stg/stg.usp_load_shipments.sql`

```sql
/* Shreds carrier XML. Expected shape:
   <Shipment id="S1" carrier="UPS">
     <Order ref="O1"/><Order ref="O2"/>
     <Events><Event type="SHIPPED" ts="2026-01-02T10:00:00"/><Event type="DELIVERED" ts="..."/></Events>
     <Promise by="2026-01-05T00:00:00"/>
     <Parcel weightKg="2.300"/>
   </Shipment>                                                                    */
CREATE OR ALTER PROCEDURE stg.usp_load_shipments
    @batch_id int
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    DECLARE @proc sysname = OBJECT_SCHEMA_NAME(@@PROCID) + N'.' + OBJECT_NAME(@@PROCID);
    DECLARE @start datetime2 = SYSDATETIME();
    DECLARE @wm datetime2, @new_wm datetime2;
    DECLARE @rows_read int, @rows_ins int, @rows_rej int, @err_no int, @err_msg nvarchar(4000);

    BEGIN TRY
        EXEC etl.usp_get_set_watermark @source_name = 'lnd.shipment', @current_value = @wm OUTPUT;

        SELECT @rows_read = COUNT(*) FROM lnd.shipment WHERE received_at > @wm;

        -- Bad records: documents without any <Order ref="..."/> cannot be attributed to an order.
        SELECT @rows_rej = COUNT(*)
        FROM lnd.shipment
        WHERE received_at > @wm
          AND payload_xml.exist('/Shipment/Order/@ref') = 0;

        BEGIN TRANSACTION;

            DELETE ss
            FROM stg.shipment AS ss
            WHERE EXISTS (SELECT 1 FROM lnd.shipment AS l
                          WHERE l.received_at > @wm AND l.shipment_src_id = ss.shipment_src_id);

            ;WITH latest AS (
                SELECT s.*,
                       ROW_NUMBER() OVER (PARTITION BY s.shipment_src_id ORDER BY s.received_at DESC, s.lnd_id DESC) AS rn
                FROM lnd.shipment AS s
                WHERE s.received_at > @wm
            )
            INSERT INTO stg.shipment
                (shipment_src_id, order_src_id, carrier, shipped_ts, delivered_ts, promised_ts, weight_kg, load_batch_id)
            SELECT DISTINCT
                   l.shipment_src_id,
                   o.ord.value('@ref', 'varchar(20)'),
                   o.ord.value('(../@carrier)[1]', 'varchar(30)'),
                   o.ord.value('(../Events/Event[@type="SHIPPED"]/@ts)[1]',   'datetime2'),
                   o.ord.value('(../Events/Event[@type="DELIVERED"]/@ts)[1]', 'datetime2'),
                   o.ord.value('(../Promise/@by)[1]',                         'datetime2'),
                   o.ord.value('(../Parcel/@weightKg)[1]',                    'decimal(9,3)'),
                   @batch_id
            FROM latest AS l
            CROSS APPLY l.payload_xml.nodes('/Shipment/Order') AS o(ord)
            WHERE l.rn = 1;

            SET @rows_ins = @@ROWCOUNT;

            SELECT @new_wm = MAX(received_at) FROM lnd.shipment WHERE received_at > @wm;
            IF @new_wm IS NOT NULL
                EXEC etl.usp_get_set_watermark @source_name = 'lnd.shipment', @new_value = @new_wm, @current_value = @wm OUTPUT;

        COMMIT TRANSACTION;

        EXEC etl.usp_write_audit @batch_id = @batch_id, @procedure_name = @proc, @step_name = 'load stg.shipment',
             @start_time = @start, @status = 'SUCCESS', @rows_read = @rows_read, @rows_inserted = @rows_ins,
             @rows_rejected = @rows_rej;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        SET @err_no = ERROR_NUMBER();
        SET @err_msg = ERROR_MESSAGE();
        EXEC etl.usp_write_audit @batch_id = @batch_id, @procedure_name = @proc, @step_name = 'load stg.shipment',
             @start_time = @start, @status = 'FAILED', @error_number = @err_no, @error_message = @err_msg;
        THROW;
    END CATCH
END
```

---

# SEED

_2 file(s)_

## 01_unknown_members.sql

**Path:** `seed/01_unknown_members.sql`

```sql
-- Unknown-member rows so facts never carry NULL surrogate keys.
SET IDENTITY_INSERT dim.customer ON;
IF NOT EXISTS (SELECT 1 FROM dim.customer WHERE customer_key = -1)
    INSERT INTO dim.customer (customer_key, customer_src_id, full_name, customer_segment, row_hash, effective_from, effective_to, is_current)
    VALUES (-1, 'UNKNOWN', N'Unknown Customer', 'OTHER', CAST(0 AS binary(32)), '1900-01-01', '9999-12-31', 1);
SET IDENTITY_INSERT dim.customer OFF;

SET IDENTITY_INSERT dim.product ON;
IF NOT EXISTS (SELECT 1 FROM dim.product WHERE product_key = -1)
    INSERT INTO dim.product (product_key, product_src_id, product_name, category, subcategory, brand, status, is_active)
    VALUES (-1, 'UNKNOWN', N'Unknown Product', N'UNCATEGORISED', N'UNCATEGORISED', N'UNKNOWN', 'UNKNOWN', 0);
SET IDENTITY_INSERT dim.product OFF;

IF NOT EXISTS (SELECT 1 FROM dim.date WHERE date_key = -1)
    INSERT INTO dim.date (date_key, full_date, day_of_week, day_name, day_of_month, day_of_year, iso_week,
                          month_number, month_name, quarter_number, calendar_year, is_weekend, is_holiday,
                          fiscal_year, fiscal_quarter, fiscal_period)
    VALUES (-1, '1900-01-01', 0, 'Unknown', 0, 0, 0, 0, 'Unknown', 0, 1900, 0, 0, 0, 0, 0);
```

## 02_pipeline_steps.sql

**Path:** `seed/02_pipeline_steps.sql`

```sql
-- Execution order consumed by etl.usp_run_daily_load.
INSERT INTO etl.pipeline_step (step_order, step_name, proc_name, target_table, max_retries, continue_on_error)
VALUES
 ( 10, 'stg_product',      'stg.usp_load_product',                     'stg.product',                     1, 0),
 ( 20, 'stg_customer',     'stg.usp_load_customer',                    'stg.customer',                    1, 0),
 ( 30, 'stg_orders',       'stg.usp_load_orders',                      'stg.order_header',                2, 0),
 ( 40, 'stg_payments',     'stg.usp_load_payments',                    'stg.payment',                     2, 0),
 ( 50, 'stg_shipments',    'stg.usp_load_shipments',                   'stg.shipment',                    2, 0),
 ( 60, 'dim_date',         'dim.usp_load_dim_date',                    'dim.date',                        0, 0),
 ( 70, 'dim_product',      'dim.usp_load_dim_product',                 'dim.product',                     2, 0),
 ( 80, 'dim_customer',     'dim.usp_load_dim_customer',                'dim.customer',                    2, 0),
 ( 90, 'fact_order_line',  'fact.usp_load_fact_order_line',            'fact.order_line',                 2, 0),
 (100, 'fact_payment',     'fact.usp_load_fact_payment',               'fact.payment',                    2, 0),
 (110, 'fact_shipment',    'fact.usp_load_fact_shipment',              'fact.shipment',                   2, 1),
 (120, 'agg_customer_rev', 'agg.usp_refresh_customer_monthly_revenue', 'agg.customer_monthly_revenue',   1, 1);
```
