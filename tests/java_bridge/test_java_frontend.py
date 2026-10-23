"""Explicit JDK regression suite; CI runs this directory without skip logic."""
from pathlib import Path
import copy
import json
import subprocess
import sys
import tempfile
import unittest

from pcpe.java_frontend import compile_frontend, translate_file, check_java_evidence
from pcpe.evidence import build_evidence
from run_java_bridge import native_permissions, ROOT


class JavaFrontendTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='java-front-test-')
        cls.base = Path(cls.temp.name)
        cls.front = compile_frontend(cls.base / 'front')
        cls.before = ROOT / 'inputs/java-bridge/chain-1/before/Service.java'
        cls.after = ROOT / 'inputs/java-bridge/chain-1/after/Service.java'
        cls.old = build_evidence(translate_file(cls.before, cls.front)['document'])[0]
        cls.new = build_evidence(translate_file(cls.after, cls.front)['document'])[0]

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def translated(self, text):
        with tempfile.TemporaryDirectory(dir=self.base) as folder:
            source = Path(folder) / 'Service.java'
            source.write_text(text, encoding='utf-8')
            return translate_file(source, self.front)

    def test_complete_inventory(self):
        projected = translate_file(self.after, self.front)
        self.assertEqual(projected['inventory']['method_names'], ['run', 'dormant'])
        self.assertEqual(projected['inventory']['statements'], 3)
        self.assertEqual(projected['document']['permissions'], ['P_A', 'P_B'])

    def test_source_change_rejects_stale_projection(self):
        self.assertFalse(check_java_evidence(self.after, self.old, self.front).accepted)
        self.assertTrue(check_java_evidence(self.after, self.new, self.front).accepted)

    def test_native_events(self):
        with tempfile.TemporaryDirectory(dir=self.base) as folder:
            self.assertEqual(native_permissions(self.before, Path(folder) / 'before'), ['P_A'])
            self.assertEqual(native_permissions(self.after, Path(folder) / 'after'), ['P_A', 'P_B'])

    def test_unsupported_constructs_are_rejected(self):
        bodies = [
            'if (true) Permission.enforce("P_A");',
            'while (true) {}',
            'try { Permission.enforce("P_A"); } finally {}',
            'throw new RuntimeException();',
            'int x = 1;',
            'System.out.println("P_A");',
            'this.run();',
            'return; Permission.enforce("P_A");',
            'Permission.enforce("P_" + "A");',
        ]
        for body in bodies:
            with self.subTest(body=body), self.assertRaises(ValueError):
                self.translated('public final class Service { public void run(){' + body + '} }')

    def test_declarations_are_not_silently_dropped(self):
        units = [
            'public class Service { public void run(){Permission.enforce("P_A");} }',
            'final class Service { public void run(){Permission.enforce("P_A");} }',
            'public final class Service { int x; public void run(){Permission.enforce("P_A");} }',
            'public final class Service { class Nested{} public void run(){Permission.enforce("P_A");} }',
            'public final class Service extends Object { public void run(){Permission.enforce("P_A");} }',
            'public final class Service { Service(){} public void run(){Permission.enforce("P_A");} }',
            'public final class Service { public void run(int x){Permission.enforce("P_A");} }',
            'public final class Service { public static void run(){Permission.enforce("P_A");} }',
            'public final class Service { @Deprecated public void run(){Permission.enforce("P_A");} }',
            'package p; public final class Service { public void run(){Permission.enforce("P_A");} }',
        ]
        for text in units:
            with self.subTest(text=text), self.assertRaises(ValueError):
                self.translated(text)

    def test_terminal_return_and_implicit_receiver(self):
        result = self.translated('public final class Service { public void run(){helper();return;} '
                                 'private void helper(){Permission.enforce("P_A");} }')
        self.assertEqual(result['inventory']['statements'], 3)
        self.assertEqual(result['document']['classes'][0]['methods'][0]['body'][0]['recv'], 'this')

    def test_scalar_type_forgery_rejected(self):
        altered = copy.deepcopy(self.new)
        altered['lower']['coverage']['totals']['entries'] = True
        self.assertFalse(check_java_evidence(self.after, altered, self.front).accepted)

    def test_source_byte_bound(self):
        with self.assertRaises(ValueError):
            self.translated(' ' * 32769)
        excessive_methods = 'public final class Service { public void run(){Permission.enforce("P_A");}' + ''.join(
            'private void m' + str(n) + '(){}' for n in range(128)) + '}'
        excessive_statements = 'public final class Service {public void run(){' + 'Permission.enforce("P_A");' * 1025 + '}}'
        for text in (excessive_methods, excessive_statements):
            with self.subTest(bound=len(text)), self.assertRaises(ValueError):
                self.translated(text)

    def test_cli_rejects_stale_source(self):
        with tempfile.TemporaryDirectory(dir=self.base) as folder:
            evidence = Path(folder) / 'evidence.json'
            for item, expected_code in ((self.old, 1), (self.new, 0)):
                evidence.write_text(json.dumps(item), encoding='utf-8')
                completed = subprocess.run([sys.executable, '-B',
                    str(ROOT / 'check_java_framework.py'), '--source',
                    str(self.after), '--evidence', str(evidence)],
                    capture_output=True, text=True, timeout=30)
                self.assertEqual(completed.returncode, expected_code, completed.stdout + completed.stderr)
                self.assertEqual(json.loads(completed.stdout)['accepted'], expected_code == 0)


if __name__ == '__main__':
    unittest.main()
