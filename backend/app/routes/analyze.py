from fastapi import APIRouter, Depends
from functools import lru_cache
from app.models.invoice import Invoice, AnomalyResult
from app.services.anomaly_service import AnomalyDetector
from app.core.config import settings

router = APIRouter()

# Dependency to get the anomaly detector with caching (Singleton)
@lru_cache()
def get_anomaly_detector():
    return AnomalyDetector(use_mock=settings.USE_MOCK_MODEL)

@router.post("/analyze", response_model=AnomalyResult)
def analyze_invoice(invoice: Invoice, detector: AnomalyDetector = Depends(get_anomaly_detector)):
    """
    Analyzes an invoice for anomalies using BigQuery ML (or mock implementation).
    """
    return detector.detect(invoice)
