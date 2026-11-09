# Deoks PUE & WUE CSV Validator (`pue_wue.py`)

Zero-dependency Python 3 CLI for validating monthly data-center energy and water CSV files before calculating period **PUE** (*Power Usage Effectiveness*) and **WUE** (*Water Usage Effectiveness*).

- **한국어 상세 해설 및 튜토리얼 (Deoks)**: [PUE·WUE 계산하기: Python CSV로 단위·기간·결측값 검증하기](https://deokss.blogspot.com/2026/10/puewue-python-csv.html)
- **English Infrastructure Analysis (Deoks)**: [Can Lower PUE Hide Higher Water Use in AI Data Centers?](https://deokss.blogspot.com/2026/10/can-lower-pue-hide-higher-water-use-in.html)

---

## Why This Tool Exists (왜 단순 평균·결측값 0 치환이 위험한가?)

When reviewing or aggregating monthly facility spreadsheets, three silent data bugs frequently distort reported PUE and WUE numbers:

1. **Unweighted monthly averaging**: Averaging monthly PUE ratios (`(2.0 + 1.2) / 2 = 1.6`) instead of dividing period numerator sums by period denominator sums (`1,280,000 kWh / 1,000,000 kWh = 1.28`).
2. **Power vs. Energy unit confusion**: Entering instantaneous power (`kW`, `MW`) into energy (`kWh`, `MWh`) columns or mixing `m3` and `L` without explicit normalization.
3. **Blank cells treated as zero / mixed boundaries**: Treating missing water meter months as `0`, skipping missing months, or combining `consumption` and `withdrawal` rows in a single ratio.

`pue_wue.py` enforces strict boundary, unit, and continuity checks using Python's standard library (`csv`, `decimal.Decimal` at 28-digit precision) with **zero third-party packages**.

---

## Quickstart (빠른 실행)

Requires **Python 3.10+** (standard library only).

```bash
# 1. Valid 2-month mixed-unit example (MWh + kWh, m3 + L)
python pue_wue.py examples/valid_2m_mixed_units.csv

# 2. Intentional unit error check (kW entered instead of kWh -> exits with code 2)
python pue_wue.py examples/invalid_kw_power_unit.csv

# 3. Intentional month gap & missing cell check (-> exits with code 2)
python pue_wue.py examples/invalid_missing_month_gap.csv

# 4. Run full 23-case validation suite
python -m unittest discover -s tests -v
```

### Expected Output (`examples/valid_2m_mixed_units.csv`)

```json
{
  "months": [
    "2026-01",
    "2026-02"
  ],
  "scope_id": "demo-a",
  "water_basis": "consumption",
  "complete_calendar_year": false,
  "facility_kwh": "1280000",
  "it_kwh": "1000000",
  "water_l": "190000",
  "period_pue": "1.28",
  "period_water_l_per_it_kwh": "0.19"
}
```

---

## CSV Input Schema (입력 CSV 규격)

 UTF-8 and UTF-8 with BOM (`utf-8-sig`) are supported. Header order must match exactly:

| Column | Allowed Values | Rule |
| :--- | :--- | :--- |
| `month` | `YYYY-MM` | Unique, strictly consecutive months across the file (`complete_calendar_year` is `true` only for a full `01..12` calendar year). |
| `scope_id` | Non-empty string | Identical across all rows so distinct sites or meter boundaries are never silently merged. |
| `facility` | Finite `> 0` | Total facility energy for the month (`facility >= it` enforced). |
| `facility_unit` | `kWh`, `MWh` | Normalized to `kWh` (`kW` / `MW` power units are rejected). |
| `it` | Finite `> 0` | IT equipment energy for the month. |
| `it_unit` | `kWh`, `MWh` | Normalized to `kWh`. |
| `water` | Finite `>= 0` | Explicit `0` is allowed; blank cells are rejected (`missing value is not zero`). |
| `water_unit` | `L`, `m3` | Normalized to `L`. |
| `water_basis` | `consumption`, `withdrawal` | Must remain consistent across all rows in the period. |

---

## Scope & Limitations (해석 시 주의사항)

- Sample CSVs in `examples/` are synthetic fixtures created to verify arithmetic and schema boundaries, not measurements from any live facility.
- Passing CSV validation confirms arithmetic, unit normalization, and period continuity for the supplied numbers; it does **not** certify physical meter accuracy, non-electric thermal inputs, or official ISO/IEC 30134-2 / Green Grid compliance.

## License

MIT License — see [LICENSE](./LICENSE).
