from fastapi import FastAPI, UploadFile, File, HTTPException
from typing import List, Dict
from app.core.document_processor import DocumentProcessor
from app.core.anomaly_detector import AnomalyDetector
from app.core.fraud_explainer import FraudExplainer
from app.models.invoice import Invoice

app = FastAPI(title="AI-GovGuard API", description="AI-powered government expenditure monitoring")

# In-memory storage for demonstration
invoices_db: Dict[str, Invoice] = {}

processor = DocumentProcessor()
detector = AnomalyDetector()
explainer = FraudExplainer()

@app.post("/invoices/upload", response_model=Invoice)
def upload_invoice(file: UploadFile = File(...)):
    """
    Upload an invoice PDF, process it, detect anomalies, and get an explanation.
    """
    if not file.filename.endswith(('.pdf', '.PDF')):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    # Process the document
    try:
        # We're passing the file object directly, but in a real app we might read bytes
        invoice = processor.process(file.file, file.filename)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing document: {str(e)}")

    # Detect anomalies
    risk_assessment = detector.detect(invoice)
    invoice.risk_assessment = risk_assessment

    # Explain if suspicious or just to add context
    explanation = explainer.explain(invoice, risk_assessment)
    invoice.risk_assessment.gemini_explanation = explanation

    # Save to database
    invoices_db[invoice.id] = invoice

    return invoice

@app.get("/invoices", response_model=List[Invoice])
async def get_invoices():
    """
    Get a list of all processed invoices.
    """
    return list(invoices_db.values())

@app.get("/invoices/{invoice_id}", response_model=Invoice)
async def get_invoice(invoice_id: str):
    """
    Get details of a specific invoice.
    """
    if invoice_id not in invoices_db:
        raise HTTPException(status_code=404, detail="Invoice not found")

    return invoices_db[invoice_id]

@app.get("/explain/{invoice_id}")
async def explain_invoice(invoice_id: str):
    """
    Get an explanation for the invoice anomaly score.
    """
    if invoice_id not in invoices_db:
        raise HTTPException(status_code=404, detail="Invoice not found")

    invoice = invoices_db[invoice_id]

    # Ensure risk assessment exists
    if not invoice.risk_assessment:
        risk_assessment = detector.detect(invoice)
        invoice.risk_assessment = risk_assessment

    # Generate explanation
    explanation = explainer.explain(invoice, invoice.risk_assessment)
    invoice.risk_assessment.gemini_explanation = explanation

    return {"explanation": explanation}
