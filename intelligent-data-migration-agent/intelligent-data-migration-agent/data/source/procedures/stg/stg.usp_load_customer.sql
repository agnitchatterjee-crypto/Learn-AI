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
