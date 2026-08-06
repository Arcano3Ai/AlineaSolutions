import re
import os
from database.models import Section, Chapter, Heading, Subheading

TEXT_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'conocimiento', '_ligie_text.txt')

RE_NICO = re.compile(r'^(\d{4})\.(\d{2})\.(\d{2})$')
RE_HDG = re.compile(r'^(\d{2})\.(\d{2})$')
RE_SUB = re.compile(r'^(\d{4})\.(\d{2})$')

SECTION_TITLES = {
    'I': 'Animales vivos y productos del reino animal',
    'II': 'Productos del reino vegetal',
    'III': 'Grasas y aceites animales o vegetales',
    'IV': 'Productos de las industrias alimentarias, bebidas, licores y tabaco',
    'V': 'Productos minerales',
    'VI': 'Productos de las industrias qu\u00edmicas y conexas',
    'VII': 'Pl\u00e1stico y sus manufacturas; caucho y sus manufacturas',
    'VIII': 'Pieles, cueros, peleter\u00eda y manufacturas',
    'IX': 'Madera y sus manufacturas',
    'X': 'Pasta de madera, papel, cart\u00f3n y sus manufacturas',
    'XI': 'Materias textiles y sus manufacturas',
    'XII': 'Calzado, sombreros y otros art\u00edculos',
    'XIII': 'Manufacturas de piedra, yeso, cemento, vidrio',
    'XIV': 'Perlas finas, piedras preciosas y metales preciosos',
    'XV': 'Metales comunes y sus manufacturas',
    'XVI': 'M\u00e1quinas y aparatos, material el\u00e9ctrico',
    'XVII': 'Material de transporte',
    'XVIII': 'Instrumentos de precisi\u00f3n, m\u00fasica, relojer\u00eda',
    'XIX': 'Armas y municiones',
    'XX': 'Mercanc\u00edas y productos diversos',
    'XXI': 'Objetos de arte, colecci\u00f3n y antig\u00fcedades',
}

CHAPTER_TO_SECTION = {}
for ch in range(1, 99):
    cs = str(ch).zfill(2)
    if ch <= 5: CHAPTER_TO_SECTION[cs] = 'I'
    elif ch <= 14: CHAPTER_TO_SECTION[cs] = 'II'
    elif ch == 15: CHAPTER_TO_SECTION[cs] = 'III'
    elif ch <= 24: CHAPTER_TO_SECTION[cs] = 'IV'
    elif ch <= 27: CHAPTER_TO_SECTION[cs] = 'V'
    elif ch <= 38: CHAPTER_TO_SECTION[cs] = 'VI'
    elif ch <= 40: CHAPTER_TO_SECTION[cs] = 'VII'
    elif ch <= 43: CHAPTER_TO_SECTION[cs] = 'VIII'
    elif ch <= 46: CHAPTER_TO_SECTION[cs] = 'IX'
    elif ch <= 49: CHAPTER_TO_SECTION[cs] = 'X'
    elif ch <= 63: CHAPTER_TO_SECTION[cs] = 'XI'
    elif ch <= 67: CHAPTER_TO_SECTION[cs] = 'XII'
    elif ch <= 70: CHAPTER_TO_SECTION[cs] = 'XIII'
    elif ch == 71: CHAPTER_TO_SECTION[cs] = 'XIV'
    elif ch <= 83: CHAPTER_TO_SECTION[cs] = 'XV'
    elif ch <= 85: CHAPTER_TO_SECTION[cs] = 'XVI'
    elif ch <= 89: CHAPTER_TO_SECTION[cs] = 'XVII'
    elif ch <= 92: CHAPTER_TO_SECTION[cs] = 'XVIII'
    elif ch == 93: CHAPTER_TO_SECTION[cs] = 'XIX'
    elif ch <= 96: CHAPTER_TO_SECTION[cs] = 'XX'
    else: CHAPTER_TO_SECTION[cs] = 'XXI'

from sources.generator import generate_complete_hs


def _get_nico_from_text():
    nico_data = []
    if not os.path.exists(TEXT_PATH):
        return nico_data

    with open(TEXT_PATH, 'r', encoding='utf-8') as f:
        content = f.read()
    lines = content.split('\n')
    lines = [l.strip() for l in lines]

    current_6d = None
    for line in lines:
        mn = RE_NICO.match(line)
        if mn:
            full = mn.group(1) + mn.group(2) + mn.group(3)
            nico_data.append(full)

    nico_data = list(dict.fromkeys(nico_data))
    return nico_data


def load_ligie_into_db(session):
    session.query(Subheading).delete()
    session.query(Heading).delete()
    session.query(Chapter).delete()
    session.query(Section).delete()
    session.commit()

    gen_data = generate_complete_hs()
    nico_codes = _get_nico_from_text()

    sec_ids = {}
    for sec in gen_data['sections']:
        s = Section(code=sec['code'], title=sec['title'], description=sec.get('description', ''))
        session.add(s)
        session.flush()
        sec_ids[sec['code']] = s.id

    ch_ids = {}
    for sec in gen_data['sections']:
        for ch in sec['chapters']:
            c = Chapter(code=ch['code'], title=ch['title'], description=ch.get('description', ''),
                       section_id=sec_ids[sec['code']])
            session.add(c)
            session.flush()
            ch_ids[ch['code']] = c.id

    h_ids = {}
    for sec in gen_data['sections']:
        for ch in sec['chapters']:
            for h in ch['headings']:
                hi = Heading(code=h['code'], title=h['title'], description=h.get('description', ''),
                            chapter_id=ch_ids[ch['code']])
                session.add(hi)
                session.flush()
                h_ids[h['code']] = hi.id

    sub_count = 0
    for sec in gen_data['sections']:
        for ch in sec['chapters']:
            for h in ch['headings']:
                for s in h['subheadings']:
                    hi_id = h_ids.get(h['code'])
                    if hi_id:
                        sub = Subheading(code=s['code'], title=s['title'], description=s.get('description', ''),
                                        heading_id=hi_id)
                        session.add(sub)
                        sub_count += 1

    session.commit()

    # Cargar y sincronizar fracciones reales LIGIE
    try:
        from utils.load_nico_fractions import load_nico_fractions
        loaded_fracs = load_nico_fractions()
    except Exception as e:
        print(f"Error al cargar fracciones NICO: {e}")
        loaded_fracs = 0

    total_h = sum(len(h) for sec in gen_data['sections'] for ch in sec['chapters'] for h in ch['headings'])
    total_sh = sub_count

    return {
        "success": True,
        "source": "HS Generator + LIGIE NICO",
        "sections": len(gen_data['sections']),
        "chapters": sum(len(sec['chapters']) for sec in gen_data['sections']),
        "headings": total_h,
        "subheadings": total_sh,
        "nicos_ligie": len(nico_codes),
        "fractions_loaded": loaded_fracs,
        "message": "Datos HS cargados desde el generador oficial. %d c\u00f3digos NICO referenciados. %d fracciones importadas." % (len(nico_codes), loaded_fracs)
    }
