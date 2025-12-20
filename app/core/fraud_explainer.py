from app.models.invoice import Invoice, RiskAssessment
import os

try:
    import google.generativeai as genai
    HAS_GEMINI = True
except ImportError:
    HAS_GEMINI = False

class FraudExplainer:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if HAS_GEMINI and self.api_key:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel('gemini-pro')

    def explain(self, invoice: Invoice, assessment: RiskAssessment) -> str:
        # Check if we have credentials and libraries to use real Gemini
        if HAS_GEMINI and self.api_key:
            try:
                return self._explain_with_gemini(invoice, assessment)
            except Exception as e:
                print(f"Gemini API failed: {e}. Falling back to mock.")
                # Fallback to mock

        return self._explain_mock(invoice, assessment)

    def _explain_with_gemini(self, invoice: Invoice, assessment: RiskAssessment) -> str:
        prompt = f"""
        Analyze the following invoice for fraud risk.
        Vendor: {invoice.vendor_name}
        Amount: {invoice.total_amount}
        Items: {invoice.items}
        Risk Flags: {assessment.reason}
        Risk Score: {assessment.risk_score}

        Provide a concise explanation of the risk factors and a recommendation.
        """
        response = self.model.generate_content(prompt)
        return response.text

    def _explain_mock(self, invoice: Invoice, assessment: RiskAssessment) -> str:
        # Mocking Google Gemini explanation
        if not assessment.is_suspicious:
            return "This invoice appears to be standard business expenditure. No significant risk factors were identified based on the vendor history and transaction amount."

        explanation = "Gemini Analysis: Potential Fraud Risk Detected.\n"
        explanation += f"1. The transaction amount of ${invoice.total_amount} is significantly higher than the average for this category.\n"
        if "watchlist" in assessment.reason:
            explanation += f"2. The vendor '{invoice.vendor_name}' has previously been flagged for irregular billing practices.\n"
        explanation += "Recommendation: Flag for manual review by the audit team."

        return explanation
