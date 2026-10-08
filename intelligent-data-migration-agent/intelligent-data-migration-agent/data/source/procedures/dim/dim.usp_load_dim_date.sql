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
