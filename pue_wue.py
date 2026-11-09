import csv
import json
import sys
from datetime import datetime
from decimal import Decimal, DecimalException, localcontext

FIELDS = ['month', 'scope_id', 'facility', 'facility_unit', 'it',
          'it_unit', 'water', 'water_unit', 'water_basis']
ENERGY = {'kWh': Decimal(1), 'MWh': Decimal(1000)}
WATER = {'L': Decimal(1), 'm3': Decimal(1000)}


def quantity(row, name, factors, allow_zero=False):
    text = row[name].strip()
    if not text:
        raise ValueError(f'{name}: missing value is not zero')
    value = Decimal(text)
    if not value.is_finite() or value < 0 or (value == 0 and not allow_zero):
        raise ValueError(f'{name}: invalid finite quantity')
    unit = row[name + '_unit'].strip()
    if unit not in factors:
        raise ValueError(f'{name}: unsupported unit {unit!r}')
    return value * factors[unit]


def calculate(file):
    with open(file, encoding='utf-8-sig', newline='') as handle:
        reader = csv.DictReader(handle, strict=True)
        if reader.fieldnames != FIELDS:
            raise ValueError('header must match the documented schema')
        rows = list(reader)
    if not rows:
        raise ValueError('CSV has no data rows')
    months, scopes, bases = set(), set(), set()
    facility = it = water = Decimal(0)
    with localcontext() as context:
        context.prec = 28
        for row in rows:
            if set(row) != set(FIELDS) or any(v is None for v in row.values()):
                raise ValueError('row has missing or extra cells')
            month = row['month'].strip()
            date = datetime.strptime(month, '%Y-%m')
            if date.strftime('%Y-%m') != month or month in months:
                raise ValueError('month must be unique YYYY-MM')
            months.add(month)
            scope = row['scope_id'].strip()
            basis = row['water_basis'].strip()
            if not scope or basis not in {'consumption', 'withdrawal'}:
                raise ValueError('scope_id and explicit water_basis are required')
            scopes.add(scope)
            bases.add(basis)
            f = quantity(row, 'facility', ENERGY)
            i = quantity(row, 'it', ENERGY)
            w = quantity(row, 'water', WATER, allow_zero=True)
            if f < i:
                raise ValueError('facility energy below IT: check meter boundaries')
            facility, it, water = facility + f, it + i, water + w
        if len(scopes) != 1 or len(bases) != 1:
            raise ValueError('do not combine different scopes or water bases')
        ordered = sorted(months)
        indices = [int(m[:4]) * 12 + int(m[5:]) for m in ordered]
        if any(b - a != 1 for a, b in zip(indices, indices[1:])):
            raise ValueError('months must be consecutive; missing months are not zero')
        annual = (len(ordered) == 12 and ordered[0].endswith('-01')
                  and ordered[-1] == ordered[0][:4] + '-12')
        def text(value):
            result = format(value, 'f')
            return result.rstrip('0').rstrip('.') if '.' in result else result
        return {'months': ordered, 'scope_id': next(iter(scopes)),
                'water_basis': next(iter(bases)), 'complete_calendar_year': annual,
                'facility_kwh': text(facility), 'it_kwh': text(it),
                'water_l': text(water), 'period_pue': text(facility / it),
                'period_water_l_per_it_kwh': text(water / it)}


if __name__ == '__main__':
    try:
        if len(sys.argv) != 2:
            raise ValueError('usage: python pue_wue.py input.csv')
        result = calculate(sys.argv[1])
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (ValueError, OSError, csv.Error, DecimalException) as error:
        print(f'ERROR: {error}', file=sys.stderr)
        sys.exit(2)
