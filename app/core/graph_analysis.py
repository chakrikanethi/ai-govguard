import os
import logging
from typing import List, Optional
from app.models.invoice import Invoice

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    from neo4j import GraphDatabase
    HAS_NEO4J = True
except ImportError:
    HAS_NEO4J = False

class GraphAnalyzer:
    def __init__(self):
        self.driver = None
        self.enabled = False

        if not HAS_NEO4J:
            logger.info("Neo4j driver not installed. Graph analysis disabled.")
            return

        self.uri = os.getenv("NEO4J_URI")
        self.user = os.getenv("NEO4J_USER")
        self.password = os.getenv("NEO4J_PASSWORD")

        if self.uri and self.user and self.password:
            try:
                self.driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
                # Verify connection
                self.driver.verify_connectivity()
                self.enabled = True
                logger.info("Connected to Neo4j successfully.")
            except Exception as e:
                logger.error(f"Failed to connect to Neo4j: {e}")
                self.enabled = False
        else:
            logger.info("Neo4j credentials not found. Graph analysis disabled.")

    def close(self):
        if self.driver:
            self.driver.close()

    def add_invoice(self, invoice: Invoice):
        if not self.enabled:
            return

        query = """
        MERGE (v:Vendor {name: $vendor_name})
        CREATE (i:Invoice {id: $invoice_id, amount: $amount, date: $date, filename: $filename})
        MERGE (i)-[:SUBMITTED_BY]->(v)
        """

        try:
            with self.driver.session() as session:
                session.run(query,
                            vendor_name=invoice.vendor_name,
                            invoice_id=invoice.id,
                            amount=invoice.total_amount,
                            date=invoice.invoice_date,
                            filename=invoice.filename)
            logger.info(f"Added invoice {invoice.id} to graph.")
        except Exception as e:
            logger.error(f"Error adding invoice to graph: {e}")

    def analyze_risk(self, vendor_name: str, invoice: Invoice) -> List[str]:
        if not self.enabled:
            return []

        signals = []

        try:
            with self.driver.session() as session:
                # Check 1: Repeated Vendors (High Frequency)
                # Count total invoices by this vendor
                query_freq = """
                MATCH (v:Vendor {name: $vendor_name})<-[:SUBMITTED_BY]-(i:Invoice)
                RETURN count(i) as count
                """
                result_freq = session.run(query_freq, vendor_name=vendor_name).single()
                if result_freq and result_freq["count"] > 5:
                    signals.append(f"High frequency vendor: {result_freq['count']} invoices found")

                # Check 2: Invoice Splitting (Same vendor, same day, multiple invoices)
                query_split = """
                MATCH (v:Vendor {name: $vendor_name})<-[:SUBMITTED_BY]-(i:Invoice)
                WHERE i.date = $date AND i.id <> $current_id
                RETURN count(i) as count, sum(i.amount) as total_amount
                """
                result_split = session.run(query_split,
                                           vendor_name=vendor_name,
                                           date=invoice.invoice_date,
                                           current_id=invoice.id).single()

                if result_split and result_split["count"] > 0:
                    signals.append(f"Potential invoice splitting: {result_split['count']} other invoice(s) found on {invoice.invoice_date}")

        except Exception as e:
            logger.error(f"Error analyzing graph risk: {e}")

        return signals
