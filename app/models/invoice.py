from pydantic import BaseModel
from typing import List, Optional

class InvoiceItem(BaseModel):
    description: str
    amount: float
    quantity: int

class RiskAssessment(BaseModel):
    is_suspicious: bool
    risk_score: float
    reason: Optional[str] = None
    gemini_explanation: Optional[str] = None
    graph_risk_signals: Optional[List[str]] = []

class Invoice(BaseModel):
    id: str
    filename: str
    vendor_name: str
    invoice_date: str
    total_amount: float
    items: List[InvoiceItem]
    risk_assessment: Optional[RiskAssessment] = None
