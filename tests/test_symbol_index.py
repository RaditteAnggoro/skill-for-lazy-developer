from pathlib import Path
import unittest

from scripts.run_symbol_index_benchmark import EXPECTED, FIXTURE, index_edges, indexed_sites


class SymbolIndexTests(unittest.TestCase):
    def test_fixture_resolves_aliases_and_qualified_calls_without_decoys(self):
        sites, _ = indexed_sites(FIXTURE, EXPECTED)
        self.assertEqual(sites, EXPECTED)

    def test_ambiguous_bindings_do_not_claim_an_edge(self):
        cases = {
            'target rebound': ('def convert(value): return value\nconvert = external\n',
                               'from units import convert\ndef run(value): return convert(value)\n'),
            'conditional rebinding': ('def convert(value): return value\n',
                                      'from units import convert\nif flag:\n    from other import convert\n'
                                      'def run(value): return convert(value)\n'),
            'wildcard rebinding': ('def convert(value): return value\n',
                                   'from units import convert\nfrom other import *\n'
                                   'def run(value): return convert(value)\n'),
            'scope shadow': ('def convert(value): return value\n',
                             'from units import convert\ndef run(convert, value): return convert(value)\n'),
            'nested scope': ('def convert(value): return value\n',
                             'from units import convert\ndef run(value): return lambda: convert(value)\n'),
        }
        for label, (units, pipeline) in cases.items():
            with self.subTest(label=label):
                self.assertEqual(index_edges({Path('units.py'): units, Path('pipeline.py'): pipeline}), [])
