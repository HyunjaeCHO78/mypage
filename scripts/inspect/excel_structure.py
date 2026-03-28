#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

NS = {
    'main': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main',
    'rel': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
    'pkgrel': 'http://schemas.openxmlformats.org/package/2006/relationships',
}

CELL_RE = re.compile(r'([A-Z]+)(\d+)')


def col_to_index(col_letters: str) -> int:
    value = 0
    for char in col_letters:
        value = value * 26 + (ord(char) - 64)
    return value


def parse_coord(coord: str) -> tuple[int, int]:
    match = CELL_RE.fullmatch(coord)
    if not match:
        raise ValueError(f'Invalid cell coordinate: {coord}')
    col_letters, row_str = match.groups()
    return int(row_str), col_to_index(col_letters)


def get_shared_strings(zf: zipfile.ZipFile) -> list[str]:
    path = 'xl/sharedStrings.xml'
    if path not in zf.namelist():
        return []
    root = ET.fromstring(zf.read(path))
    strings = []
    for si in root.findall('main:si', NS):
        parts = []
        for text_node in si.findall('.//main:t', NS):
            parts.append(text_node.text or '')
        strings.append(''.join(parts))
    return strings


def get_sheet_targets(zf: zipfile.ZipFile) -> dict[str, str]:
    rel_root = ET.fromstring(zf.read('xl/_rels/workbook.xml.rels'))
    rels: dict[str, str] = {}
    for rel in rel_root.findall('pkgrel:Relationship', NS):
        rel_id = rel.attrib.get('Id')
        target = rel.attrib.get('Target')
        if rel_id and target:
            rels[rel_id] = 'xl/' + target.lstrip('/')
    return rels


def get_sheet_entries(zf: zipfile.ZipFile) -> list[tuple[str, str]]:
    wb_root = ET.fromstring(zf.read('xl/workbook.xml'))
    targets = get_sheet_targets(zf)
    entries: list[tuple[str, str]] = []
    for sheet in wb_root.findall('main:sheets/main:sheet', NS):
        name = sheet.attrib.get('name', 'UNKNOWN')
        rel_id = sheet.attrib.get('{%s}id' % NS['rel'])
        target = targets.get(rel_id, '')
        entries.append((name, target))
    return entries


def get_merged_ranges(zf: zipfile.ZipFile, sheet_path: str) -> list[str]:
    root = ET.fromstring(zf.read(sheet_path))
    return [node.attrib['ref'] for node in root.findall('main:mergeCells/main:mergeCell', NS) if 'ref' in node.attrib]


def cell_text(cell, shared_strings: list[str]) -> str | int | float | None:
    value_node = cell.find('main:v', NS)
    if value_node is None:
        inline = cell.find('main:is/main:t', NS)
        return inline.text if inline is not None else None
    raw = value_node.text
    if raw is None:
        return None
    cell_type = cell.attrib.get('t')
    if cell_type == 's':
        idx = int(raw)
        return shared_strings[idx] if 0 <= idx < len(shared_strings) else raw
    return raw


def scan_sheet(zf: zipfile.ZipFile, sheet_name: str, sheet_path: str, shared_strings: list[str]) -> dict:
    root = ET.fromstring(zf.read(sheet_path))
    cells = root.findall('.//main:sheetData/main:row/main:c', NS)
    non_empty_coords: list[tuple[int, int]] = []
    formula_count = 0
    value_count = 0
    sample_by_row: dict[int, list[tuple[int, str, object]]] = {}

    for cell in cells:
        ref = cell.attrib.get('r')
        if not ref:
            continue
        row_idx, col_idx = parse_coord(ref)
        value = cell_text(cell, shared_strings)
        if value not in (None, ''):
            non_empty_coords.append((row_idx, col_idx))
            value_count += 1
            sample_by_row.setdefault(row_idx, []).append((col_idx, ref, value))
        if cell.find('main:f', NS) is not None:
            formula_count += 1

    if non_empty_coords:
        first_row = min(r for r, _ in non_empty_coords)
        last_row = max(r for r, _ in non_empty_coords)
        first_col = min(c for _, c in non_empty_coords)
        last_col = max(c for _, c in non_empty_coords)
        start_ref = min(
            ((r, c) for r, c in non_empty_coords),
            key=lambda item: (item[0], item[1])
        )
        table_start = next(
            ref for row in sample_by_row.values() for _, ref, _ in row
            if parse_coord(ref) == start_ref
        )
    else:
        first_row = last_row = first_col = last_col = None
        table_start = None

    sample_rows = []
    for row_idx in sorted(sample_by_row)[:8]:
        row_cells = sorted(sample_by_row[row_idx], key=lambda item: item[0])[:12]
        sample_rows.append({
            'row': row_idx,
            'cells': [{ref: value} for _, ref, value in row_cells],
        })

    return {
        'sheet_name': sheet_name,
        'sheet_path': sheet_path,
        'first_used_row': first_row,
        'last_used_row': last_row,
        'first_used_column': first_col,
        'last_used_column': last_col,
        'table_start_candidate': table_start,
        'formula_cell_count': formula_count,
        'value_cell_count': value_count,
        'merged_ranges': get_merged_ranges(zf, sheet_path),
        'sample_rows': sample_rows,
    }


def inspect_workbook(path: Path) -> dict:
    report = {'path': str(path), 'exists': path.exists()}
    if not path.exists():
        report['error'] = 'file not found'
        return report

    with zipfile.ZipFile(path) as zf:
        shared_strings = get_shared_strings(zf)
        sheet_entries = get_sheet_entries(zf)
        report['sheet_names'] = [name for name, _ in sheet_entries]
        report['sheet_count'] = len(sheet_entries)
        report['sheets'] = [scan_sheet(zf, name, target, shared_strings) for name, target in sheet_entries]
    return report


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print('Usage: python3 scripts/inspect/excel_structure.py <file1.xlsx> [file2.xlsx ...]', file=sys.stderr)
        return 1
    reports = [inspect_workbook(Path(arg)) for arg in argv[1:]]
    print(json.dumps(reports, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv))
