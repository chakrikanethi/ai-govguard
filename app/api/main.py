from fastapi import FastAPI, UploadFile, File, HTTPException
from typing import List, Dict
from app.core.document_processor import DocumentProcessor
from app.core.anomaly_detector import AnomalyDetector
from app.core.fraud_explainer import FraudExplainer
from app.core.graph_analysis import GraphAnalyzer
from app.models.invoice import Invoice

app = FastAPI(title="AI-GovGuard API", description="AI-powered government expenditure monitoring")

# In-memory storage for demonstration
invoices_db: Dict[str, Invoice] = {}

processor = DocumentProcessor()
detector = AnomalyDetector()
explainer = FraudExplainer()
graph_analyzer = GraphAnalyzer()

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

    # Graph Analysis
    try:
        graph_analyzer.add_invoice(invoice)
        graph_risk_signals = graph_analyzer.analyze_risk(invoice.vendor_name, invoice)
        if invoice.risk_assessment:
            invoice.risk_assessment.graph_risk_signals = graph_risk_signals
    except Exception as e:
        print(f"Graph analysis failed: {e}")

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
