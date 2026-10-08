/* Inline table-valued function. Fiscal year starts 1 April and is named for the
   calendar year in which it ends (April 2025 -> FY2026, period 1). */
CREATE OR ALTER FUNCTION dbo.fn_fiscal_period (@d date)
RETURNS TABLE
AS
RETURN
(
    SELECT
        CAST(YEAR(@d) + CASE WHEN MONTH(@d) >= 4 THEN 1 ELSE 0 END AS smallint) AS fiscal_year,
        CAST(((MONTH(@d) + 8) % 12) / 3 + 1 AS tinyint)                          AS fiscal_quarter,
        CAST(((MONTH(@d) + 8) % 12) + 1 AS tinyint)                              AS fiscal_period
);
