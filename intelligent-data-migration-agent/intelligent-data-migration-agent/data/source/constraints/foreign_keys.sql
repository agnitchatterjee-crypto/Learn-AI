ALTER TABLE fact.order_line ADD CONSTRAINT fk_fact_order_line_date     FOREIGN KEY (order_date_key) REFERENCES dim.date (date_key);
ALTER TABLE fact.order_line ADD CONSTRAINT fk_fact_order_line_customer FOREIGN KEY (customer_key)   REFERENCES dim.customer (customer_key);
ALTER TABLE fact.order_line ADD CONSTRAINT fk_fact_order_line_product  FOREIGN KEY (product_key)    REFERENCES dim.product (product_key);

ALTER TABLE fact.payment ADD CONSTRAINT fk_fact_payment_date     FOREIGN KEY (payment_date_key) REFERENCES dim.date (date_key);
ALTER TABLE fact.payment ADD CONSTRAINT fk_fact_payment_customer FOREIGN KEY (customer_key)     REFERENCES dim.customer (customer_key);

ALTER TABLE fact.shipment ADD CONSTRAINT fk_fact_shipment_customer  FOREIGN KEY (customer_key)       REFERENCES dim.customer (customer_key);
ALTER TABLE fact.shipment ADD CONSTRAINT fk_fact_shipment_ship_date FOREIGN KEY (ship_date_key)      REFERENCES dim.date (date_key);
ALTER TABLE fact.shipment ADD CONSTRAINT fk_fact_shipment_deliv_dt  FOREIGN KEY (delivered_date_key) REFERENCES dim.date (date_key);
ALTER TABLE fact.shipment ADD CONSTRAINT fk_fact_shipment_prom_dt   FOREIGN KEY (promised_date_key)  REFERENCES dim.date (date_key);

ALTER TABLE agg.customer_monthly_revenue ADD CONSTRAINT fk_agg_cmr_customer FOREIGN KEY (customer_key) REFERENCES dim.customer (customer_key);
