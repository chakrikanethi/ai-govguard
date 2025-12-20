from app.models.invoice import Invoice, RiskAssessment

class AnomalyDetector:
    def detect(self, invoice: Invoice) -> RiskAssessment:
        # Simple rule-based anomaly detection

        # Rule 1: High amount threshold
        HIGH_AMOUNT_THRESHOLD = 10000.00

        # Rule 2: Suspicious vendors
        SUSPICIOUS_VENDORS = ["Shadow Corp", "Null Enterprises"]

        risk_score = 0.0
        reasons = []
        is_suspicious = False

        if invoice.total_amount > HIGH_AMOUNT_THRESHOLD:
            risk_score += 0.7
            reasons.append(f"Total amount ${invoice.total_amount} exceeds threshold of ${HIGH_AMOUNT_THRESHOLD}")

        if invoice.vendor_name in SUSPICIOUS_VENDORS:
            risk_score += 0.8
            reasons.append(f"Vendor '{invoice.vendor_name}' is on the watchlist")

        if risk_score > 0.5:
            is_suspicious = True

        return RiskAssessment(
            is_suspicious=is_suspicious,
            risk_score=min(risk_score, 1.0),
            reason="; ".join(reasons) if reasons else "No anomalies detected"
        )
