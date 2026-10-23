"""Reproduce only the supplied, reviewed Java permission-event fixtures.

No external source is executed. The complete Java frontend never executes its
input; native execution here is limited to the eight frozen owned units.
"""
from pathlib import Path
import argparse
import gzip
import json
import tempfile

from pcpe.java_frontend import (JAVA, checked, executable, compile_frontend,
                                translate_file, check_java_evidence)
from pcpe.evidence import build_evidence
from pcpe.checker import validate
from pcpe.source_oracle import permission_oracle

ROOT = Path(__file__).resolve().parent


def json_bytes(value):
    return (json.dumps(value, indent=2, sort_keys=True) + '\n').encode('utf-8')


def native_permissions(source, out):
    out.mkdir(parents=True, exist_ok=False)
    checked([executable('javac'), '-proc:none', '--release', '17', '-encoding',
             'UTF-8', '-d', str(out), str(source), str(JAVA / 'Permission.java'),
             str(JAVA / 'Probe.java')])
    text = checked([executable('java'), '-Xmx256m', '-cp', str(out), 'Probe'])
    return text.splitlines()


def run(out):
    out = Path(out)
    if out.exists():
        raise ValueError('Refusing an existing output directory')
    rows, records = [], []
    with tempfile.TemporaryDirectory(prefix='permission-java-') as temporary:
        temporary = Path(temporary)
        front = compile_frontend(temporary / 'frontend')
        for length in (1, 4, 16, 64):
            pair = {}
            for stage in ('before', 'after'):
                relative = Path('inputs/java-bridge') / ('chain-' + str(length)) / stage / 'Service.java'
                source = ROOT / relative
                projection = translate_file(source, front)
                evidence, stats = build_evidence(projection['document'])
                verdict = check_java_evidence(source, evidence, front)
                if not verdict.accepted:
                    raise AssertionError(verdict)
                native = native_permissions(source, temporary / ('native-' + str(length) + '-' + stage))
                direct = sorted(p for api, p in permission_oracle(projection['document'])[0]
                                if api == 'API')
                catalog = evidence['lower']['ir']['catalog']['permissions']
                horn = [catalog[int(row['query'].split(':')[-1][1:])]
                        for row in evidence['classification'] if row['status'] == 'must']
                if native != direct or direct != sorted(horn):
                    raise AssertionError((native, direct, horn))
                expected = ['P_A'] if stage == 'before' else ['P_A', 'P_B']
                if native != expected:
                    raise AssertionError('Unexpected owned fixture events')
                pair[stage] = (projection, evidence)
                records.append({'source': relative.as_posix(),
                                'source_text': source.read_text(encoding='utf-8'),
                                'projection': projection, 'evidence': evidence,
                                'native_permissions': native, 'direct_permissions': direct,
                                'horn_permissions': sorted(horn), 'stats': stats})
            old = pair['before'][1]
            proof_only = validate(old['lower']['program'], old['lower']['certificate'])
            changed_source = ROOT / 'inputs/java-bridge' / ('chain-' + str(length)) / 'after/Service.java'
            stale = check_java_evidence(changed_source, old, front)
            if not proof_only.accepted or stale.accepted:
                raise AssertionError('Source coverage separation did not hold')
            rows.append({'chain_methods': length, 'total_methods': length + 1,
                         'before_statements': pair['before'][0]['inventory']['statements'],
                         'after_statements': pair['after'][0]['inventory']['statements'],
                         'before_native_permissions': ['P_A'],
                         'after_native_permissions': ['P_A', 'P_B'],
                         'same_literal_inventory': (
                             pair['before'][0]['document']['permissions'] ==
                             pair['after'][0]['document']['permissions']),
                         'proof_only_on_old_program': proof_only.accepted,
                         'stale_projection_on_new_java': stale.accepted,
                         'stale_reason': stale.reason})
    table = [r'\begin{tabular}{rrrrcc}', r'\toprule',
             r'Chain & Methods & Old stmt. & New stmt. & Old proof & Java check \\',
             r'\midrule']
    for row in rows:
        table.append(f"{row['chain_methods']} & {row['total_methods']} & "
                     f"{row['before_statements']} & {row['after_statements']} & "
                     r'accept & reject \\')
    table.extend([r'\bottomrule', r'\end{tabular}', ''])
    products = {
        'summary.json': json_bytes({'source_units': 8, 'native_runs': 8,
            'new_source_omissions_rejected': 4, 'rows': rows,
            'semantics': 'Permission-event sets on owned acyclic final classes; not Android enforcement',
            'trusted_boundary': 'Installed JDK parser/type checker, closed profile mapping, owned Permission event primitive'}),
        'records.json.gz': gzip.compress(json_bytes(records), mtime=0),
        'table.tex': '\n'.join(table).encode('utf-8')}
    out.mkdir(parents=True, exist_ok=False)
    for name, data in products.items():
        (out / name).write_bytes(data)
    return products


def compare(actual, expected):
    for name in ('summary.json', 'table.tex'):
        if (actual / name).read_bytes() != (expected / name).read_bytes():
            raise ValueError('Java study differs: ' + name)
    if gzip.decompress((actual / 'records.json.gz').read_bytes()) != gzip.decompress(
            (expected / 'records.json.gz').read_bytes()):
        raise ValueError('Java source/evidence records differ')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--compare', type=Path)
    args = parser.parse_args()
    run(args.out)
    if args.compare:
        compare(args.out, args.compare)
    print('Java source bridge: eight native runs agree; four stale projections rejected')
