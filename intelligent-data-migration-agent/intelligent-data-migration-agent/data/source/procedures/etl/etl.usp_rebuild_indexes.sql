/* Index maintenance driven by sys.dm_db_index_physical_stats, executed through a cursor and dynamic ALTER INDEX.
   Intended as a "retire, do not migrate" case: Snowflake has no user-managed indexes. */
CREATE OR ALTER PROCEDURE etl.usp_rebuild_indexes
    @reorganize_pct float = 10.0,
    @rebuild_pct    float = 30.0,
    @min_pages      int   = 1000,
    @dry_run        bit   = 1
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @schema_name sysname, @table_name sysname, @index_name sysname, @frag float, @sql nvarchar(max);

    DECLARE cur_idx CURSOR LOCAL FAST_FORWARD FOR
        SELECT s.name, t.name, i.name, ps.avg_fragmentation_in_percent
        FROM sys.dm_db_index_physical_stats(DB_ID(), NULL, NULL, NULL, 'LIMITED') AS ps
        JOIN sys.indexes AS i ON i.object_id = ps.object_id AND i.index_id = ps.index_id
        JOIN sys.tables  AS t ON t.object_id = ps.object_id
        JOIN sys.schemas AS s ON s.schema_id = t.schema_id
        WHERE ps.index_id > 0
          AND ps.page_count >= @min_pages
          AND ps.avg_fragmentation_in_percent >= @reorganize_pct
        ORDER BY ps.avg_fragmentation_in_percent DESC;

    OPEN cur_idx;
    FETCH NEXT FROM cur_idx INTO @schema_name, @table_name, @index_name, @frag;

    WHILE @@FETCH_STATUS = 0
    BEGIN
        SET @sql = N'ALTER INDEX ' + QUOTENAME(@index_name) + N' ON ' + QUOTENAME(@schema_name) + N'.' + QUOTENAME(@table_name)
                 + CASE WHEN @frag >= @rebuild_pct THEN N' REBUILD WITH (ONLINE = ON, SORT_IN_TEMPDB = ON);'
                        ELSE N' REORGANIZE;' END;

        IF @dry_run = 1
            PRINT @sql;
        ELSE
            EXEC sp_executesql @sql;

        FETCH NEXT FROM cur_idx INTO @schema_name, @table_name, @index_name, @frag;
    END

    CLOSE cur_idx;
    DEALLOCATE cur_idx;
END
