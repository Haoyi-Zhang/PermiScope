"""Benign export regression using retained results, without running experiments."""
from __future__ import annotations

import json
from pathlib import Path
import re
import tempfile
import unittest

from export_paper_data import export


ROOT = Path(__file__).resolve().parents[1]
PAPER_DATA = ROOT.parent / "paper" / "data"
TABLES = (
    "baseline-table.tex", "campaign-table.tex", "diversity-table.tex",
    "family-table.tex", "framework-fault-table.tex", "framework-revision-table.tex",
    "kernel-table.tex", "public-table.tex", "resource-table.tex", "scale-table.tex",
    "unresolved-histogram-table.tex",
)


class PaperExportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="permiscope-paper-export-")
        cls.addClassCleanup(cls.temp.cleanup)
        cls.out = Path(cls.temp.name)
        export(ROOT / "results" / "observed", ROOT / "results" / "framework-replay", cls.out)

    def test_complete_output_inventory(self):
        self.assertEqual(
            {path.name for path in self.out.iterdir()},
            set(TABLES) | {"metrics.tex", "metrics.json"},
        )

    @unittest.skipUnless(PAPER_DATA.is_dir(), "sibling paper package not present")
    def test_all_table_labels_and_typesetting_match(self):
        for name in TABLES:
            with self.subTest(table=name):
                self.assertEqual(
                    (self.out / name).read_text(encoding="utf-8"),
                    (PAPER_DATA / name).read_text(encoding="utf-8"),
                )

    @unittest.skipUnless(PAPER_DATA.is_dir(), "sibling paper package not present")
    def test_all_numeric_tokens_and_metrics_match(self):
        for name in TABLES + ("metrics.tex",):
            with self.subTest(file=name):
                expected = (PAPER_DATA / name).read_text(encoding="utf-8")
                actual = (self.out / name).read_text(encoding="utf-8")
                # Ignore provenance comments, not any macro, table cell or dimension.
                expected = re.sub(r"(?m)^%.*$", "", expected)
                actual = re.sub(r"(?m)^%.*$", "", actual)
                self.assertEqual(re.findall(r"\d+(?:[.,]\d+)*", actual),
                                 re.findall(r"\d+(?:[.,]\d+)*", expected))
                self.assertEqual(actual.strip(), expected.strip())
        self.assertEqual(
            json.loads((self.out / "metrics.json").read_text(encoding="utf-8")),
            json.loads((PAPER_DATA / "metrics.json").read_text(encoding="utf-8")),
        )

    def test_public_and_fault_presentation(self):
        public = (self.out / "public-table.tex").read_text(encoding="utf-8")
        faults = (self.out / "framework-fault-table.tex").read_text(encoding="utf-8")
        self.assertIn("Operation & Retained lines & Primitive", public)
        self.assertIn("Vibrator: cancel & ", public)
        self.assertIn("Wallpaper: lock callback & ", public)
        self.assertEqual(public.count(r"\textnormal{"), 24)
        self.assertNotIn(r"\texttt", public + faults)
        self.assertIn(r"INTERNAL\_\allowbreak{}SYSTEM\_\allowbreak{}WINDOW", public)
        self.assertIn("fault-12 & Unsupported candidate & Unsupported operation at statement 3:0:6", faults)
        self.assertIn("fault-24 & Altered classification & classification mismatch", faults)

    def test_scale_rows_use_retained_summaries(self):
        chunks = json.loads((ROOT / "results" / "observed" / "run-all-summary.json")
                            .read_text(encoding="utf-8"))["chunks"]
        scale = sorted((item for item in chunks if item["chunk"].startswith("scale-")),
                       key=lambda item: (item["atoms"], item["initial_facts"]))
        rows = (self.out / "scale-table.tex").read_text(encoding="utf-8").splitlines()[4:-2]
        self.assertEqual(len(rows), 6)
        for row, item in zip(rows, scale):
            expected = [f"{item[key]:,}" for key in (
                "atoms", "initial_facts", "premise_incidences", "proof_nodes",
                "encoded_certificate_bytes")]
            expected.append(f"{1000 * item['wall_seconds']:.1f}")
            self.assertEqual(row, " & ".join(expected) + r" \\")


if __name__ == "__main__":
    unittest.main()
