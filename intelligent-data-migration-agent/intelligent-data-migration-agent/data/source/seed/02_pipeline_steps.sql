-- Execution order consumed by etl.usp_run_daily_load.
INSERT INTO etl.pipeline_step (step_order, step_name, proc_name, target_table, max_retries, continue_on_error)
VALUES
 ( 10, 'stg_product',      'stg.usp_load_product',                     'stg.product',                     1, 0),
 ( 20, 'stg_customer',     'stg.usp_load_customer',                    'stg.customer',                    1, 0),
 ( 30, 'stg_orders',       'stg.usp_load_orders',                      'stg.order_header',                2, 0),
 ( 40, 'stg_payments',     'stg.usp_load_payments',                    'stg.payment',                     2, 0),
 ( 50, 'stg_shipments',    'stg.usp_load_shipments',                   'stg.shipment',                    2, 0),
 ( 60, 'dim_date',         'dim.usp_load_dim_date',                    'dim.date',                        0, 0),
 ( 70, 'dim_product',      'dim.usp_load_dim_product',                 'dim.product',                     2, 0),
 ( 80, 'dim_customer',     'dim.usp_load_dim_customer',                'dim.customer',                    2, 0),
 ( 90, 'fact_order_line',  'fact.usp_load_fact_order_line',            'fact.order_line',                 2, 0),
 (100, 'fact_payment',     'fact.usp_load_fact_payment',               'fact.payment',                    2, 0),
 (110, 'fact_shipment',    'fact.usp_load_fact_shipment',              'fact.shipment',                   2, 1),
 (120, 'agg_customer_rev', 'agg.usp_refresh_customer_monthly_revenue', 'agg.customer_monthly_revenue',   1, 1);
