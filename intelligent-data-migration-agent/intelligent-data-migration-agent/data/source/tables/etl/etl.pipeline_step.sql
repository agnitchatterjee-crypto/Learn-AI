CREATE TABLE etl.pipeline_step (
    step_order        int           NOT NULL,
    step_name         varchar(100)  NOT NULL,
    proc_name         nvarchar(300) NOT NULL,   -- invoked dynamically by etl.usp_run_daily_load
    target_table      nvarchar(300) NULL,       -- used for the post-step row-count check
    is_enabled        bit           NOT NULL CONSTRAINT df_etl_pipeline_step_enabled DEFAULT 1,
    max_retries       int           NOT NULL CONSTRAINT df_etl_pipeline_step_retries DEFAULT 2,
    continue_on_error bit           NOT NULL CONSTRAINT df_etl_pipeline_step_coe DEFAULT 0,
    CONSTRAINT pk_etl_pipeline_step PRIMARY KEY CLUSTERED (step_order),
    CONSTRAINT uq_etl_pipeline_step_name UNIQUE (step_name)
);
