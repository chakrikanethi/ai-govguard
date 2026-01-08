import pytest
from unittest.mock import MagicMock, patch
from app.core.fraud_explainer import FraudExplainer
from app.models.invoice import Invoice, RiskAssessment, InvoiceItem
import os

@pytest.fixture
def mock_vertexai():
    with patch("app.core.fraud_explainer.vertexai") as mock_vertex:
        with patch("app.core.fraud_explainer.GenerativeModel") as mock_model_class:
            mock_model_instance = MagicMock()
            mock_model_class.return_value = mock_model_instance
            yield mock_vertex, mock_model_instance

def test_fraud_explainer_init(mock_vertexai):
    mock_vertex, mock_model = mock_vertexai
    with patch.dict(os.environ, {"GOOGLE_CLOUD_PROJECT": "test-project", "GOOGLE_CLOUD_LOCATION": "us-central1"}):
        explainer = FraudExplainer()
        mock_vertex.init.assert_called_with(project="test-project", location="us-central1")
        assert explainer.model == mock_model

def test_explain_with_vertex(mock_vertexai):
    mock_vertex, mock_model = mock_vertexai

    # Mock response
    mock_response = MagicMock()
    mock_response.text = "This is a suspicious invoice due to high amount."
    mock_model.generate_content.return_value = mock_response

    invoice = Invoice(
        id="123",
        filename="test.pdf",
        vendor_name="Test Vendor",
        invoice_date="2023-01-01",
        total_amount=1000.0,
        items=[InvoiceItem(description="Item 1", amount=1000.0, quantity=1)]
    )
    assessment = RiskAssessment(
        is_suspicious=True,
        risk_score=0.9,
        reason="High amount"
    )

    with patch.dict(os.environ, {"GOOGLE_CLOUD_PROJECT": "test-project"}):
        explainer = FraudExplainer()
        # Force HAS_VERTEX to True effectively via the mock import above,
        # but we also need to ensure the module sees HAS_VERTEX as True.
        # Since we patched the import before test execution, it might be tricky depending on when the module was loaded.
        # But we are mocking vertexai which is what the try/except block checks.
        # Actually, the try/except block runs at module level.
        # If we run pytest, the module is imported.
        # So we rely on the fact that if we can't import vertexai, HAS_VERTEX is False.
        # But here we want to test the Vertex path.

        # We need to simulate that `vertexai` is present.
        # In a test environment where `google-cloud-aiplatform` is NOT installed, HAS_VERTEX will be False.
        # We need to patch HAS_VERTEX in the module.

        with patch("app.core.fraud_explainer.HAS_VERTEX", True):
            explanation = explainer.explain(invoice, assessment)

            assert explanation == "This is a suspicious invoice due to high amount."
            mock_model.generate_content.assert_called_once()

            # Verify prompt content
            args, _ = mock_model.generate_content.call_args
            prompt = args[0]
            assert "Vendor: Test Vendor" in prompt
            assert "Anomaly Score: 0.9" in prompt
            assert "invoice splitting" in prompt # Check instructions

def test_explain_fallback_to_mock(mock_vertexai):
    # Test fallback when Vertex AI fails or is not configured
    invoice = Invoice(
        id="123",
        filename="test.pdf",
        vendor_name="Test Vendor",
        invoice_date="2023-01-01",
        total_amount=1000.0,
        items=[]
    )
    assessment = RiskAssessment(
        is_suspicious=True,
        risk_score=0.9,
        reason="High amount"
    )

    # Case 1: No Project ID
    with patch.dict(os.environ, {}, clear=True):
        explainer = FraudExplainer()
        explanation = explainer.explain(invoice, assessment)
        assert "Gemini Analysis" in explanation # Uses mock implementation

    # Case 2: Vertex AI Exception
    mock_vertex, mock_model = mock_vertexai
    mock_model.generate_content.side_effect = Exception("API Error")

    with patch.dict(os.environ, {"GOOGLE_CLOUD_PROJECT": "test-project"}):
        with patch("app.core.fraud_explainer.HAS_VERTEX", True):
            explainer = FraudExplainer()
            explanation = explainer.explain(invoice, assessment)
            assert "Gemini Analysis" in explanation # Falls back to mock
