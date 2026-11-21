"""Replay the five synthetic controls against the audited baseline and this tree."""

from pathlib import Path
import json
import subprocess
import sys
from tempfile import TemporaryDirectory
from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]
BASELINE = '69b93d53fa1715a613299204500eb024d170c1a2'
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts import compare_enhancement_results, scan_skill_security  # noqa: E402
from scripts.verify_phase_receipts import file_digest, plan_digest, verify  # noqa: E402


def baseline_module(name):
    path = f'scripts/{name}.py'
    source = subprocess.check_output(['git', 'show', f'{BASELINE}:{path}'], cwd=ROOT)
    module = ModuleType(name)
    module.__file__ = str(ROOT / path)
    exec(compile(source, path, 'exec'), module.__dict__)
    return module


def trial_report(variant, outcome):
    report = {key: 'locked' for key in compare_enhancement_results.LOCKED}
    report.update(trials=3, case_ids=['fixture'], complete=True, isolation_preflight='pass')
    report['results'] = [dict(case_id='fixture', trial=i, variant=variant, outcome=outcome)
                         for i in range(1, 4)]
    return report


def phase_controls(root, legacy_simulator):
    (root / 'impl.txt').write_text('implementation', encoding='utf-8')
    artifacts = root / 'artifacts'
    artifacts.mkdir()
    (artifacts / 'check.log').write_text('passed', encoding='utf-8')
    common = dict(entry='entry', exit='check', evidence='artifact',
                  inputs=['impl.txt'], required_checks=['check'])
    plan = {'phases': [dict(common, id='work', primary='lean-senior-engineering'),
                       dict(common, id='final', primary='verification-before-completion',
                            depends_on=['work'])]}
    if legacy_simulator is not None:
        trace = legacy_simulator.simulate(plan)['trace']
        return trace[1]['status'] != 'completed', trace[0]['status'] != 'completed'
    receipts = dict(version=1, plan_sha256=plan_digest(plan), phases=[])
    missing = verify(plan, receipts, root, artifacts)['phases'][1]['status'] == 'waiting'
    receipts['phases'].append({'id': 'work',
                               'input_sha256': {'impl.txt': file_digest(root, 'impl.txt')},
                               'checks': {'check': {'outcome': 'passed', 'path': 'check.log',
                                                    'sha256': file_digest(artifacts, 'check.log')}}})
    (root / 'impl.txt').write_text('changed implementation', encoding='utf-8')
    stale = verify(plan, receipts, root, artifacts)['phases'][0]['status'] == 'stale'
    return missing, stale


def controls(comparator, scanner, legacy_simulator):
    a, b = trial_report('baseline', 'blocked'), trial_report('candidate', 'pass')
    no_pairs = comparator.compare(a, b).get('coverage_status') == 'insufficient_evidence'
    findings = scanner.scan_text('sudo echo synthetic-private-note')
    redact = bool(findings) and 'synthetic-private-note' not in str(findings)
    with TemporaryDirectory() as temp:
        root = Path(temp)
        notes = root / 'large.md'
        notes.write_bytes(b'x' * (1024 * 1024 + 1))
        bound = any(row['rule'] == 'size-limit' for row in scanner.scan_path(notes))
        missing, stale = phase_controls(root, legacy_simulator)
    return {'no_pairs_reported': no_pairs, 'redacted': redact, 'bounded_scan': bound,
            'missing_receipt_blocks': missing, 'changed_input_blocks': stale}


def main():
    old_compare = baseline_module('compare_enhancement_results')
    old_scan = baseline_module('scan_skill_security')
    old_simulate = baseline_module('simulate_phase_orchestration')
    rows = [dict(variant=v, trial=i, checks=controls(comparator, scanner, legacy))
            for i in range(1, 4)
            for v, comparator, scanner, legacy in (
                ('baseline', old_compare, old_scan, old_simulate),
                ('candidate', compare_enhancement_results, scan_skill_security, None),
            )]
    totals = {v: sum(sum(row['checks'].values()) for row in rows if row['variant'] == v)
              for v in ('baseline', 'candidate')}
    print(json.dumps({'baseline': BASELINE, 'possible_per_variant': 15,
                      'passed': totals, 'results': rows}, indent=2))
    return 0 if totals['candidate'] == 15 else 1


if __name__ == '__main__':
    sys.exit(main())
