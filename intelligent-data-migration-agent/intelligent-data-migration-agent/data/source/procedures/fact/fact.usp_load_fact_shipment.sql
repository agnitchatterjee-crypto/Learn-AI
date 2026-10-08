/* Loads shipments with SLA measures. Uses the scalar UDF dbo.fn_business_days (row-by-row on SQL Server)
   and unknown-member date keys (-1) for missing delivery / promise dates. */
CREATE OR ALTER PROCEDURE fact.usp_load_fact_shipment
    @batch_id   int,
    @reprocess  bit  = 0,
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
            shipment_src_id        varchar(30)  NOT NULL,
            order_src_id           varchar(20)  NOT NULL,
            customer_key           int          NOT NULL,
            carrier                varchar(30)  NULL,
            ship_date_key          int          NOT NULL,
            delivered_date_key     int          NOT NULL,
            promised_date_key      int          NOT NULL,
            weight_kg              decimal(9,3) NULL,
            transit_business_days  int          NULL,
            promised_business_days int          NULL,
            delivery_status        varchar(20)  NOT NULL,
            is_sla_breach          bit          NOT NULL,
            PRIMARY KEY (shipment_src_id, order_src_id)
        );
        CREATE TABLE #merge_log (action_name nvarchar(10) NOT NULL);

        INSERT INTO #src
        SELECT s.shipment_src_id,
               s.order_src_id,
               ISNULL(oc.customer_key, -1),
               s.carrier,
               ISNULL(dsh.date_key, -1),
               ISNULL(ddl.date_key, -1),
               ISNULL(dpr.date_key, -1),
               s.weight_kg,
               CASE WHEN s.delivered_ts IS NOT NULL
                    THEN dbo.fn_business_days(CAST(s.shipped_ts AS date), CAST(s.delivered_ts AS date)) END,
               CASE WHEN s.promised_ts IS NOT NULL
                    THEN dbo.fn_business_days(CAST(s.shipped_ts AS date), CAST(s.promised_ts AS date)) END,
               CASE WHEN s.delivered_ts IS NOT NULL                         THEN 'DELIVERED'
                    WHEN s.promised_ts  < @as_of_date                       THEN 'LATE_UNDELIVERED'
                    WHEN s.shipped_ts   IS NOT NULL                         THEN 'IN_TRANSIT'
                    ELSE 'PENDING' END,
               CASE WHEN s.delivered_ts IS NOT NULL AND CAST(s.delivered_ts AS date) > CAST(s.promised_ts AS date) THEN 1
                    WHEN s.delivered_ts IS NULL     AND CAST(s.promised_ts  AS date) < @as_of_date                THEN 1
                    ELSE 0 END
        FROM stg.shipment AS s
        LEFT JOIN dim.date AS dsh ON dsh.full_date = CAST(s.shipped_ts   AS date)
        LEFT JOIN dim.date AS ddl ON ddl.full_date = CAST(s.delivered_ts AS date)
        LEFT JOIN dim.date AS dpr ON dpr.full_date = CAST(s.promised_ts  AS date)
        OUTER APPLY (SELECT TOP (1) f.customer_key
                     FROM fact.order_line AS f
                     WHERE f.order_src_id = s.order_src_id) AS oc
        WHERE s.load_batch_id = @batch_id OR @reprocess = 1;

        SET @rows_read = @@ROWCOUNT;

        MERGE fact.shipment AS t
        USING #src AS s
           ON t.shipment_src_id = s.shipment_src_id AND t.order_src_id = s.order_src_id
        WHEN MATCHED THEN
            UPDATE SET
                t.customer_key           = s.customer_key,
                t.carrier                = s.carrier,
                t.ship_date_key          = s.ship_date_key,
                t.delivered_date_key     = s.delivered_date_key,
                t.promised_date_key      = s.promised_date_key,
                t.weight_kg              = s.weight_kg,
                t.transit_business_days  = s.transit_business_days,
                t.promised_business_days = s.promised_business_days,
                t.delivery_status        = s.delivery_status,
                t.is_sla_breach          = s.is_sla_breach,
                t.load_batch_id          = @batch_id,
                t.updated_at             = SYSDATETIME()
        WHEN NOT MATCHED BY TARGET THEN
            INSERT (shipment_src_id, order_src_id, customer_key, carrier, ship_date_key, delivered_date_key,
                    promised_date_key, weight_kg, transit_business_days, promised_business_days,
                    delivery_status, is_sla_breach, load_batch_id)
            VALUES (s.shipment_src_id, s.order_src_id, s.customer_key, s.carrier, s.ship_date_key, s.delivered_date_key,
                    s.promised_date_key, s.weight_kg, s.transit_business_days, s.promised_business_days,
                    s.delivery_status, s.is_sla_breach, @batch_id)
        OUTPUT $action INTO #merge_log (action_name);

        SELECT @ins = COUNT(*) FROM #merge_log WHERE action_name = 'INSERT';
        SELECT @upd = COUNT(*) FROM #merge_log WHERE action_name = 'UPDATE';

        EXEC etl.usp_write_audit @batch_id = @batch_id, @procedure_name = @proc, @step_name = 'load fact.shipment',
             @start_time = @start, @status = 'SUCCESS', @rows_read = @rows_read, @rows_inserted = @ins, @rows_updated = @upd;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        SET @err_no = ERROR_NUMBER();
        SET @err_msg = ERROR_MESSAGE();
        EXEC etl.usp_write_audit @batch_id = @batch_id, @procedure_name = @proc, @step_name = 'load fact.shipment',
             @start_time = @start, @status = 'FAILED', @error_number = @err_no, @error_message = @err_msg;
        THROW;
    END CATCH
END
