import json
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from main import app


class ForecastExportEndpointTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)
        self.jobs_dir = Path("storage/jobs")
        self.jobs_dir.mkdir(parents=True, exist_ok=True)
        self.job_id = "export-test-job"
        self.job_file = self.jobs_dir / f"{self.job_id}.json"
        if self.job_file.exists():
            self.job_file.unlink()

        payload = {
            "jobId": self.job_id,
            "fileId": "file-1",
            "status": "COMPLETED",
            "mode": "demand",
            "schema_version": "1.0.0",
            "results": [
                {
                    "product_id": "SKU-TEST",
                    "product_name": "Sample SKU",
                    "mode": "demand",
                    "demand_frequency": "D",
                    "reorder_date": "2024-01-10",
                    "recommended_order_qty": 123.456,
                    "reorder_point": 50.5,
                    "safety_stock": 12.3,
                    "stockout_date": "2024-01-20",
                    "starting_inventory": 200.0,
                    "lead_time_days": 5,
                    "service_level": 0.95,
                    "model_used": "AutoARIMA",
                    "schema_version": "1.0.0",
                    "ai_summary": "Keep monitoring.",
                    "forecast_points": [
                        {
                            "date": "2024-01-01",
                            "forecast": 10.0,
                            "lower_bound": 8.0,
                            "upper_bound": 12.0,
                        },
                        {
                            "date": "2024-01-02",
                            "forecast": 11.0,
                            "lower_bound": 9.0,
                            "upper_bound": 13.0,
                        },
                    ],
                }
            ],
        }
        self.job_file.write_text(json.dumps(payload), encoding="utf-8")

    def tearDown(self) -> None:
        if self.job_file.exists():
            self.job_file.unlink()

    def test_exports_orders_csv(self) -> None:
        response = self.client.get(f"/api/forecast/{self.job_id}/export")
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/csv", response.headers.get("content-type", ""))
        csv_lines = response.text.splitlines()
        self.assertGreaterEqual(len(csv_lines), 2)
        header = csv_lines[0]
        self.assertIn("recommended_order_qty", header)
        self.assertIn("SKU-TEST", response.text)
        self.assertIn("123.46", response.text)

    def test_exports_forecast_csv(self) -> None:
        response = self.client.get(
            f"/api/forecast/{self.job_id}/export", params={"kind": "forecast"}
        )
        self.assertEqual(response.status_code, 200)
        csv_lines = response.text.splitlines()
        self.assertGreaterEqual(len(csv_lines), 3)
        header = csv_lines[0]
        self.assertIn("forecast", header)
        self.assertIn("2024-01-02", response.text)


if __name__ == "__main__":
    unittest.main()
