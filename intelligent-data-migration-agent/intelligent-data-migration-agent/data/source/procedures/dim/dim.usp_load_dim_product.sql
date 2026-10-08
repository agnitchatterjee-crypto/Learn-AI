/* SCD Type 1 via MERGE, with soft delete for products that disappear from the source. */
CREATE OR ALTER PROCEDURE dim.usp_load_dim_product
    @batch_id int
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    DECLARE @proc sysname = OBJECT_SCHEMA_NAME(@@PROCID) + N'.' + OBJECT_NAME(@@PROCID);
    DECLARE @start datetime2 = SYSDATETIME();
    DECLARE @rows_read int, @ins int, @upd int, @err_no int, @err_msg nvarchar(4000);

    BEGIN TRY
        SELECT @rows_read = COUNT(*) FROM stg.product;

        -- Guard: an empty staging table would otherwise soft-delete the whole dimension.
        IF @rows_read = 0
            THROW 50020, 'stg.product is empty; refusing to deactivate the entire product dimension.', 1;

        CREATE TABLE #merge_log (
            action_name nvarchar(10) NOT NULL,
            product_key int          NOT NULL
        );

        MERGE dim.product AS t
        USING stg.product AS s
           ON t.product_src_id = s.product_src_id
        WHEN MATCHED AND (
                   ISNULL(t.product_name, '') <> ISNULL(s.product_name, '')
                OR ISNULL(t.category, '')     <> ISNULL(s.category, '')
                OR ISNULL(t.subcategory, '')  <> ISNULL(s.subcategory, '')
                OR ISNULL(t.brand, '')        <> ISNULL(s.brand, '')
                OR ISNULL(t.list_price, -1)   <> ISNULL(s.list_price, -1)
                OR ISNULL(t.unit_cost, -1)    <> ISNULL(s.unit_cost, -1)
                OR ISNULL(t.status, '')       <> ISNULL(s.status, '')
                OR t.is_active                <> IIF(s.status = 'ACTIVE', 1, 0)
             ) THEN
            UPDATE SET
                t.product_name = s.product_name,
                t.category     = s.category,
                t.subcategory  = s.subcategory,
                t.brand        = s.brand,
                t.list_price   = s.list_price,
                t.unit_cost    = s.unit_cost,
                t.status       = s.status,
                t.is_active    = IIF(s.status = 'ACTIVE', 1, 0),
                t.updated_at   = SYSDATETIME()
        WHEN NOT MATCHED BY TARGET THEN
            INSERT (product_src_id, product_name, category, subcategory, brand, list_price, unit_cost, status, is_active)
            VALUES (s.product_src_id, s.product_name, s.category, s.subcategory, s.brand, s.list_price, s.unit_cost,
                    s.status, IIF(s.status = 'ACTIVE', 1, 0))
        WHEN NOT MATCHED BY SOURCE AND t.product_key > 0 AND t.is_active = 1 THEN
            UPDATE SET t.is_active = 0, t.updated_at = SYSDATETIME()
        OUTPUT $action, inserted.product_key INTO #merge_log (action_name, product_key);

        SELECT @ins = COUNT(*) FROM #merge_log WHERE action_name = 'INSERT';
        SELECT @upd = COUNT(*) FROM #merge_log WHERE action_name = 'UPDATE';

        EXEC etl.usp_write_audit @batch_id = @batch_id, @procedure_name = @proc, @step_name = 'merge dim.product (SCD1)',
             @start_time = @start, @status = 'SUCCESS', @rows_read = @rows_read, @rows_inserted = @ins, @rows_updated = @upd;
    END TRY
    BEGIN CATCH
        SET @err_no = ERROR_NUMBER();
        SET @err_msg = ERROR_MESSAGE();
        EXEC etl.usp_write_audit @batch_id = @batch_id, @procedure_name = @proc, @step_name = 'merge dim.product (SCD1)',
             @start_time = @start, @status = 'FAILED', @error_number = @err_no, @error_message = @err_msg;
        THROW;
    END CATCH
END
