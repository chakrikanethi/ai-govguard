import unittest
from unittest.mock import MagicMock, call
import datetime
from google.cloud import bigquery
from src.invoice_storage import setup_bigquery, store_invoices, SCHEMA

class TestInvoiceStorage(unittest.TestCase):
    def setUp(self):
        self.mock_client = MagicMock(spec=bigquery.Client)
        self.mock_client.project = "test-project"
        self.dataset_id = "test_dataset"
        self.table_id = "test_table"

    def test_setup_bigquery(self):
        # Mock create_dataset and create_table
        self.mock_client.create_dataset = MagicMock()
        self.mock_client.create_table = MagicMock()

        setup_bigquery(self.mock_client, self.dataset_id, self.table_id)

        # Verify create_dataset was called
        self.mock_client.create_dataset.assert_called_once()
        args, kwargs = self.mock_client.create_dataset.call_args
        self.assertEqual(args[0].dataset_id, self.dataset_id)
        self.assertEqual(kwargs['exists_ok'], True)

        # Verify create_table was called
        self.mock_client.create_table.assert_called_once()
        args, kwargs = self.mock_client.create_table.call_args
        self.assertEqual(args[0].table_id, self.table_id)
        self.assertEqual(args[0].schema, SCHEMA)
        self.assertEqual(kwargs['exists_ok'], True)

    def test_store_invoices_empty(self):
        store_invoices(self.mock_client, self.dataset_id, self.table_id, [])
        self.mock_client.query.assert_not_called()

    def test_store_invoices_success(self):
        invoices = [
            {
                "invoice_id": "INV-001",
                "vendor_name": "Acme Corp",
                "invoice_date": datetime.date(2023, 10, 26),
                "total_amount": 100.50,
                "currency": "USD",
                "extracted_at": datetime.datetime(2023, 10, 27, 10, 0, 0)
            }
        ]

        mock_query_job = MagicMock()
        self.mock_client.query.return_value = mock_query_job

        store_invoices(self.mock_client, self.dataset_id, self.table_id, invoices)

        self.mock_client.query.assert_called_once()
        args, kwargs = self.mock_client.query.call_args
        query_str = args[0]
        job_config = kwargs['job_config']

        # Verify query structure
        self.assertIn("MERGE `test-project.test_dataset.test_table` T", query_str)
        self.assertIn("USING UNNEST(@invoices) S", query_str)
        self.assertIn("ON T.invoice_id = S.invoice_id", query_str)
        self.assertIn("WHEN MATCHED THEN", query_str)
        self.assertIn("UPDATE SET", query_str)
        self.assertIn("WHEN NOT MATCHED THEN", query_str)
        self.assertIn("INSERT", query_str)

        # Verify query parameters
        self.assertEqual(len(job_config.query_parameters), 1)
        param = job_config.query_parameters[0]
        self.assertEqual(param.name, "invoices")
        self.assertEqual(param.array_type, "STRUCT<invoice_id STRING, vendor_name STRING, invoice_date DATE, total_amount FLOAT64, currency STRING, extracted_at TIMESTAMP>")
        self.assertEqual(param.values, invoices)

        mock_query_job.result.assert_called_once()

    def test_store_invoices_deduplication(self):
        invoices = [
            {
                "invoice_id": "INV-001",
                "vendor_name": "Acme Corp",
                "total_amount": 100.0
            },
            {
                "invoice_id": "INV-001",
                "vendor_name": "Acme Corp Updated",
                "total_amount": 150.0
            }
        ]

        mock_query_job = MagicMock()
        self.mock_client.query.return_value = mock_query_job

        store_invoices(self.mock_client, self.dataset_id, self.table_id, invoices)

        args, kwargs = self.mock_client.query.call_args
        job_config = kwargs['job_config']
        param_values = job_config.query_parameters[0].values

        self.assertEqual(len(param_values), 1)
        self.assertEqual(param_values[0]["invoice_id"], "INV-001")
        self.assertEqual(param_values[0]["vendor_name"], "Acme Corp Updated")
        self.assertEqual(param_values[0]["total_amount"], 150.0)

if __name__ == '__main__':
    unittest.main()
