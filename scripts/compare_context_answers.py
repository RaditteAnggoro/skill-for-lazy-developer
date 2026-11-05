"""Compare model answers for full and blind-selected synthetic context."""
import argparse
import json
from pathlib import Path
import subprocess
import tempfile

import yaml

from scripts.context_optimizer import RawEvidenceStore, optimize_case


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', default='gpt-6.1-sol')
    parser.add_argument('--limit', type=int, default=2)
    args = parser.parse_args()
    cases = yaml.safe_load(Path('tests/token_optimization_cases.yaml').read_text())['cases']
    results = []
    with tempfile.TemporaryDirectory(prefix='context-eval-') as temp:
        store = RawEvidenceStore(Path(temp) / 'raw')
        for case in cases[:args.limit]:
            prepared = optimize_case(case, store)
            row = {'id': case['id']}
            for mode in ('baseline', 'optimized'):
                prompt = ('Answer the task using only the supplied context. Explain the cause, '
                          'safe action and critical constraints. Do not use tools.\n\n' + prepared[mode])
                proc = subprocess.run(['codex', 'exec', '--ephemeral', '--ignore-user-config',
                                       '--skip-git-repo-check', '--sandbox', 'read-only',
                                       '--model', args.model, '--cd', temp, '-'],
                                      input=prompt, text=True, capture_output=True, timeout=180)
                if proc.returncode:
                    raise RuntimeError('{} {} failed: {}'.format(case['id'], mode, proc.stderr[-1000:]))
                answer = proc.stdout.strip()
                row[mode] = {'answer': answer,
                             'missing_expected_phrases': [x for x in case['must_include']
                                                          if x.casefold() not in answer.casefold()]}
            results.append(row)
            print(json.dumps(row, ensure_ascii=False), flush=True)
    print('Completed {} paired trials; phrase matching requires manual review.'.format(len(results)))


if __name__ == '__main__':
    main()
