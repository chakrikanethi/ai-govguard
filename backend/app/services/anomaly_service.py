import os
from typing import Any
from app.models.invoice import Invoice, AnomalyResult
from app.core.config import settings

# Try importing BigQuery, handle if not available (though it is in requirements)
try:
    from google.cloud import bigquery
except ImportError:
    bigquery = None

# Try importing sklearn for mock implementation
try:
    from sklearn.ensemble import IsolationForest
    import numpy as np
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

class AnomalyDetector:
    def __init__(self, use_mock: bool = True):
        self.use_mock = use_mock
        self.client = None
        if not self.use_mock and bigquery:
            # In a real app, credentials would be handled by environment variables
            try:
                self.client = bigquery.Client(project=settings.PROJECT_ID)
            except Exception as e:
                # Fallback if creds missing in dev
                print(f"Failed to init BigQuery client: {e}")
                self.client = None

        # Pre-train a small mock model for demonstration if using mock
        self.mock_model = None
        if self.use_mock and SKLEARN_AVAILABLE:
            self._train_mock_model()

    def _train_mock_model(self):
        """Trains a lightweight Isolation Forest on synthetic data for mock purposes."""
        # Generate synthetic normal data: high frequency, low-ish amounts
        # We want the "Normal" cluster to be centered around our "Normal" scaling point.
        # Normal scaling point:
        # Amount 1000 -> (1000-5000)/2500 = -1.6
        # Freq 50 -> (50-50)/25 = 0

        rng = np.random.RandomState(42)

        # Create a cluster around (-1.6, 0) for normal invoices
        X_normal = 0.5 * rng.randn(100, 2) + np.array([-1.6, 0])

        # Add some noise/outliers to make the model realistic
        X_normal_2 = 0.5 * rng.randn(50, 2) + np.array([0, 0])

        X_train = np.r_[X_normal, X_normal_2]

        self.mock_model = IsolationForest(contamination=0.1, random_state=42)
        self.mock_model.fit(X_train)

    def detect(self, invoice: Invoice) -> AnomalyResult:
        if self.use_mock:
            return self._detect_mock(invoice)
        else:
            return self._detect_real(invoice)

    def _detect_real(self, invoice: Invoice) -> AnomalyResult:
        """
        Generates BigQuery SQL to detect anomalies.
        """
        if not self.client:
             # If client failed to init (e.g. no creds), fallback to mock with a warning detail
             result = self._detect_mock(invoice)
             result.details = f"Fallback to Mock (BQ Client missing): {result.details}"
             return result

        model_ref = f"`{settings.PROJECT_ID}.{settings.DATASET_ID}.{settings.MODEL_NAME}`"

        # SQL query to predict anomaly score using a pre-trained BQML model
        # Contamination set to 0.05 (5%)
        query = f"""
            SELECT
              *
            FROM
              ML.DETECT_ANOMALIES(MODEL {model_ref},
                STRUCT(
                  {invoice.amount} AS amount,
                  {invoice.vendor_frequency} AS vendor_frequency
                ),
                STRUCT(0.05 AS contamination)
              )
        """

        try:
            query_job = self.client.query(query)
            results = query_job.result()
            row = next(results)

            # Assuming schema returns is_anomaly (bool) and anomaly_score (float)
            is_anomaly = row.is_anomaly
            score = row.anomaly_score

            risk_level = "High" if is_anomaly else "Low"
            if not is_anomaly and score > 0.5: # Arbitrary threshold for Medium
                risk_level = "Medium"

            return AnomalyResult(
                invoice_id=invoice.invoice_id,
                anomaly_score=score,
                is_anomaly=is_anomaly,
                risk_level=risk_level,
                details="Detected via BigQuery ML"
            )
        except Exception as e:
            # Fallback if query fails
             result = self._detect_mock(invoice)
             result.details = f"Fallback to Mock (BQ Error: {str(e)}): {result.details}"
             return result

    def _detect_mock(self, invoice: Invoice) -> AnomalyResult:
        """
        Uses sklearn Isolation Forest or simple heuristics.
        """
        if SKLEARN_AVAILABLE and self.mock_model:
            # Normalize inputs roughly to the mock training space for demo
            scaled_amount = (invoice.amount - 5000) / 2500
            scaled_freq = (invoice.vendor_frequency - 50) / 25

            pred = self.mock_model.predict([[scaled_amount, scaled_freq]])[0]
            score = self.mock_model.score_samples([[scaled_amount, scaled_freq]])[0]

            is_anomaly = pred == -1
            risk_score = -score

            risk_level = "High" if is_anomaly else "Low"
            if not is_anomaly and risk_score > 0.6:
                risk_level = "Medium"

            return AnomalyResult(
                invoice_id=invoice.invoice_id,
                anomaly_score=float(risk_score),
                is_anomaly=bool(is_anomaly),
                risk_level=risk_level,
                details="Detected via Mock Isolation Forest"
            )
        else:
            # Fallback heuristic
            is_anomaly = False
            risk_level = "Low"
            score = 0.0

            if invoice.amount > 5000 and invoice.vendor_frequency < 2:
                is_anomaly = True
                risk_level = "High"
                score = 0.9
            elif invoice.amount > 3000:
                risk_level = "Medium"
                score = 0.6

            return AnomalyResult(
                invoice_id=invoice.invoice_id,
                anomaly_score=score,
                is_anomaly=is_anomaly,
                risk_level=risk_level,
                details="Detected via Heuristic Rule"
            )

    @staticmethod
    def get_create_model_sql() -> str:
        """Returns the SQL to create the model in BigQuery."""
        model_ref = f"`{settings.PROJECT_ID}.{settings.DATASET_ID}.{settings.MODEL_NAME}`"
        table_ref = f"`{settings.PROJECT_ID}.{settings.DATASET_ID}.invoice_history`"

        return f"""
        CREATE OR REPLACE MODEL {model_ref}
        OPTIONS(
          model_type='ISOLATION_FOREST',
          contamination=0.05
        ) AS
        SELECT
          amount,
          vendor_frequency
        FROM
          {table_ref}
        """
