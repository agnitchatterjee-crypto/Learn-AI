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
