CREATE OR ALTER PROCEDURE stg.usp_load_product
    @batch_id int
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    DECLARE @proc sysname = OBJECT_SCHEMA_NAME(@@PROCID) + N'.' + OBJECT_NAME(@@PROCID);
    DECLARE @start datetime2 = SYSDATETIME();
    DECLARE @rows_read int, @rows_ins int, @err_no int, @err_msg nvarchar(4000);

    BEGIN TRY
        SELECT @rows_read = COUNT(*) FROM lnd.product;

        TRUNCATE TABLE stg.product;

        INSERT INTO stg.product
            (product_src_id, product_name, category, subcategory, brand,
             list_price, unit_cost, status, source_modified_at, load_batch_id)
        SELECT
            UPPER(LTRIM(RTRIM(product_src_id))),
            LTRIM(RTRIM(product_name)),
            ISNULL(NULLIF(LTRIM(RTRIM(category)), ''),    'UNCATEGORISED'),
            ISNULL(NULLIF(LTRIM(RTRIM(subcategory)), ''), 'UNCATEGORISED'),
            ISNULL(NULLIF(LTRIM(RTRIM(brand)), ''),       'UNKNOWN'),
            CONVERT(decimal(18,2), ISNULL(NULLIF(list_price, ''), '0')),
            CONVERT(decimal(18,2), ISNULL(NULLIF(unit_cost, ''),  '0')),
            UPPER(ISNULL(status, 'ACTIVE')),
            CONVERT(datetime2, NULLIF(modified_at, '')),
            @batch_id
        FROM lnd.product
        WHERE extract_id = (SELECT MAX(extract_id) FROM lnd.product)
          AND UPPER(ISNULL(status, '')) <> 'TEST';

        SET @rows_ins = @@ROWCOUNT;

        EXEC etl.usp_write_audit @batch_id = @batch_id, @procedure_name = @proc, @step_name = 'load stg.product',
             @start_time = @start, @status = 'SUCCESS', @rows_read = @rows_read, @rows_inserted = @rows_ins,
             @rows_rejected = 0;
    END TRY
    BEGIN CATCH
        SET @err_no = ERROR_NUMBER();
        SET @err_msg = ERROR_MESSAGE();
        EXEC etl.usp_write_audit @batch_id = @batch_id, @procedure_name = @proc, @step_name = 'load stg.product',
             @start_time = @start, @status = 'FAILED', @error_number = @err_no, @error_message = @err_msg;
        THROW;
    END CATCH
END
