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
