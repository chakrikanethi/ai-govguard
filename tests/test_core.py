import pytest
from app.core.document_processor import DocumentProcessor
from app.core.anomaly_detector import AnomalyDetector
from app.core.fraud_explainer import FraudExplainer
from app.models.invoice import Invoice, InvoiceItem

def test_document_processor():
    processor = DocumentProcessor()
    # Test normal invoice
    invoice = processor.process(None, "normal_invoice.pdf")
    assert invoice.filename == "normal_invoice.pdf"
    assert invoice.total_amount == 450.50
    assert invoice.vendor_name == "Office Supplies Co"

    # Test suspicious invoice
    suspicious_invoice = processor.process(None, "suspicious_invoice.pdf")
    assert suspicious_invoice.filename == "suspicious_invoice.pdf"
    assert suspicious_invoice.total_amount == 15000.00
    assert suspicious_invoice.vendor_name == "Shadow Corp"

def test_anomaly_detector():
    detector = AnomalyDetector()

    # Test normal invoice - should pass
    normal_invoice = Invoice(
        id="1", filename="test.pdf", vendor_name="Normal Co",
        invoice_date="2023-01-01", total_amount=100.00, items=[]
    )
    risk_normal = detector.detect(normal_invoice)
    assert risk_normal.is_suspicious is False
    assert risk_normal.risk_score == 0.0

    # Test high amount
    high_amount_invoice = Invoice(
        id="2", filename="high.pdf", vendor_name="Normal Co",
        invoice_date="2023-01-01", total_amount=20000.00, items=[]
    )
    risk_high = detector.detect(high_amount_invoice)
    assert risk_high.is_suspicious is True
    assert "exceeds threshold" in risk_high.reason

    # Test suspicious vendor
    vendor_invoice = Invoice(
        id="3", filename="vendor.pdf", vendor_name="Shadow Corp",
        invoice_date="2023-01-01", total_amount=100.00, items=[]
    )
    risk_vendor = detector.detect(vendor_invoice)
    assert risk_vendor.is_suspicious is True
    assert "watchlist" in risk_vendor.reason

def test_fraud_explainer():
    explainer = FraudExplainer()
    detector = AnomalyDetector()

    # Suspicious invoice
    invoice = Invoice(
        id="4", filename="bad.pdf", vendor_name="Shadow Corp",
        invoice_date="2023-01-01", total_amount=20000.00, items=[]
    )
    assessment = detector.detect(invoice)
    explanation = explainer.explain(invoice, assessment)

    assert "Gemini Analysis" in explanation
    assert "Potential Fraud Risk Detected" in explanation

    # Normal invoice
    normal_invoice = Invoice(
        id="5", filename="good.pdf", vendor_name="Good Co",
        invoice_date="2023-01-01", total_amount=100.00, items=[]
    )
    normal_assessment = detector.detect(normal_invoice)
    explanation = explainer.explain(normal_invoice, normal_assessment)
    assert "standard business expenditure" in explanation
