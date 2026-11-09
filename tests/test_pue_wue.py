import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / 'pue_wue.py'
HEADER = 'month,scope_id,facility,facility_unit,it,it_unit,water,water_unit,water_basis'
ROWS = [
    '2026-01,demo-a,200,MWh,100,MWh,10,m3,consumption',
    '2026-02,demo-a,1080000,kWh,900000,kWh,180000,L,consumption',
]


def execute(rows=None, header=HEADER, bom=False):
    text = header + '\n' + '\n'.join(ROWS if rows is None else rows) + '\n'
    with tempfile.TemporaryDirectory() as folder:
        file = Path(folder) / 'example.csv'
        file.write_text(text, encoding='utf-8-sig' if bom else 'utf-8')
        return subprocess.run(
            [sys.executable, str(SCRIPT), str(file)],
            capture_output=True,
            text=True,
            encoding='utf-8',
        )


class CalculatorTests(unittest.TestCase):
    def good(self, rows=None, **kwargs):
        result = execute(rows, **kwargs)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def bad(self, rows, **kwargs):
        result = execute(rows, **kwargs)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, '')
        self.assertIn('ERROR:', result.stderr)

    def change(self, column, value, row=0):
        rows = [r.split(',') for r in ROWS]
        rows[row][HEADER.split(',').index(column)] = value
        return [','.join(r) for r in rows]

    def test_mixed_units_totals_and_ratios(self):
        value = self.good()
        self.assertEqual(value['facility_kwh'], '1280000')
        self.assertEqual(value['it_kwh'], '1000000')
        self.assertEqual(value['water_l'], '190000')
        self.assertEqual(value['period_pue'], '1.28')
        self.assertEqual(value['period_water_l_per_it_kwh'], '0.19')

    def test_not_unweighted_mean(self):
        self.assertNotEqual(self.good()['period_pue'], '1.6')

    def test_two_months_are_not_annual(self):
        self.assertFalse(self.good()['complete_calendar_year'])

    def test_missing_water_not_zero(self):
        self.bad(self.change('water', ''))

    def test_nan_rejected(self):
        self.bad(self.change('facility', 'NaN'))

    def test_infinity_rejected(self):
        self.bad(self.change('it', 'Infinity'))

    def test_negative_water_rejected(self):
        self.bad(self.change('water', '-1'))

    def test_zero_it_rejected(self):
        self.bad(self.change('it', '0'))

    def test_facility_less_than_it_rejected(self):
        self.bad(self.change('facility', '50'))

    def test_kw_is_not_energy(self):
        self.bad(self.change('facility_unit', 'kW'))

    def test_unknown_water_unit_rejected(self):
        self.bad(self.change('water_unit', 'gallon'))

    def test_water_basis_mismatch_rejected(self):
        self.bad(self.change('water_basis', 'withdrawal'))

    def test_scope_mismatch_rejected(self):
        self.bad(self.change('scope_id', 'other-site'))

    def test_duplicate_month_rejected(self):
        self.bad([ROWS[0], ROWS[0]])

    def test_gap_rejected(self):
        self.bad(self.change('month', '2026-04', 1))

    def test_invalid_month_rejected(self):
        self.bad(self.change('month', '2026-13'))

    def test_empty_rows_rejected(self):
        self.bad([])

    def test_duplicate_header_rejected(self):
        self.bad(ROWS, header=HEADER.replace('water_basis', 'water'))

    def test_extra_cell_rejected(self):
        self.bad([ROWS[0] + ',extra', ROWS[1]])

    def test_utf8_bom_supported(self):
        self.assertEqual(self.good(bom=True)['period_pue'], '1.28')

    def test_real_zero_water_allowed(self):
        rows = [r.replace(',10,m3,', ',0,m3,').replace(',180000,L,', ',0,L,') for r in ROWS]
        self.assertEqual(self.good(rows)['period_water_l_per_it_kwh'], '0')

    def test_twelve_month_calendar_year(self):
        rows = [f'2025-{m:02},demo-a,110,kWh,100,kWh,0,L,consumption' for m in range(1, 13)]
        self.assertTrue(self.good(rows)['complete_calendar_year'])

    def test_order_does_not_change_totals(self):
        self.assertEqual(self.good(list(reversed(ROWS)))['period_pue'], '1.28')

    def test_withdrawal_label_preserved(self):
        rows = [r.replace('consumption', 'withdrawal') for r in ROWS]
        self.assertEqual(self.good(rows)['water_basis'], 'withdrawal')


if __name__ == '__main__':
    unittest.main(verbosity=2)
