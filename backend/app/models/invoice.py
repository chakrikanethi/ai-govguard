from pydantic import BaseModel, Field
from typing import Optional

class Invoice(BaseModel):
    invoice_id: str
    amount: float
    vendor_id: str
    vendor_frequency: int = Field(..., description="Number of times this vendor has been seen in the past")

class AnomalyResult(BaseModel):
    invoice_id: str
    anomaly_score: float
    is_anomaly: bool
    risk_level: str  # e.g., "Low", "Medium", "High"
    details: Optional[str] = None
