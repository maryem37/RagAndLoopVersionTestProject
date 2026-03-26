import json

with open('output/reports/coverage_report_auth_20260323_203124.json') as f:
    data = json.load(f)
    packages = data.get('packages', [])
    print(f'Total packages: {len(packages)}')
    print('Packages in coverage report:')
    for p in packages[:10]:
        cov = p['lines']['rate_%']
        print(f"  {p['package']}: {cov}% lines")
