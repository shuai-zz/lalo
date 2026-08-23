from __future__ import annotations

import unittest

from lalo import check_configuration, provider_statuses


class ConfigurationTests(unittest.TestCase):
    def test_provider_status_never_contains_the_secret(self) -> None:
        statuses = provider_statuses({"OPENAI_API_KEY": "top-secret"})

        self.assertEqual(len(statuses), 1)
        self.assertEqual(statuses[0].name, "openai")
        self.assertTrue(statuses[0].configured)
        self.assertNotIn("top-secret", repr(statuses))

    def test_default_configuration_only_requires_an_api_key(self) -> None:
        result = check_configuration({"OPENAI_API_KEY": "top-secret"})

        self.assertTrue(result.valid, result.errors)

    def test_reports_stable_errors_for_invalid_values(self) -> None:
        result = check_configuration(
            {
                "OPENAI_API_KEY": " ",
                "OPENAI_BASE_URL": "ftp://user:password@example.com",
                "LALO_OPENAI_VISION_MODEL": "",
                "LALO_OPENAI_IMAGE_MODEL": " ",
                "LALO_OPENAI_ZERO_RETENTION": "yes",
            }
        )

        self.assertEqual(
            result.errors,
            (
                "missing:OPENAI_API_KEY",
                "invalid:OPENAI_BASE_URL",
                "invalid:LALO_OPENAI_VISION_MODEL",
                "invalid:LALO_OPENAI_IMAGE_MODEL",
                "invalid:LALO_OPENAI_ZERO_RETENTION",
            ),
        )


if __name__ == "__main__":
    unittest.main()
