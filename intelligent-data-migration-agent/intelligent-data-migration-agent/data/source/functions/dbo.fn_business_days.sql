/* Business days elapsed after @start_date up to and including @end_date,
   excluding weekends and rows flagged is_holiday in dim.date.
   Same day = 0. Returns NULL when @end_date < @start_date.
   Migration notes: relies on DATENAME/DATEFIRST (language dependent) and a table lookup
   inside a scalar UDF (row-by-row cost on SQL Server). */
CREATE OR ALTER FUNCTION dbo.fn_business_days (@start_date date, @end_date date)
RETURNS int
AS
BEGIN
    IF @start_date IS NULL OR @end_date IS NULL OR @end_date < @start_date
        RETURN NULL;

    DECLARE @s date = DATEADD(day, 1, @start_date);
    IF @s > @end_date
        RETURN 0;

    DECLARE @days int = DATEDIFF(day, @s, @end_date) + 1;
    DECLARE @weekend_days int =
          (DATEDIFF(week, @s, @end_date) * 2)
        + CASE WHEN DATENAME(weekday, @s)        = 'Sunday'   THEN 1 ELSE 0 END
        + CASE WHEN DATENAME(weekday, @end_date) = 'Saturday' THEN 1 ELSE 0 END;

    DECLARE @holidays int;
    SELECT @holidays = COUNT(*)
    FROM dim.date d
    WHERE d.full_date BETWEEN @s AND @end_date
      AND d.is_holiday = 1
      AND d.is_weekend = 0;

    RETURN @days - @weekend_days - ISNULL(@holidays, 0);
END
