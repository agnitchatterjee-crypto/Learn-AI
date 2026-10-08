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
