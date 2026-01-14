-- SQL to create the BigQuery ML Anomaly Detection Model
-- Replace variables as needed if running manually outside the app context

CREATE OR REPLACE MODEL `ai-govguard-dev.invoices.invoice_anomaly_model`
OPTIONS(
  model_type='ISOLATION_FOREST',
  contamination=0.05
) AS
SELECT
  amount,
  vendor_frequency
FROM
  `ai-govguard-dev.invoices.invoice_history`;
