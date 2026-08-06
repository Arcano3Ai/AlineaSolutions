import json
import os
from database.models import Section, Chapter, Heading, Subheading, RGIRule

DATA_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'hs_codes.json')

def load_hs_data(session):
    if session.query(Section).count() > 0:
        return
    if not os.path.exists(DATA_FILE):
        return
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    for sec_data in data.get('sections', []):
        section = Section(
            code=sec_data['code'],
            title=sec_data['title'],
            description=sec_data.get('description', '')
        )
        session.add(section)
        session.flush()
        for ch_data in sec_data.get('chapters', []):
            chapter = Chapter(
                code=ch_data['code'],
                title=ch_data['title'],
                description=ch_data.get('description', ''),
                section_id=section.id
            )
            session.add(chapter)
            session.flush()
            for h_data in ch_data.get('headings', []):
                heading = Heading(
                    code=h_data['code'],
                    title=h_data['title'],
                    description=h_data.get('description', ''),
                    chapter_id=chapter.id
                )
                session.add(heading)
                session.flush()
                for s_data in h_data.get('subheadings', []):
                    subheading = Subheading(
                        code=s_data['code'],
                        title=s_data['title'],
                        description=s_data.get('description', ''),
                        heading_id=heading.id
                    )
                    session.add(subheading)
    session.commit()

def load_rgi_rules(session):
    if session.query(RGIRule).count() > 0:
        return
    rules = [
        {
            "rule_number": 1,
            "title": "Títulos de las Secciones, Capítulos o Subcapítulos",
            "content": "Los títulos de las Secciones, Capítulos o Subcapítulos solo tienen un valor indicativo, ya que la clasificación está determinada legalmente por los textos de las partidas y de las Notas de Sección o de Capítulo y, si no son contrarias a los textos de dichas partidas y Notas, de acuerdo con las Reglas siguientes.",
            "examples": "Ejemplo: El título de la Sección XI 'Materias textiles y sus manufacturas' no clasifica automáticamente todos los productos textiles; debe verificarse la partida específica."
        },
        {
            "rule_number": 2,
            "title": "Clasificación de artículos incompletos, mezclas y combinaciones",
            "content": "a) Cualquier referencia a un artículo en una partida comprende también al artículo incompleto o sin terminar, siempre que presente las características esenciales del artículo completo o terminado. b) Cualquier referencia a una materia comprende también las mezclas o combinaciones de dicha materia con otras.",
            "examples": "Ejemplo: Un automóvil sin motor aún conserva las características esenciales de un automóvil (partida 87.03)."
        },
        {
            "rule_number": 3,
            "title": "Clasificación de mercancías clasificables en dos o más partidas",
            "content": "a) La partida más específica prevalece sobre las más genéricas. b) Los productos mezclados o compuestos se clasifican según la materia que les confiera su carácter esencial. c) Cuando no sea posible aplicar a) o b), se clasificará en la última partida por orden de numeración.",
            "examples": "Ejemplo: Un cepillo de dientes eléctrico se clasifica como aparato eléctrico (85.43) o como cepillo (96.03). La regla 3a indica que la partida más específica es 96.03."
        },
        {
            "rule_number": 4,
            "title": "Clasificación por analogía",
            "content": "Las mercancías que no puedan clasificarse aplicando las reglas anteriores se clasifican en la partida que comprenda aquellas con las que tengan mayor analogía.",
            "examples": "Ejemplo: Se aplica cuando no existe una partida específica y se busca la mercancía más similar."
        },
        {
            "rule_number": 5,
            "title": "Clasificación de estuches, envases y continentes",
            "content": "a) Los estuches y continentes especialmente diseñados para contener un artículo determinado se clasifican con dicho artículo. b) Los envases que contengan mercancías se clasifican con ellas, excepto cuando sean claramente susceptibles de utilización repetida.",
            "examples": "Ejemplo: Un estuche para joyas se clasifica con las joyas que contiene (Regla 5a)."
        },
        {
            "rule_number": 6,
            "title": "Clasificación de subpartidas",
            "content": "La clasificación de mercancías en las subpartidas de una misma partida está determinada legalmente por los textos de estas subpartidas y de las Notas de subpartida, aplicando las Reglas anteriores, con las adaptaciones necesarias.",
            "examples": "Ejemplo: Para clasificar a nivel de 6 dígitos, se aplican las reglas 1-5 dentro de la partida de 4 dígitos."
        },
    ]
    for i, rule in enumerate(rules, 1):
        session.add(RGIRule(
            rule_number=rule['rule_number'],
            title=rule['title'],
            content=rule['content'],
            examples=rule['examples']
        ))
    session.commit()
