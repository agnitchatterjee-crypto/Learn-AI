/* Parses gateway JSON. One landing document can allocate a payment across several orders. */
CREATE OR ALTER PROCEDURE stg.usp_load_payments
    @batch_id int
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    DECLARE @proc sysname = OBJECT_SCHEMA_NAME(@@PROCID) + N'.' + OBJECT_NAME(@@PROCID);
    DECLARE @start datetime2 = SYSDATETIME();
    DECLARE @wm datetime2, @new_wm datetime2;
    DECLARE @rows_read int, @rows_ins int, @rows_rej int, @err_no int, @err_msg nvarchar(4000);

    BEGIN TRY
        EXEC etl.usp_get_set_watermark @source_name = 'lnd.payment', @current_value = @wm OUTPUT;

        SELECT @rows_read = COUNT(*) FROM lnd.payment WHERE received_at > @wm;
        SELECT @rows_rej  = COUNT(*) FROM lnd.payment WHERE received_at > @wm AND ISJSON(payload) <> 1;

        BEGIN TRANSACTION;

            DELETE sp
            FROM stg.payment AS sp
            WHERE EXISTS (SELECT 1 FROM lnd.payment AS l
                          WHERE l.received_at > @wm AND l.payment_src_id = sp.payment_src_id);

            ;WITH latest AS (
                SELECT p.*,
                       ROW_NUMBER() OVER (PARTITION BY p.payment_src_id ORDER BY p.received_at DESC, p.lnd_id DESC) AS rn
                FROM lnd.payment AS p
                WHERE p.received_at > @wm
            )
            INSERT INTO stg.payment
                (payment_src_id, order_src_id, method, payment_type, amount, currency_code, status,
                 event_ts, gateway_ref, load_batch_id)
            SELECT l.payment_src_id,
                   a.order_id,
                   UPPER(j.method),
                   UPPER(j.payment_type),
                   a.amount,
                   UPPER(j.currency_code),
                   UPPER(j.status),
                   j.event_ts,
                   j.gateway_ref,
                   @batch_id
            FROM latest AS l
            CROSS APPLY OPENJSON(CASE WHEN ISJSON(l.payload) = 1 THEN l.payload END)
                WITH (
                    method        varchar(20)  '$.method',
                    payment_type  varchar(20)  '$.type',
                    currency_code char(3)      '$.currency',
                    status        varchar(20)  '$.status',
                    event_ts      datetime2    '$.event_ts',
                    gateway_ref   varchar(50)  '$.gateway.ref',
                    allocations   nvarchar(max) '$.allocations' AS JSON
                ) AS j
            CROSS APPLY OPENJSON(j.allocations)
                WITH (
                    order_id varchar(20)   '$.order_id',
                    amount   decimal(18,2) '$.amount'
                ) AS a
            WHERE l.rn = 1
              AND a.order_id IS NOT NULL
              AND a.amount IS NOT NULL;

            SET @rows_ins = @@ROWCOUNT;

            SELECT @new_wm = MAX(received_at) FROM lnd.payment WHERE received_at > @wm;
            IF @new_wm IS NOT NULL
                EXEC etl.usp_get_set_watermark @source_name = 'lnd.payment', @new_value = @new_wm, @current_value = @wm OUTPUT;

        COMMIT TRANSACTION;

        EXEC etl.usp_write_audit @batch_id = @batch_id, @procedure_name = @proc, @step_name = 'load stg.payment',
             @start_time = @start, @status = 'SUCCESS', @rows_read = @rows_read, @rows_inserted = @rows_ins,
             @rows_rejected = @rows_rej;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        SET @err_no = ERROR_NUMBER();
        SET @err_msg = ERROR_MESSAGE();
        EXEC etl.usp_write_audit @batch_id = @batch_id, @procedure_name = @proc, @step_name = 'load stg.payment',
             @start_time = @start, @status = 'FAILED', @error_number = @err_no, @error_message = @err_msg;
        THROW;
    END CATCH
END
