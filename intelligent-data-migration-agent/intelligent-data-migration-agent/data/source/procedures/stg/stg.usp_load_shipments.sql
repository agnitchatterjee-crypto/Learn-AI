/* Shreds carrier XML. Expected shape:
   <Shipment id="S1" carrier="UPS">
     <Order ref="O1"/><Order ref="O2"/>
     <Events><Event type="SHIPPED" ts="2026-01-02T10:00:00"/><Event type="DELIVERED" ts="..."/></Events>
     <Promise by="2026-01-05T00:00:00"/>
     <Parcel weightKg="2.300"/>
   </Shipment>                                                                    */
CREATE OR ALTER PROCEDURE stg.usp_load_shipments
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
        EXEC etl.usp_get_set_watermark @source_name = 'lnd.shipment', @current_value = @wm OUTPUT;

        SELECT @rows_read = COUNT(*) FROM lnd.shipment WHERE received_at > @wm;

        -- Bad records: documents without any <Order ref="..."/> cannot be attributed to an order.
        SELECT @rows_rej = COUNT(*)
        FROM lnd.shipment
        WHERE received_at > @wm
          AND payload_xml.exist('/Shipment/Order/@ref') = 0;

        BEGIN TRANSACTION;

            DELETE ss
            FROM stg.shipment AS ss
            WHERE EXISTS (SELECT 1 FROM lnd.shipment AS l
                          WHERE l.received_at > @wm AND l.shipment_src_id = ss.shipment_src_id);

            ;WITH latest AS (
                SELECT s.*,
                       ROW_NUMBER() OVER (PARTITION BY s.shipment_src_id ORDER BY s.received_at DESC, s.lnd_id DESC) AS rn
                FROM lnd.shipment AS s
                WHERE s.received_at > @wm
            )
            INSERT INTO stg.shipment
                (shipment_src_id, order_src_id, carrier, shipped_ts, delivered_ts, promised_ts, weight_kg, load_batch_id)
            SELECT DISTINCT
                   l.shipment_src_id,
                   o.ord.value('@ref', 'varchar(20)'),
                   o.ord.value('(../@carrier)[1]', 'varchar(30)'),
                   o.ord.value('(../Events/Event[@type="SHIPPED"]/@ts)[1]',   'datetime2'),
                   o.ord.value('(../Events/Event[@type="DELIVERED"]/@ts)[1]', 'datetime2'),
                   o.ord.value('(../Promise/@by)[1]',                         'datetime2'),
                   o.ord.value('(../Parcel/@weightKg)[1]',                    'decimal(9,3)'),
                   @batch_id
            FROM latest AS l
            CROSS APPLY l.payload_xml.nodes('/Shipment/Order') AS o(ord)
            WHERE l.rn = 1;

            SET @rows_ins = @@ROWCOUNT;

            SELECT @new_wm = MAX(received_at) FROM lnd.shipment WHERE received_at > @wm;
            IF @new_wm IS NOT NULL
                EXEC etl.usp_get_set_watermark @source_name = 'lnd.shipment', @new_value = @new_wm, @current_value = @wm OUTPUT;

        COMMIT TRANSACTION;

        EXEC etl.usp_write_audit @batch_id = @batch_id, @procedure_name = @proc, @step_name = 'load stg.shipment',
             @start_time = @start, @status = 'SUCCESS', @rows_read = @rows_read, @rows_inserted = @rows_ins,
             @rows_rejected = @rows_rej;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        SET @err_no = ERROR_NUMBER();
        SET @err_msg = ERROR_MESSAGE();
        EXEC etl.usp_write_audit @batch_id = @batch_id, @procedure_name = @proc, @step_name = 'load stg.shipment',
             @start_time = @start, @status = 'FAILED', @error_number = @err_no, @error_message = @err_msg;
        THROW;
    END CATCH
END
