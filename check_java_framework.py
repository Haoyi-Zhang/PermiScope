"""Check evidence against complete Java input without executing that input."""
import argparse
from dataclasses import asdict
import json
from pathlib import Path
import tempfile
from pcpe.java_frontend import compile_frontend, check_java_evidence


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--evidence', type=Path, required=True)
    args = parser.parse_args()
    try:
        evidence = json.loads(args.evidence.read_text(encoding='utf-8'))
        with tempfile.TemporaryDirectory(prefix='java-evidence-check-') as folder:
            classes = compile_frontend(Path(folder) / 'classes')
            verdict = check_java_evidence(args.source, evidence, classes)
        print(json.dumps(asdict(verdict), sort_keys=True))
        return 0 if verdict.accepted else 1
    except (ValueError, RuntimeError, OSError) as error:
        print(json.dumps({'accepted': False, 'reason': str(error)}, sort_keys=True))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
