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
