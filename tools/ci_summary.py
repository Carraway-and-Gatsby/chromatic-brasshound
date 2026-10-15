#!/usr/bin/env python3
"""Expose the existing ROM/emulator reports in a GitHub Actions job summary."""
import json
import os
from pathlib import Path


REPORTS = (
    ('Cartridge validation', Path('build/rom-validation.json')),
    ('Gameplay and campaign', Path('build/campaign-test-artifacts/report.json')),
    ('Browser input', Path('build/campaign-test-artifacts/browser-input-report.json')),
    ('Native UI', Path('build/ui-test-artifacts/display/report.json')),
    ('ROOK poses and collision', Path('build/rook-review/2026-10-15/after/report.json')),
)


def summary():
    lines = ['## BRASSHOUND ROM self-check', '',
             '| Suite | Result |', '|---|---|']
    detail = []
    passed = True
    rom_sha = None
    for name, path in REPORTS:
        if not path.exists():
            lines.append(f'| {name} | Report not produced |')
            passed = False
            continue
        report = json.loads(path.read_text())
        lines.append(f'| {name} | {"PASS" if report.get("passed") else "FAIL"} |')
        passed = passed and report.get('passed') is True
        if 'cases' in report:
            for case, result in report['cases'].items():
                if not result.get('passed'):
                    error = str(result.get('error', 'No error detail')).replace('\n', ' ').replace('|', '/')
                    lines.append(f'| ↳ {case} | {error} |')
            campaign = report['cases'].get('complete_campaign', {}).get('campaign')
            if campaign:
                detail.append(f'Input-only campaign: **{campaign["approximate_seconds"]}s**, '
                              f'{campaign["retries"]} retries, '
                              f'OAM peak {campaign["peak_oam"]}, '
                              f'scanline peak {campaign["peak_sprites_per_scanline"]}, '
                              f'overflow frames {campaign["sprite_overflow_frames"]}.')
        if 'sha256' in report or 'rom_validation' in report:
            rom_sha = report.get('sha256') or report['rom_validation'].get('sha256')
    if rom_sha:
        detail += ['', f'ROM SHA-256: `{rom_sha}`.']
    lines += ['', *detail, '',
              'ROM, symbols, JSON, native screenshots and APU recordings are in the run artifact.',
              'These checks exercise actual CGB emulation; physical hardware remains unverified.']
    return '\n'.join(lines) + '\n', passed


if __name__ == '__main__':
    output, passed = summary()
    destination = os.environ.get('GITHUB_STEP_SUMMARY')
    if destination:
        with Path(destination).open('a') as stream:
            stream.write(output)
    else:
        print(output, end='')
    raise SystemExit(0 if passed else 1)
