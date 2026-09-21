from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from sodminer.strings import (
    extract_strings,
    extract_strings_from_path,
    write_string_records,
)


class StringExtractorTests(unittest.TestCase):
    def test_extracts_ascii_utf8_and_utf16le_with_offsets(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.bin"
            ascii_text = b"Big Chomp"
            utf8_text = "Café Dream".encode("utf-8")
            utf16_text = "Starless Path".encode("utf-16le")
            payload = (
                b"\x00\x01"
                + ascii_text
                + b"\x00\xff"
                + utf8_text
                + b"\x00\x00"
                + utf16_text
                + b"\x00"
            )
            path.write_bytes(payload)

            records = extract_strings(path, "v1.4.0", min_length=4)

            by_key = {(item["encoding"], item["text"]): item for item in records}
            self.assertEqual(by_key[("ascii", "Big Chomp")]["offset"], 2)
            self.assertEqual(
                by_key[("utf-8", "Café Dream")]["offset"],
                payload.index(utf8_text),
            )
            self.assertEqual(
                by_key[("utf-16le", "Starless Path")]["offset"],
                payload.index(utf16_text),
            )
            self.assertEqual(by_key[("ascii", "Big Chomp")]["release"], "v1.4.0")

    def test_contains_filter_is_case_insensitive(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.bin"
            path.write_bytes(b"ordinary chomp\x00BIG CHOMP\x00")

            records = extract_strings(path, "v1.4.0", contains="big chomp")

            texts = [item["text"] for item in records]
            self.assertEqual(texts, ["BIG CHOMP"])

    def test_directory_extraction_preserves_relative_source_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "game"
            target = root / "RawData" / "sample.bin"
            target.parent.mkdir(parents=True)
            target.write_bytes(b"Big Chomp")

            records = list(
                extract_strings_from_path(
                    root,
                    "v1.4.0",
                    contains="Big Chomp",
                )
            )

            self.assertEqual(len(records), 1)
            self.assertEqual(records[0]["source_file"], "RawData/sample.bin")

    def test_write_jsonl_returns_count(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "out" / "strings.jsonl"
            destination, count = write_string_records(
                [
                    {
                        "source_file": "x.bin",
                        "release": "v1.4.0",
                        "offset": 2,
                        "encoding": "ascii",
                        "text": "Big Chomp",
                    }
                ],
                output,
            )

            self.assertEqual(destination, output)
            self.assertEqual(count, 1)
            parsed = json.loads(output.read_text(encoding="utf-8").strip())
            self.assertEqual(parsed["text"], "Big Chomp")


if __name__ == "__main__":
    unittest.main()
