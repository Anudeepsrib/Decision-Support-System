"""Configuration checks for reusable organization profiles."""

import os
import unittest
from unittest.mock import patch

from backend.config import _build_settings


class ConfigurationTests(unittest.TestCase):
    def test_profile_can_be_rebranded_without_code_changes(self):
        profile = {
            "APP_NAME": "Example Regulatory DSS",
            "REGULATOR_NAME": "Example Energy Commission",
            "REGULATOR_SHORT_NAME": "EEC",
            "UTILITY_NAME": "Example Utility",
            "UTILITY_ADDRESS": "One Main Street|Example City",
            "COMMISSION_MEMBERS": "A. Chair, Chair|B. Member, Member",
            "CASE_ID_PREFIX": "Example Cases",
            "REPORT_FILENAME_PREFIX": "Example Orders",
        }
        with patch.dict(os.environ, profile, clear=False):
            settings = _build_settings()

        self.assertEqual(settings.app_name, "Example Regulatory DSS")
        self.assertEqual(settings.utility_address, ["One Main Street", "Example City"])
        self.assertEqual(settings.commission_members[1], "B. Member, Member")
        self.assertEqual(settings.case_id_prefix, "Example-Cases")
        self.assertEqual(settings.report_filename_prefix, "Example-Orders")


if __name__ == "__main__":
    unittest.main()
