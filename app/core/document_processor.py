from app.models.invoice import Invoice, InvoiceItem
import uuid
from typing import BinaryIO
import os
import random

try:
    from google.cloud import documentai
    from google.api_core.client_options import ClientOptions
    HAS_GOOGLE_CLOUD = True
except ImportError:
    HAS_GOOGLE_CLOUD = False

class DocumentProcessor:
    def __init__(self):
        self.project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
        self.location = "us" # Format is 'us' or 'eu'
        self.processor_id = os.getenv("DOCUMENT_AI_PROCESSOR_ID")

    def process(self, file_content: BinaryIO, filename: str) -> Invoice:
        # Check if we have credentials and libraries to use real Document AI
        if HAS_GOOGLE_CLOUD and self.project_id and self.processor_id:
            try:
                return self._process_with_google(file_content, filename)
            except Exception as e:
                print(f"Google Document AI failed: {e}. Falling back to mock.")
                # Fallback to mock if real processing fails

        return self._process_mock(filename)

    def _process_with_google(self, file_content: BinaryIO, filename: str) -> Invoice:
        # Instantiates a client
        opts = ClientOptions(api_endpoint=f"{self.location}-documentai.googleapis.com")
        client = documentai.DocumentProcessorServiceClient(client_options=opts)

        # The full resource name of the processor
        name = client.processor_path(self.project_id, self.location, self.processor_id)

        # Read the file into memory
        file_content.seek(0)
        content = file_content.read()

        # Load Binary Data into Document AI RawDocument Object
        raw_document = documentai.RawDocument(content=content, mime_type="application/pdf")

        # Configure the process request
        request = documentai.ProcessRequest(name=name, raw_document=raw_document)

        # Use the client to process the document
        result = client.process_document(request=request)
        document = result.document

        # Extract data from entities (simplified for hackathon)
        vendor_name = "Unknown Vendor"
        total_amount = 0.0
        date = "2023-01-01"

        for entity in document.entities:
            if entity.type_ == "supplier_name":
                vendor_name = entity.mention_text
            elif entity.type_ == "total_amount":
                try:
                    total_amount = float(entity.normalized_value.text)
                except:
                    pass
            elif entity.type_ == "invoice_date":
                try:
                    date = entity.normalized_value.text
                except:
                    date = entity.mention_text

        # Create invoice object
        return Invoice(
            id=str(uuid.uuid4()),
            filename=filename,
            vendor_name=vendor_name,
            invoice_date=date,
            total_amount=total_amount,
            items=[] # Detailed item extraction omitted for brevity
        )

    def _process_mock(self, filename: str) -> Invoice:
        # Determine if we should generate a suspicious invoice for demo purposes
        # If filename contains "suspicious", we make it suspicious
        is_suspicious_demo = "suspicious" in filename.lower()

        invoice_id = str(uuid.uuid4())

        if is_suspicious_demo:
            vendor_name = "Shadow Corp"
            total_amount = 15000.00
            items = [
                InvoiceItem(description="Consulting Services", amount=15000.00, quantity=1)
            ]
        else:
            vendor_name = "Office Supplies Co"
            total_amount = 450.50
            items = [
                InvoiceItem(description="Paper Reams", amount=50.00, quantity=5),
                InvoiceItem(description="Printer Ink", amount=200.50, quantity=1)
            ]

        return Invoice(
            id=invoice_id,
            filename=filename,
            vendor_name=vendor_name,
            invoice_date="2023-10-27",
            total_amount=total_amount,
            items=items
        )
