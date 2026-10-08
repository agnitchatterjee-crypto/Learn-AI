/* Trims, collapses repeated spaces and proper-cases a person name.
   Migration notes: WHILE loop character processing in a scalar UDF. */
CREATE OR ALTER FUNCTION dbo.fn_clean_name (@name nvarchar(200))
RETURNS nvarchar(200)
AS
BEGIN
    IF @name IS NULL
        RETURN NULL;

    DECLARE @s nvarchar(200) = LTRIM(RTRIM(@name));
    WHILE CHARINDEX('  ', @s) > 0
        SET @s = REPLACE(@s, '  ', ' ');

    DECLARE @i int = 1;
    DECLARE @len int = LEN(@s);
    DECLARE @out nvarchar(200) = N'';
    DECLARE @c nchar(1);
    DECLARE @prev nchar(1) = N' ';

    WHILE @i <= @len
    BEGIN
        SET @c = SUBSTRING(@s, @i, 1);
        SET @out = @out + CASE WHEN @prev IN (N' ', N'-', N'''') THEN UPPER(@c) ELSE LOWER(@c) END;
        SET @prev = @c;
        SET @i += 1;
    END

    RETURN NULLIF(@out, N'');
END
