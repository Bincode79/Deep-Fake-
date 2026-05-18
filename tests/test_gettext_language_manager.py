import unittest
import importlib.util
from pathlib import Path


def _load_language_manager():
    module_path = Path(__file__).resolve().parents[1] / "modules" / "gettext.py"
    spec = importlib.util.spec_from_file_location("gettext_under_test", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.LanguageManager


class LanguageManagerTests(unittest.TestCase):
    def test_get_alias_matches_translate_method(self):
        LanguageManager = _load_language_manager()
        manager = LanguageManager("en")
        manager.translations = {"Hello": "Xin chao"}

        self.assertEqual(manager._("Hello"), "Xin chao")
        self.assertEqual(manager.get("Hello"), "Xin chao")

    def test_missing_key_falls_back_to_key_or_default(self):
        LanguageManager = _load_language_manager()
        manager = LanguageManager("en")

        self.assertEqual(manager._("Missing"), "Missing")
        self.assertEqual(manager.get("Missing", "Fallback"), "Fallback")


if __name__ == "__main__":
    unittest.main()
