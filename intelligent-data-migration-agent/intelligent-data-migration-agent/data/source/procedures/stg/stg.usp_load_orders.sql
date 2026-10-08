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
