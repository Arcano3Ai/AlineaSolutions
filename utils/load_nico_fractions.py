import sys, os, json, re
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__))))
from database.models import init_db, get_session, Subheading, Fraction, Heading, Chapter, Section

def _find_or_create_parent(session, parent_6):
    """Find existing subheading or create a virtual one linked to proper heading/chapter."""
    sub = session.query(Subheading).filter_by(code=parent_6).first()
    if sub:
        return sub
    
    # Try to find the heading (4-digit)
    heading_code = parent_6[:4]
    heading = session.query(Heading).filter_by(code=heading_code).first()
    
    if heading:
        # Create subheading under existing heading
        sub = Subheading(
            code=parent_6,
            title=f"Subpartida {parent_6}",
            description="",
            heading_id=heading.id
        )
        session.add(sub)
        session.flush()
        return sub
    
    # Try to find the chapter (2-digit)
    chapter_code = parent_6[:2]
    chapter = session.query(Chapter).filter_by(code=chapter_code).first()
    
    if chapter:
        # Create heading + subheading
        heading = Heading(
            code=heading_code,
            title=f"Partida {heading_code}",
            description=f"Partida {heading_code}",
            chapter_id=chapter.id
        )
        session.add(heading)
        session.flush()
        sub = Subheading(
            code=parent_6,
            title=f"Subpartida {parent_6}",
            description="",
            heading_id=heading.id
        )
        session.add(sub)
        session.flush()
        return sub
    
    # Try to find the section (Roman numeral from chapter)
    # Crude mapping: chapter ranges correspond to sections
    ch_num = int(chapter_code)
    section_map = [
        (1, 5, "I"), (6, 14, "II"), (15, 15, "III"), (16, 24, "IV"),
        (25, 27, "V"), (28, 39, "VI"), (40, 43, "VII"), (44, 46, "VIII"),
        (47, 49, "IX"), (50, 63, "X"), (64, 67, "XI"), (68, 70, "XII"),
        (71, 71, "XIII"), (72, 83, "XIV"), (84, 85, "XV"), (86, 89, "XVI"),
        (90, 92, "XVII"), (93, 93, "XVIII"), (94, 96, "XIX"), (97, 97, "XX"),
    ]
    sec_code = "XXI"
    for lo, hi, sc in section_map:
        if lo <= ch_num <= hi:
            sec_code = sc
            break
    
    section = session.query(Section).filter_by(code=sec_code).first()
    if not section:
        section = Section(
            code=sec_code,
            title=f"Secci\u00f3n {sec_code}",
            description=f"Secci\u00f3n {sec_code}"
        )
        session.add(section)
        session.flush()
    
    chapter = Chapter(
        code=chapter_code,
        title=f"Cap\u00edtulo {chapter_code}",
        description=f"Cap\u00edtulo {chapter_code}",
        section_id=section.id
    )
    session.add(chapter)
    session.flush()
    
    heading = Heading(
        code=heading_code,
        title=f"Partida {heading_code}",
        description=f"Partida {heading_code}",
        chapter_id=chapter.id
    )
    session.add(heading)
    session.flush()
    
    sub = Subheading(
        code=parent_6,
        title=f"Subpartida {parent_6}",
        description="",
        heading_id=heading.id
    )
    session.add(sub)
    session.flush()
    return sub


def load_nico_fractions():
    nico_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "nico_real_descriptions.json")
    with open(nico_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    nico_map = data["by_8digit"]

    engine = init_db()
    session = get_session(engine)

    # Clear existing fractions
    session.query(Fraction).delete()
    session.commit()

    matched = 0
    errors = 0
    created_subs = 0

    for nico_code, desc in nico_map.items():
        parts = nico_code.split(".")
        if len(parts) != 3:
            errors += 1
            continue
        
        clean_8 = parts[0] + parts[1] + parts[2]
        parent_6 = parts[0] + parts[1]

        sub = _find_or_create_parent(session, parent_6)
        if sub is None:
            errors += 1
            continue
        
        # Check if sub was just created
        if sub.description == "":
            created_subs += 1

        # Enriquecer la descripción con el contexto jerárquico
        parent_context = ""
        if sub:
            parent_context += f" {sub.title or ''} {sub.description or ''}"
            if sub.heading:
                parent_context += f" {sub.heading.title or ''} {sub.heading.description or ''}"
                if sub.heading.chapter:
                    parent_context += f" {sub.heading.chapter.title or ''}"

        full_desc = f"{desc} | {parent_context}".strip()

        frac = Fraction(
            code=clean_8,
            title=desc,
            description=full_desc,
            subheading_id=sub.id
        )
        session.add(frac)
        matched += 1

    session.commit()

    print(f"Total NICO codes: {len(nico_map)}")
    print(f"Loaded as Fractions: {matched}")
    print(f"Errors: {errors}")
    print(f"Subheadings auto-created: {created_subs}")

    frac_count = session.query(Fraction).count()
    sub_with = session.query(Subheading).filter(Subheading.fractions.any()).count()
    sub_total = session.query(Subheading).count()
    h_total = session.query(Heading).count()
    ch_total = session.query(Chapter).count()
    sec_total = session.query(Section).count()
    print(f"\nFractions in DB: {frac_count}")
    print(f"Subheadings with fractions: {sub_with} / {sub_total}")
    print(f"Total headings: {h_total}")
    print(f"Total chapters: {ch_total}")
    print(f"Total sections: {sec_total}")

    return matched

if __name__ == "__main__":
    load_nico_fractions()
