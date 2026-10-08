/* Converts an amount to USD using the latest rate on or before @rate_date.
   Returns NULL when no rate exists (callers treat that as a reject). */
CREATE OR ALTER FUNCTION dbo.fn_convert_currency (@amount decimal(18,4), @from_currency char(3), @rate_date date)
RETURNS decimal(18,4)
AS
BEGIN
    IF @amount IS NULL
        RETURN NULL;
    IF @from_currency = 'USD'
        RETURN @amount;

    DECLARE @rate decimal(18,8);
    SELECT TOP (1) @rate = r.rate
    FROM ref.currency_rate r
    WHERE r.from_currency = @from_currency
      AND r.to_currency   = 'USD'
      AND r.rate_date    <= @rate_date
    ORDER BY r.rate_date DESC;

    RETURN CASE WHEN @rate IS NULL THEN NULL ELSE ROUND(@amount * @rate, 4) END;
END
