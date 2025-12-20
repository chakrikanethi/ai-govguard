from google.cloud import bigquery
from typing import List, Dict, Any
import datetime

SCHEMA = [
    bigquery.SchemaField("invoice_id", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("vendor_name", "STRING", mode="NULLABLE"),
    bigquery.SchemaField("invoice_date", "DATE", mode="NULLABLE"),
    bigquery.SchemaField("total_amount", "FLOAT", mode="NULLABLE"),
    bigquery.SchemaField("currency", "STRING", mode="NULLABLE"),
    bigquery.SchemaField("extracted_at", "TIMESTAMP", mode="NULLABLE"),
]

def setup_bigquery(client: bigquery.Client, dataset_id: str, table_id: str, location: str = "US"):
    """
    Creates the dataset and table if they do not exist.
    """
    dataset_ref = bigquery.DatasetReference(client.project, dataset_id)
    dataset = bigquery.Dataset(dataset_ref)
    dataset.location = location
    try:
        client.create_dataset(dataset, exists_ok=True)
        print(f"Dataset {dataset_id} created or already exists.")
    except Exception as e:
        print(f"Error creating dataset {dataset_id}: {e}")
        raise

    table_ref = dataset_ref.table(table_id)
    table = bigquery.Table(table_ref, schema=SCHEMA)
    try:
        client.create_table(table, exists_ok=True)
        print(f"Table {table_id} created or already exists.")
    except Exception as e:
        print(f"Error creating table {table_id}: {e}")
        raise

def store_invoices(client: bigquery.Client, dataset_id: str, table_id: str, invoices: List[Dict[str, Any]]):
    """
    Stores extracted invoice data into BigQuery.
    Handles duplicate invoice IDs by updating the existing record (Upsert).
    Also handles intra-batch duplicates by taking the last occurrence.
    """
    if not invoices:
        print("No invoices to store.")
        return

    full_table_id = f"{client.project}.{dataset_id}.{table_id}"

    # Deduplicate invoices based on invoice_id, keeping the last one
    unique_invoices_map = {}
    for inv in invoices:
        if "invoice_id" in inv and inv["invoice_id"]:
            unique_invoices_map[inv["invoice_id"]] = inv
        else:
            # Handle cases where invoice_id might be missing if necessary, but schema says REQUIRED
            # For now, we skip or log. Let's assume input validation has happened or we skip.
            # But since schema is REQUIRED, if we try to insert NULL, BQ will fail.
            # We'll just skip here for safety or proceed and let BQ fail?
            # Let's proceed, BQ will throw error if we pass NULL.
            pass

    # However, if invoice_id is missing, we can't key it.
    # We will filter out items without invoice_id to avoid key errors in the map logic if needed,
    # but the loop above already handles it (won't add to map if key is missing/empty).

    # Reconstruct list
    deduplicated_invoices = list(unique_invoices_map.values())

    if not deduplicated_invoices:
         print("No valid invoices to store after deduplication.")
         return

    # Let's ensure the input dicts match the expected structure.
    sanitized_invoices = []
    for inv in deduplicated_invoices:
        sanitized_invoices.append({
            "invoice_id": inv.get("invoice_id"),
            "vendor_name": inv.get("vendor_name"),
            "invoice_date": inv.get("invoice_date"),
            "total_amount": inv.get("total_amount"),
            "currency": inv.get("currency"),
            "extracted_at": inv.get("extracted_at")
        })

    # The query parameters require the values to be in the correct type.

    query = f"""
        MERGE `{full_table_id}` T
        USING UNNEST(@invoices) S
        ON T.invoice_id = S.invoice_id
        WHEN MATCHED THEN
          UPDATE SET
            vendor_name = S.vendor_name,
            invoice_date = S.invoice_date,
            total_amount = S.total_amount,
            currency = S.currency,
            extracted_at = S.extracted_at
        WHEN NOT MATCHED THEN
          INSERT (invoice_id, vendor_name, invoice_date, total_amount, currency, extracted_at)
          VALUES (invoice_id, vendor_name, invoice_date, total_amount, currency, extracted_at)
    """

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ArrayQueryParameter(
                "invoices",
                "STRUCT<invoice_id STRING, vendor_name STRING, invoice_date DATE, total_amount FLOAT64, currency STRING, extracted_at TIMESTAMP>",
                sanitized_invoices
            )
        ]
    )

    try:
        query_job = client.query(query, job_config=job_config)
        query_job.result()  # Wait for the job to complete
        print(f"Successfully processed {len(sanitized_invoices)} invoices.")
    except Exception as e:
        print(f"Error storing invoices: {e}")
        raise
