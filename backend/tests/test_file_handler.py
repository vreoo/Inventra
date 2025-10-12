import shutil
import unittest
from pathlib import Path

from models.forecast import ColumnMapping, ForecastConfig, ForecastMode
from services.file_handler import FileHandler


class FileHandlerTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sample_csv = Path("sample_data/demand_planning_example.csv")
        if not cls.sample_csv.exists():
            raise unittest.SkipTest("Sample demand planning CSV is missing.")

    def setUp(self):
        self.upload_dir = Path("storage/test_uploads")
        if self.upload_dir.exists():
            shutil.rmtree(self.upload_dir)
        self.handler = FileHandler(upload_dir=str(self.upload_dir))

    def tearDown(self):
        if self.upload_dir.exists():
            shutil.rmtree(self.upload_dir)
        processed_dir = Path("storage/processed/test_job")
        if processed_dir.exists():
            shutil.rmtree(processed_dir)
        raw_dir = Path("storage/raw/test_job")
        if raw_dir.exists():
            shutil.rmtree(raw_dir)
        metadata_dir = Path("storage/upload_metadata")
        manifest = metadata_dir / "test_job.json"
        if manifest.exists():
            manifest.unlink()

    def test_validate_csv_file_for_demand_mode(self):
        result = self.handler.validate_csv_file(self.sample_csv, ForecastMode.DEMAND)
        self.assertTrue(result["valid"])
        self.assertIn("summary", result)
        summary = result["summary"]
        self.assertIsInstance(summary.get("rows"), int)
        self.assertIn("mapping", result)
        mapping = result["mapping"]
        self.assertIn("date", mapping)
        self.assertIn("demand", mapping)

    def test_prepare_demand_artifacts(self):
        file_id = "test_job"
        destination = self.handler.get_file_path(file_id)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(self.sample_csv.read_bytes())

        mapping_dict = {
            "date": "date",
            "sku": "sku",
            "demand": "demand_units",
            "inventory": "on_hand",
            "lead_time": "lead_time_days",
            "name": "product_name",
        }
        mapping = ColumnMapping(**mapping_dict)
        config = ForecastConfig()

        artifacts = self.handler.prepare_demand_artifacts(file_id, mapping, config)

        self.assertGreater(len(artifacts.demand_df), 0)
        self.assertIn("SKU-100", artifacts.inventory_on_hand)
        self.assertIn("SKU-100", artifacts.lead_times)
        self.assertIsNotNone(artifacts.validation.detected_frequency)


if __name__ == "__main__":
    unittest.main()
