"""Closed whole-unit Java bridge through the installed JDK compiler.

This parser never executes supplied Java. Native execution is confined to the
separate study driver's reviewed owned fixtures and trusted event primitive.
The JDK AST/type checker and this profile mapping join the trusted boundary.
"""
from pathlib import Path
import json
import os
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
JAVA = ROOT / 'java_bridge'


def executable(name):
    home = os.environ.get('JAVA_HOME')
    path = Path(home) / 'bin' / (name + ('.exe' if os.name == 'nt' else '')) if home else None
    if path is None or not path.is_file():
        found = shutil.which(name)
        if found is None:
            raise RuntimeError('An installed JDK 17+ with javac/java is required')
        path = Path(found)
    return str(path.resolve())


def checked(command, cwd=None, timeout=30):
    completed = subprocess.run(command, cwd=cwd, capture_output=True, text=True,
                               encoding='utf-8', timeout=timeout)
    if completed.returncode:
        raise ValueError('Java profile/compiler rejected input: ' +
                         (completed.stderr.strip() or 'nonzero exit'))
    return completed.stdout


def compile_frontend(classes):
    classes = Path(classes)
    classes.mkdir(parents=True, exist_ok=False)
    checked([executable('javac'), '-proc:none', '--release', '17', '-encoding', 'UTF-8',
             '-d', str(classes), str(JAVA / 'JavaSubsetFront.java')])
    return classes


def translate_file(source, classes):
    source = Path(source).resolve()
    before = source.read_bytes()
    if len(before) > 32768:
        raise ValueError('Java source byte bound')
    raw = checked([executable('java'), '-Xmx256m', '-cp', str(Path(classes).resolve()),
                   'JavaSubsetFront', str(source), str(JAVA / 'Permission.java')])
    if source.read_bytes() != before:
        raise ValueError('Source changed during checking')
    result = json.loads(raw)
    from .source_model import parse_source
    parse_source(result['document'])
    return result


def check_java_evidence(source, evidence, classes):
    """Reconstruct from a separate complete source; never trust submitted IR."""
    from .source_checker import validate_source_evidence
    actual = translate_file(source, classes)
    return validate_source_evidence(actual['document'], evidence)
