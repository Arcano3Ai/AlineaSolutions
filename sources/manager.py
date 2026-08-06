from sources.generator import save_hs_data, generate_complete_hs
from sources.official import (get_source_status, TARICSource, search_all_official_sources,
                              verify_hs_code_with_official_sources, download_official_hs_database,
                              OFFICIAL_SOURCES)
from database.models import Section, Chapter, Heading, Subheading
import datetime


def reload_hs_from_generator(session):
    data = generate_complete_hs()
    _import_hs_data(session, data)
    return {
        "success": True,
        "sections": len(data["sections"]),
        "chapters": sum(len(s["chapters"]) for s in data["sections"]),
        "headings": sum(1 for s in data["sections"] for c in s["chapters"] for h in c["headings"]),
        "subheadings": sum(len(h["subheadings"]) for s in data["sections"] for c in s["chapters"] for h in c["headings"]),
        "message": "Base de datos HS regenerada correctamente"
    }


def _import_hs_data(session, data):
    session.query(Subheading).delete()
    session.query(Heading).delete()
    session.query(Chapter).delete()
    session.query(Section).delete()
    session.commit()

    for sec_data in data["sections"]:
        section = Section(
            code=sec_data["code"],
            title=sec_data["title"],
            description=sec_data.get("description", "")
        )
        session.add(section)
        session.flush()
        for ch_data in sec_data["chapters"]:
            chapter = Chapter(
                code=ch_data["code"],
                title=ch_data["title"],
                description=ch_data.get("description", ""),
                section_id=section.id
            )
            session.add(chapter)
            session.flush()
            for h_data in ch_data["headings"]:
                heading = Heading(
                    code=h_data["code"],
                    title=h_data["title"],
                    description=h_data.get("description", ""),
                    chapter_id=chapter.id
                )
                session.add(heading)
                session.flush()
                for s_data in h_data["subheadings"]:
                    subheading = Subheading(
                        code=s_data["code"],
                        title=s_data["title"],
                        description=s_data.get("description", ""),
                        heading_id=heading.id
                    )
                    session.add(subheading)
    session.commit()


def get_official_sources_list():
    return OFFICIAL_SOURCES


def sync_from_official_sources(session):
    result = download_official_hs_database(session)
    return result


def get_database_stats(session):
    sections = session.query(Section).count()
    chapters = session.query(Chapter).count()
    headings = session.query(Heading).count()
    subheadings = session.query(Subheading).count()
    return {
        "sections": sections,
        "chapters": chapters,
        "headings": headings,
        "subheadings": subheadings,
        "total_codes": subheadings
    }


def rebuild_database(session):
    data = generate_complete_hs()
    _import_hs_data(session, data)
    return get_database_stats(session)
