import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from newsren.cache import load_cache, save_cache


class CacheTests(unittest.TestCase):
    def test_missing_file_is_empty(self):
        with TemporaryDirectory() as tmp:
            loaded = load_cache(Path(tmp) / "cache.json")
        self.assertEqual(loaded, {"stories": [], "sources": {}})

    def test_corrupt_file_is_ignored(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "cache.json"
            path.write_text("{", encoding="utf-8")
            self.assertEqual(load_cache(path), {"stories": [], "sources": {}})

    def test_incomplete_story_is_dropped(self):
        payload = {
            "stories": [
                {"title": "no id"},
                {
                    "id": "abc123abc123abcd",
                    "title": "Kept",
                    "url": "https://example.com/a",
                    "source_name": "The Verge",
                    "category": "technology",
                },
            ],
            "sources": {},
        }
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "cache.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            loaded = load_cache(path)
        self.assertEqual([story["id"] for story in loaded["stories"]], ["abc123abc123abcd"])

    def test_round_trip(self):
        payload = {
            "stories": [
                {
                    "id": "abc123abc123abcd",
                    "title": "Kept",
                    "url": "https://example.com/a",
                    "source_name": "The Verge",
                    "category": "technology",
                }
            ],
            "sources": {"https://example.com": {"last_error": ""}},
        }
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "nested" / "cache.json"
            save_cache(path, payload)
            self.assertEqual(load_cache(path), payload)
            self.assertIsInstance(json.loads(path.read_text(encoding="utf-8")), dict)


if __name__ == "__main__":
    unittest.main()
