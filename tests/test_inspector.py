from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from sodminer.inspector import inspect_installation, write_inspection


class InspectorTests(unittest.TestCase):
    def test_detects_mono_shape_of_dreams_layout(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "Shape of Dreams"
            managed = root / "Shape of Dreams_Data" / "Managed"
            managed.mkdir(parents=True)
            (managed / "Assembly-CSharp.dll").write_bytes(b"managed")
            (managed / "Dew.Core.dll").write_bytes(b"dew")
            (root / "Shape of Dreams_Data" / "globalgamemanagers").write_bytes(
                b"\\x00Unity 6000.0.45f1\\x00"
            )

            overrides = root / "RawData" / "!ModResources" / "overrides"
            overrides.mkdir(parents=True)
            (overrides / "SkillTrigger.json").write_text("{}", encoding="utf-8")

            template = root / "Mods" / "ModTemplate"
            template.mkdir(parents=True)

            report = inspect_installation(root)

            self.assertEqual(report["engine"]["scripting_backend"], "mono")
            self.assertEqual(report["engine"]["unity_version"], "6000.0.45f1")
            self.assertIn("RawData", report["layout"]["raw_data_directories"])
            self.assertIn(
                "RawData/!ModResources/overrides",
                report["layout"]["override_directories"],
            )
            self.assertIn("Mods/ModTemplate", report["layout"]["mod_template_directories"])

            core_names = {
                Path(item["path"]).name
                for item in report["assemblies"]["core"]
            }
            self.assertIn("Assembly-CSharp.dll", core_names)
            self.assertIn("Dew.Core.dll", core_names)

    def test_detects_il2cpp_layout(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "Shape of Dreams"
            metadata = root / "Shape of Dreams_Data" / "il2cpp_data" / "Metadata"
            metadata.mkdir(parents=True)
            (metadata / "global-metadata.dat").write_bytes(b"metadata")
            (root / "GameAssembly.dll").write_bytes(b"gameassembly")

            report = inspect_installation(root)

            self.assertEqual(report["engine"]["scripting_backend"], "il2cpp")
            self.assertTrue(report["assemblies"]["game_assembly"])
            self.assertTrue(report["assemblies"]["il2cpp_metadata"])

    def test_write_inspection_creates_json_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "reports" / "inspection.json"
            path = write_inspection(
                {"schema_version": 1, "installation": "test"},
                output,
            )
            self.assertEqual(path, output)
            self.assertIn(
                '"schema_version": 1',
                output.read_text(encoding="utf-8"),
            )


if __name__ == "__main__":
    unittest.main()
