from fastapi.testclient import TestClient
from app.api.main import app
import pytest

client = TestClient(app)

def test_upload_invoice():
    # Mock file upload
    files = {'file': ('test.pdf', b'dummy content', 'application/pdf')}
    response = client.post("/invoices/upload", files=files)

    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "test.pdf"
    assert "id" in data
    assert "risk_assessment" in data

def test_upload_suspicious_invoice():
    # Mock suspicious file upload
    files = {'file': ('suspicious_invoice.pdf', b'dummy content', 'application/pdf')}
    response = client.post("/invoices/upload", files=files)

    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "suspicious_invoice.pdf"
    assert data["risk_assessment"]["is_suspicious"] is True
    assert "Gemini Analysis" in data["risk_assessment"]["gemini_explanation"]

def test_upload_invalid_file_type():
    files = {'file': ('test.txt', b'dummy content', 'text/plain')}
    response = client.post("/invoices/upload", files=files)

    assert response.status_code == 400
    assert response.json()["detail"] == "Only PDF files are supported"

def test_get_invoices():
    # First upload an invoice
    files = {'file': ('list_test.pdf', b'dummy content', 'application/pdf')}
    client.post("/invoices/upload", files=files)

    response = client.get("/invoices")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1

def test_get_invoice_detail():
    # First upload an invoice
    files = {'file': ('detail_test.pdf', b'dummy content', 'application/pdf')}
    upload_response = client.post("/invoices/upload", files=files)
    invoice_id = upload_response.json()["id"]

    response = client.get(f"/invoices/{invoice_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == invoice_id
    assert data["filename"] == "detail_test.pdf"

def test_get_invoice_not_found():
    response = client.get("/invoices/non_existent_id")
    assert response.status_code == 404

def test_explain_invoice():
    # First upload an invoice
    files = {'file': ('explain_test.pdf', b'dummy content', 'application/pdf')}
    upload_response = client.post("/invoices/upload", files=files)
    invoice_id = upload_response.json()["id"]

    # Call explain endpoint
    response = client.get(f"/explain/{invoice_id}")
    assert response.status_code == 200
    data = response.json()
    assert "explanation" in data
    assert isinstance(data["explanation"], str)

def test_explain_invoice_not_found():
    response = client.get("/explain/non_existent_id")
    assert response.status_code == 404
