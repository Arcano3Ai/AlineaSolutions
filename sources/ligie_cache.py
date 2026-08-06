import pdfplumber
import json
import os
import time

PDF_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'conocimiento', 'LIGIE-UNIFICADA-LIGIE_20250728-20250728.pdf')
CACHE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'conocimiento', '_tables_cache.json')


def extract_all_tables():
    if os.path.exists(CACHE_PATH):
        with open(CACHE_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)

    all_tables = {}
    with pdfplumber.open(PDF_PATH) as pdf:
        total = len(pdf.pages)
        for i in range(total):
            tables = pdf.pages[i].extract_tables()
            if tables:
                clean = []
                for t in tables:
                    clean_t = []
                    for row in t:
                        clean_t.append([str(c).strip() if c else '' for c in row])
                    clean.append(clean_t)
                if clean:
                    all_tables[str(i)] = clean
            if (i + 1) % 100 == 0:
                print('  %d/%d pages (%.0f%%)' % (i + 1, total, (i + 1) / total * 100))

    os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
    with open(CACHE_PATH, 'w', encoding='utf-8') as f:
        json.dump(all_tables, f, ensure_ascii=False)
    print('Cache saved to %s' % CACHE_PATH)
    return all_tables


def parse_ligie_from_tables():
    all_tables = extract_all_tables()
    data = {
        'sections': [],
        'chapters': [],
        'headings': [],
        'subheadings': [],
        'nicos': []
    }
    seen_sec = set()
    seen_ch = set()
    seen_h = set()
    seen_sub = set()

    import re
    re_sec = re.compile(r'^Secci\u00f3n\s+(X{0,3}(?:IX|IV|V?I)?)\s*\.?$', re.I)
    re_ch = re.compile(r'^Cap\u00edtulo\s+(\d{2})\s*\.?$', re.I)
    re_h = re.compile(r'^(\d{2})\.(\d{2})$')
    re_sub = re.compile(r'^(\d{4})\.(\d{2})$')
    re_nico = re.compile(r'^(\d{4})\.(\d{2})\.(\d{2})$')

    current_section = None
    current_chapter = None

    def is_header(text):
        return bool(re_sec.match(text) or re_ch.match(text))

    for page_str in sorted(all_tables.keys(), key=int):
        tables = all_tables[page_str]

        # Check if first table is tariff table
        is_tariff = False
        for table in tables[:2]:
            for row in table[:4]:
                for c in row:
                    if 'C\u00d3DIGO' in c and 'DESCRIPCI\u00d3N' in c:
                        is_tariff = True
                        break

        for table in tables:
            if not table or len(table) < 3:
                continue

            for row in table:
                if not row:
                    continue
                first = row[0].strip() if row[0] else ''

                sm = re_sec.match(first)
                if sm:
                    current_section = sm.group(1)
                    if current_section not in seen_sec:
                        seen_sec.add(current_section)
                        data['sections'].append(current_section)
                    continue

                cm = re_ch.match(first)
                if cm:
                    current_chapter = cm.group(1)
                    if current_chapter not in seen_ch:
                        seen_ch.add(current_chapter)
                        data['chapters'].append(current_chapter)
                    continue

                if not is_tariff:
                    continue

                desc = row[2].strip().replace('\n', ' ') if len(row) > 2 and row[2] else ''

                mn = re_nico.match(first)
                if mn and desc:
                    full = mn.group(1) + mn.group(2) + mn.group(3)
                    data['nicos'].append({
                        'code': full,
                        'nico': row[1].strip() if len(row) > 1 else '',
                        'title': desc,
                        'chapter': current_chapter
                    })
                    continue

                ms = re_sub.match(first)
                if ms and desc:
                    full = ms.group(1) + ms.group(2)
                    if full not in seen_sub:
                        seen_sub.add(full)
                        data['subheadings'].append({
                            'code': full,
                            'title': desc,
                            'chapter': current_chapter
                        })
                    continue

                mh = re_h.match(first)
                if mh and desc:
                    full = mh.group(1) + mh.group(2)
                    if full not in seen_h:
                        seen_h.add(full)
                        data['headings'].append({
                            'code': full,
                            'title': desc,
                            'chapter': current_chapter
                        })

    return data


if __name__ == '__main__':
    import sys
    start = time.time()
    print('Extrayendo tablas del PDF LIGIE...')
    data = parse_ligie_from_tables()
    elapsed = time.time() - start
    print('\nResultados:')
    print('  Secciones: %d' % len(data['sections']))
    print('  Cap\u00edtulos: %d' % len(data['chapters']))
    print('  Partidas (4d): %d' % len(data['headings']))
    print('  Subpartidas (6d): %d' % len(data['subheadings']))
    print('  NICOs (8d): %d' % len(data['nicos']))
    print('  Tiempo: %.1f min' % (elapsed / 60))
