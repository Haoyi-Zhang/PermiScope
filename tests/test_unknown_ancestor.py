"""Unknown ancestors are rejected independently of declaration order."""
import itertools
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from pcpe.source_model import parse_source
from pcpe.source_checker import validate_source_evidence

ROOT = Path(__file__).resolve().parents[1]


def source_document():
    return {
        "language": "bfil-1", "permissions": ["P"],
        "classes": [
            {"name": "A", "super": "B", "fields": [], "methods": [
                {"name": "run", "params": [], "returns": None,
                 "locals": [], "body": []}]},
            {"name": "B", "super": "C", "fields": [], "methods": []},
            {"name": "C", "super": "Missing", "fields": [], "methods": []}],
        "services": [{"name": "S", "declared_class": "A",
                      "implementation_class": "A"}],
        "entries": [{"name": "API", "service": "S", "selector": "run",
                     "arg_classes": []}],
    }


def evidence_document():
    # The outer schema is sufficient to reach source admission; a rejected
    # source must not inspect the evidence bodies.
    return {"language": "bfil-evidence-1", "lower": {}, "upper": {},
            "classification": []}


class UnknownAncestorTests(unittest.TestCase):
    def test_parser_rejects_every_class_order(self):
        source = source_document()
        for order in itertools.permutations(source["classes"]):
            source["classes"] = list(order)
            with self.subTest(order=[row["name"] for row in order]):
                with self.assertRaisesRegex(ValueError, "unknown super class"):
                    parse_source(source)

    def test_checker_rejects_without_lookup_exception(self):
        verdict = validate_source_evidence(source_document(), evidence_document())
        self.assertFalse(verdict.accepted)
        self.assertEqual(verdict.reason, "source-unknown super class")

    def test_cli_returns_rejection_without_traceback(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.json"
            evidence = Path(directory) / "evidence.json"
            source.write_text(json.dumps(source_document()), encoding="utf-8")
            evidence.write_text(json.dumps(evidence_document()), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, "-B", str(ROOT / "check_framework.py"),
                 str(source), str(evidence)], cwd=ROOT, capture_output=True,
                text=True, check=False)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(result.stderr, "")
        self.assertEqual(json.loads(result.stdout)["reason"],
                         "source-unknown super class")

    def test_valid_ancestor_chain_remains_accepted(self):
        source = source_document()
        source["classes"][-1]["super"] = None
        self.assertEqual(parse_source(source).class_map["A"].super, "B")


if __name__ == "__main__":
    unittest.main()
