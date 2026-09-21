from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from sodminer.jsonsearch import (
    search_json_file,
    search_json_path,
    write_json_search_records,
)


class JsonSearchTests(unittest.TestCase):
    def test_finds_top_level_key_and_preserves_container(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "memories.json"
            path.write_text(
                json.dumps(
                    {
                        "St_R_Chomp": {"name": "Chomp"},
                        "St_U_BigChomp": {
                            "name": "Big Chomp",
                            "image": "St_U_BigChomp.png",
                        },
                    }
                ),
                encoding="utf-8",
            )

            records = search_json_file(path, "St_U_BigChomp", exact=True)

            key_hits = [item for item in records if item["match_kind"] == "key"]
            self.assertEqual(len(key_hits), 1)
            self.assertEqual(key_hits[0]["top_level_key"], "St_U_BigChomp")
            self.assertEqual(key_hits[0]["json_path"], '$["St_U_BigChomp"]')

    def test_finds_nested_reference_and_reports_top_level_object(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "stars.json"
            path.write_text(
                json.dumps(
                    {
                        "Star_Node_Example": {
                            "reward": "St_U_BigChomp",
                            "label": "Example",
                        }
                    }
                ),
                encoding="utf-8",
            )

            records = search_json_file(path, "St_U_BigChomp", exact=True)

            self.assertEqual(len(records), 1)
            self.assertEqual(records[0]["match_kind"], "value")
            self.assertEqual(records[0]["top_level_key"], "Star_Node_Example")
            self.assertEqual(
                records[0]["json_path"],
                '$["Star_Node_Example"]["reward"]',
            )

    def test_directory_search_uses_relative_source_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "RawData"
            target = root / "en-US" / "memories.json"
            target.parent.mkdir(parents=True)
            target.write_text(
                json.dumps({"St_U_BigChomp": {"name": "Big Chomp"}}),
                encoding="utf-8",
            )

            records = list(search_json_path(root, "big chomp"))

            self.assertEqual(len(records), 1)
            self.assertEqual(records[0]["source_file"], "en-US/memories.json")
            self.assertEqual(records[0]["top_level_key"], "St_U_BigChomp")

    def test_write_jsonl_returns_count(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "matches.jsonl"
            destination, count = write_json_search_records(
                [
                    {
                        "source_file": "en-US/memories.json",
                        "json_path": '$["St_U_BigChomp"]',
                        "match_kind": "key",
                        "matched_text": "St_U_BigChomp",
                        "top_level_key": "St_U_BigChomp",
                    }
                ],
                output,
            )

            self.assertEqual(destination, output)
            self.assertEqual(count, 1)
            parsed = json.loads(output.read_text(encoding="utf-8").strip())
            self.assertEqual(parsed["top_level_key"], "St_U_BigChomp")


if __name__ == "__main__":
    unittest.main()
