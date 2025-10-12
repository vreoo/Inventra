import shutil
import unittest
from pathlib import Path

from models.forecast import ConfigScope, ConfigUpdate
from services.config_service import ConfigService


class ConfigServiceTestCase(unittest.TestCase):
    def setUp(self):
        self.config_dir = Path("storage/test_configs")
        if self.config_dir.exists():
            shutil.rmtree(self.config_dir)
        self.service = ConfigService(config_dir=str(self.config_dir))

    def tearDown(self):
        if self.config_dir.exists():
            shutil.rmtree(self.config_dir)

    def test_append_and_read_config(self):
        update = ConfigUpdate(
            scope=ConfigScope.GLOBAL,
            settings={"service_level": 0.97},
            author="unit-test",
        )
        record = self.service.append_update(update)
        latest = self.service.get_latest_config()

        self.assertEqual(record.settings["service_level"], 0.97)
        self.assertIn("global", latest)
        self.assertEqual(latest["global"]["service_level"], 0.97)

        history = self.service.get_history()
        self.assertGreaterEqual(len(history), 1)


if __name__ == "__main__":
    unittest.main()
