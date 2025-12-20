from app.models.invoice import Invoice, RiskAssessment
import os

try:
    import vertexai
    from vertexai.generative_models import GenerativeModel
    HAS_VERTEX = True
except ImportError:
    HAS_VERTEX = False

class FraudExplainer:
    def __init__(self):
        self.project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
        self.location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")

        if HAS_VERTEX and self.project_id:
            vertexai.init(project=self.project_id, location=self.location)
            self.model = GenerativeModel("gemini-1.5-flash-001")

    def explain(self, invoice: Invoice, assessment: RiskAssessment) -> str:
        # Check if we have credentials and libraries to use real Gemini
        if HAS_VERTEX and self.project_id:
            try:
                return self._explain_with_vertex(invoice, assessment)
            except Exception as e:
                print(f"Vertex AI failed: {e}. Falling back to mock.")
                # Fallback to mock

        return self._explain_mock(invoice, assessment)

    def _explain_with_vertex(self, invoice: Invoice, assessment: RiskAssessment) -> str:
        prompt = f"""
You are an expert fraud auditor. Analyze the following invoice details and anomaly score to provide a plain English explanation for the risk.

Invoice Details:
Vendor: {invoice.vendor_name}
Total Amount: {invoice.total_amount}
Items: {invoice.items}
Date: {invoice.invoice_date}

Anomaly Score: {assessment.risk_score} (0-1 scale, higher is riskier)
Risk Flags: {assessment.reason}

Instructions:
1. Explain why this invoice is considered suspicious based on the score and details.
2. Mention possible fraud patterns such as "invoice splitting", "repeated vendors", or "high-value amounts" if applicable.
3. Keep the explanation professional, concise, and suitable for an auditor.
"""
        response = self.model.generate_content(prompt)
        return response.text

    def _explain_mock(self, invoice: Invoice, assessment: RiskAssessment) -> str:
        # Mocking Google Gemini explanation
        if not assessment.is_suspicious:
            return "This invoice appears to be standard business expenditure. No significant risk factors were identified based on the vendor history and transaction amount."

        explanation = "Gemini Analysis: Potential Fraud Risk Detected.\n"
        explanation += f"1. The transaction amount of ${invoice.total_amount} is significantly higher than the average for this category.\n"
        if assessment.reason and "watchlist" in assessment.reason:
            explanation += f"2. The vendor '{invoice.vendor_name}' has previously been flagged for irregular billing practices.\n"
        explanation += "Recommendation: Flag for manual review by the audit team."

        return explanation
