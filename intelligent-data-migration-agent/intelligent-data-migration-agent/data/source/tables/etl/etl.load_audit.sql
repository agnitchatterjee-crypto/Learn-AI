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
