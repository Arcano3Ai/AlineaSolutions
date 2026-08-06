import io
import pandas as pd
from database.models import Classification, Subheading, Heading, Chapter

def export_classifications_csv(session):
    classifications = session.query(Classification).order_by(Classification.created_at.desc()).all()
    data = []
    for c in classifications:
        data.append({
            'ID': c.id,
            'Producto': c.product_description,
            'Código HS': c.hs_code,
            'Confianza': c.confidence,
            'Método': c.method,
            'Notas': c.notes or '',
            'Fecha': c.created_at.strftime('%Y-%m-%d %H:%M:%S') if c.created_at else ''
        })
    df = pd.DataFrame(data)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Clasificaciones')
    output.seek(0)
    return output

def export_classifications_excel(session):
    return export_classifications_csv(session)

def import_classifications_csv(session, file_content):
    try:
        df = pd.read_csv(io.StringIO(file_content))
        count = 0
        for _, row in df.iterrows():
            c = Classification(
                product_description=row.get('Producto', row.get('product_description', '')),
                hs_code=str(row.get('Código HS', row.get('hs_code', ''))),
                confidence=float(row.get('Confianza', row.get('confidence', 0))),
                method=row.get('Método', row.get('method', 'import')),
                notes=row.get('Notas', row.get('notes', '')),
            )
            session.add(c)
            count += 1
        session.commit()
        return {'success': True, 'count': count}
    except Exception as e:
        return {'success': False, 'error': str(e)}

def import_classifications_excel(session, file_bytes):
    try:
        df = pd.read_excel(io.BytesIO(file_bytes), engine='openpyxl')
        count = 0
        for _, row in df.iterrows():
            c = Classification(
                product_description=row.get('Producto', row.get('product_description', '')),
                hs_code=str(row.get('Código HS', row.get('hs_code', ''))),
                confidence=float(row.get('Confianza', row.get('confidence', 0))),
                method=row.get('Método', row.get('method', 'import')),
                notes=row.get('Notas', row.get('notes', '')),
            )
            session.add(c)
            count += 1
        session.commit()
        return {'success': True, 'count': count}
    except Exception as e:
        return {'success': False, 'error': str(e)}

def export_hs_catalog_excel(session):
    data = []
    for sub in session.query(Subheading).all():
        heading = sub.heading
        chapter = heading.chapter
        data.append({
            'Sección': chapter.section.title if chapter.section else '',
            'Capítulo': chapter.code,
            'Capítulo Título': chapter.title,
            'Partida': heading.code,
            'Partida Título': heading.title,
            'Subpartida': sub.code,
            'Subpartida Título': sub.title,
        })
    df = pd.DataFrame(data)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Catálogo HS')
    output.seek(0)
    return output
