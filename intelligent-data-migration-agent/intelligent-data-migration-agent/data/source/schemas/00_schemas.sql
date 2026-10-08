/* Synthetic retail order-to-cash platform (SQL Server 2017+).
   lnd  = landing (raw extracts, loaded by upstream ingestion)
   stg  = cleansed staging
   ref  = reference data
   dim / fact / agg = warehouse layers
   rpt  = reporting views
   etl  = control tables and orchestration                      */
IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = 'lnd')  EXEC('CREATE SCHEMA lnd');
IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = 'stg')  EXEC('CREATE SCHEMA stg');
IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = 'ref')  EXEC('CREATE SCHEMA ref');
IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = 'dim')  EXEC('CREATE SCHEMA dim');
IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = 'fact') EXEC('CREATE SCHEMA fact');
IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = 'agg')  EXEC('CREATE SCHEMA agg');
IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = 'rpt')  EXEC('CREATE SCHEMA rpt');
IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = 'etl')  EXEC('CREATE SCHEMA etl');
