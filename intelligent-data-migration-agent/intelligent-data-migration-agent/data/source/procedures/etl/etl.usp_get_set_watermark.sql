CREATE OR ALTER PROCEDURE etl.usp_get_set_watermark
    @source_name   varchar(100),
    @new_value     datetime2 = NULL,
    @current_value datetime2 = NULL OUTPUT
AS
BEGIN
    SET NOCOUNT ON;

    IF NOT EXISTS (SELECT 1 FROM etl.watermark WHERE source_name = @source_name)
        INSERT INTO etl.watermark (source_name, last_value) VALUES (@source_name, '1900-01-01');

    SELECT @current_value = last_value
    FROM etl.watermark
    WHERE source_name = @source_name;

    IF @new_value IS NOT NULL AND @new_value > @current_value
    BEGIN
        UPDATE etl.watermark
        SET last_value = @new_value,
            updated_at = SYSDATETIME()
        WHERE source_name = @source_name;

        IF @@ROWCOUNT <> 1
            THROW 50010, 'Watermark update did not affect exactly one row.', 1;

        SET @current_value = @new_value;
    END
END
