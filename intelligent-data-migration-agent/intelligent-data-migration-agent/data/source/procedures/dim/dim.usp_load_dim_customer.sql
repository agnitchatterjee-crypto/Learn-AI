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
