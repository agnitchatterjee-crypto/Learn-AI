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
