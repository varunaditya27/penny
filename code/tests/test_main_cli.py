import csv
import os
import tempfile
import unittest
from unittest.mock import patch

from code.main import main, run_pipeline


class TestMainCLI(unittest.TestCase):
    """Verifies that the CLI entry point runs correctly in both sample and production modes."""

    def test_run_pipeline_sample_mode(self):
        with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.csv') as tmp:
            tmp_path = tmp.name

        try:
            run_pipeline(sample_mode=True, output_path=tmp_path, tolerance=10.0)

            # Check that output file exists and has 25 rows + header
            self.assertTrue(os.path.exists(tmp_path))
            with open(tmp_path, newline='', encoding='utf-8') as f:
                reader = list(csv.reader(f))
            self.assertEqual(len(reader), 26)  # 1 header + 25 rows
            self.assertEqual(reader[0][0], 'request_id')
            self.assertEqual(reader[1][0], 'request_01')
            self.assertEqual(reader[-1][0], 'request_25')
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_cli_argument_parsing(self):
        with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.csv') as tmp:
            tmp_path = tmp.name

        try:
            test_args = ['main.py', '--eval-sample', '--output', tmp_path, '--tolerance', '10.0']
            with patch('sys.argv', test_args):
                main()

            self.assertTrue(os.path.exists(tmp_path))
            with open(tmp_path, newline='', encoding='utf-8') as f:
                reader = list(csv.reader(f))
            self.assertEqual(len(reader), 26)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)


if __name__ == '__main__':
    unittest.main()
