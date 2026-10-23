"""Check the retained source/evidence study and render its paper table.

Native execution is reproduced separately by run_java_bridge.py. This consumer
checks frozen record consistency, current input text, BFIL replay and stale
source verdicts; it does not pretend to re-execute the Java logger.
"""
from pathlib import Path
import argparse
import gzip
import json
from pcpe.source_checker import validate_source_evidence
from pcpe.source_oracle import permission_oracle
from pcpe.checker import validate
from run_java_bridge import ROOT


def render():
    directory = ROOT / 'results/java-bridge'
    summary = json.loads((directory / 'summary.json').read_text(encoding='utf-8'))
    records = json.loads(gzip.decompress((directory / 'records.json.gz').read_bytes()))
    if len(records) != 8 or summary['source_units'] != 8 or summary['native_runs'] != 8:
        raise ValueError('Java study inventory')
    expected_sources = [f'inputs/java-bridge/chain-{n}/{stage}/Service.java'
                        for n in (1, 4, 16, 64) for stage in ('before', 'after')]
    if [record['source'] for record in records] != expected_sources:
        raise ValueError('Java source order/inventory')
    rows = []
    for index, n in enumerate((1, 4, 16, 64)):
        before, after = records[2*index:2*index+2]
        for record in (before, after):
            if (ROOT / record['source']).read_text(encoding='utf-8') != record['source_text']:
                raise ValueError('Retained source no longer current')
            document, evidence = record['projection']['document'], record['evidence']
            if not validate_source_evidence(document, evidence).accepted:
                raise ValueError('Invalid retained evidence')
            permissions = sorted(p for api, p in permission_oracle(document)[0] if api == 'API')
            catalog = evidence['lower']['ir']['catalog']['permissions']
            horn = sorted(catalog[int(row['query'].split(':')[-1][1:])]
                          for row in evidence['classification'] if row['status'] == 'must')
            if not permissions == horn == record['native_permissions'] == record['direct_permissions'] == record['horn_permissions']:
                raise ValueError('Retained permission mismatch')
        old = before['evidence']
        stale = validate_source_evidence(after['projection']['document'], old)
        row = {'chain_methods': n, 'total_methods': n+1,
               'before_statements': before['projection']['inventory']['statements'],
               'after_statements': after['projection']['inventory']['statements'],
               'before_native_permissions': before['native_permissions'],
               'after_native_permissions': after['native_permissions'],
               'same_literal_inventory': before['projection']['document']['permissions'] == after['projection']['document']['permissions'],
               'proof_only_on_old_program': validate(old['lower']['program'], old['lower']['certificate']).accepted,
               'stale_projection_on_new_java': stale.accepted, 'stale_reason': stale.reason}
        if not row['same_literal_inventory'] or stale.accepted or not row['proof_only_on_old_program']:
            raise ValueError('Source omission control')
        rows.append(row)
    if rows != summary['rows'] or summary['new_source_omissions_rejected'] != 4:
        raise ValueError('Java summary mismatch')
    lines = [r'\begin{tabular}{rrrrcc}', r'\toprule',
             r'Chain & Methods & Old stmt. & New stmt. & Old proof & Java check \\',
             r'\midrule']
    for row in rows:
        lines.append(f"{row['chain_methods']} & {row['total_methods']} & "
                     f"{row['before_statements']} & {row['after_statements']} & "
                     r'accept & reject \\')
    lines.extend([r'\bottomrule', r'\end{tabular}', ''])
    data = '\n'.join(lines).encode('utf-8')
    if data != (directory / 'table.tex').read_bytes():
        raise ValueError('Retained Java table mismatch')
    return data


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    data = render()
    if args.out:
        args.out.write_bytes(data)
    print('Java table: eight current sources and evidence records consistent')
