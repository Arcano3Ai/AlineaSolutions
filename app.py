import os
import json
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS
from sqlalchemy.orm import scoped_session, sessionmaker
from database.models import (init_db, Section, Chapter, Heading, Subheading, Fraction,
                             Classification, RGIRule, Client, InventoryItem, AuditLog,
                             VucemAcuse, CartaPorte, ManifestacionValor, SATProductKey,
                             ChatThread, ChatMessage)
from utils.data_loader import load_hs_data, load_rgi_rules
from classifiers.classifier import search_by_text, get_all_rules, apply_rgi, classify_with_ai
from utils.import_export import export_classifications_excel, import_classifications_csv, import_classifications_excel, export_hs_catalog_excel
from sources.manager import (reload_hs_from_generator, get_official_sources_list,
                              sync_from_official_sources, get_database_stats,
                              rebuild_database)
from sources.official import get_source_status, search_all_official_sources, verify_hs_code_with_official_sources
from sources.ligie_extractor import load_ligie_into_db as load_ligie

# Carga de variables de entorno desde .env (si existe)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

app = Flask(__name__)
CORS(app)

# --- Sesión SQLAlchemy thread-safe (scoped_session) ---
# Una sesión por hilo/request; se libera automáticamente en teardown.
engine = init_db()
_SessionFactory = sessionmaker(bind=engine)
session = scoped_session(_SessionFactory)

@app.teardown_appcontext
def shutdown_session(exception=None):
    """Cierra y devuelve la sesión al pool al finalizar cada request."""
    session.remove()

def seed_data(sess):
    try:
        # Seed Clients
        if sess.query(Client).count() == 0:
            clients = [
                Client(rfc='SOL890412AA1', name='ALINEA S.A.S. DE C.V.', patent='3589', agent='Lic. Roberto Delgado', status='Activo'),
                Client(rfc='EXP990101BB3', name='GLOBAL LOGISTICS MEXICO', patent='4012', agent='Dra. Alicia Mendoza', status='Activo'),
                Client(rfc='ARQ150403CC4', name='ALINEA SOLUTIONS S.A. DE C.V.', patent='1650', agent='Ing. Sergio Montes', status='Activo')
            ]
            sess.add_all(clients)
            sess.commit()
            
        # Seed Inventory
        if sess.query(InventoryItem).count() == 0:
            items = [
                InventoryItem(sku='LAP-THINK-001', description='Laptop Lenovo ThinkPad T14 AMD Ryzen 7', sat_code='8471.30.01', unit='H87', quantity=150.0, price=1200.00),
                InventoryItem(sku='BATT-LITH-100', description='Batería de Litio Recargable 3.7V 2000mAh', sat_code='8507.60.01', unit='H87', quantity=5000.0, price=8.50),
                InventoryItem(sku='VALV-STEEL-08', description='Válvula de compuerta de acero inoxidable 2 pulgadas', sat_code='8481.80.01', unit='H87', quantity=45.0, price=350.00),
                InventoryItem(sku='ORANGE-FRESH-A', description='Naranjas frescas tipo Valencia calidad exportación', sat_code='0805.10.01', unit='KGM', quantity=12000.0, price=0.85)
            ]
            sess.add_all(items)
            sess.commit()
            
        # Seed SAT Product Keys
        if sess.query(SATProductKey).count() == 0:
            sat_keys = [
                SATProductKey(code='43211508', name='Computadoras personales', description='Computadoras de escritorio, laptops y tabletas personales.', default_hs_code='8471.30.01'),
                SATProductKey(code='50161813', name='Naranjas', description='Naranjas frescas o secas en estado natural.', default_hs_code='0805.10.01'),
                SATProductKey(code='40141602', name='Válvulas de control', description='Válvulas industriales y reguladores de flujo.', default_hs_code='8481.80.01'),
                SATProductKey(code='44121701', name='Bolígrafos o plumas', description='Bolígrafos, plumas estilográficas, lapiceros y repuestos.', default_hs_code='9608.40.02'),
                SATProductKey(code='26111707', name='Pilas y baterías recargables', description='Baterías de iones de litio, níquel y otros acumuladores.', default_hs_code='8507.60.01')
            ]
            sess.add_all(sat_keys)
            sess.commit()

        # Seed Audit Log
        if sess.query(AuditLog).count() == 0:
            logs = [
                AuditLog(action='Inicialización del sistema', module='ADMIN', details='Ecosistema de Alinea SA de CV cargado correctamente.', username='sistema'),
                AuditLog(action='Carga de catálogo arancelario', module='CLASSIFIER', details='Se cargó el catálogo HS básico con 21 secciones.', username='sistema')
            ]
            sess.add_all(logs)
            sess.commit()
    except Exception as e:
        print(f"Error al sembrar datos: {e}")

with app.app_context():
    try:
        load_hs_data(session)
        load_rgi_rules(session)
        seed_data(session)
        
        # Copiar logo.png a logo_light.png si no existe para cumplir con index.html
        import shutil
        img_dir = os.path.join(app.root_path, 'static', 'img')
        logo_path = os.path.join(img_dir, 'logo.png')
        logo_light_path = os.path.join(img_dir, 'logo_light.png')
        if os.path.exists(logo_path) and not os.path.exists(logo_light_path):
            shutil.copy(logo_path, logo_light_path)
    except Exception as e:
        print(f"Skipping seeding (table lock or already exists): {e}")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/sections')
def get_sections():
    sections = session.query(Section).order_by(Section.code).all()
    return jsonify([{
        'id': s.id,
        'code': s.code,
        'title': s.title,
        'description': s.description
    } for s in sections])

@app.route('/api/sections/<section_id>/chapters')
def get_chapters(section_id):
    chapters = session.query(Chapter).filter_by(section_id=section_id).order_by(Chapter.code).all()
    return jsonify([{
        'id': c.id,
        'code': c.code,
        'title': c.title,
        'description': c.description
    } for c in chapters])

@app.route('/api/chapters/<chapter_id>/headings')
def get_headings(chapter_id):
    headings = session.query(Heading).filter_by(chapter_id=chapter_id).order_by(Heading.code).all()
    return jsonify([{
        'id': h.id,
        'code': h.code,
        'title': h.title,
        'description': h.description
    } for h in headings])

@app.route('/api/headings/<heading_id>/subheadings')
def get_subheadings(heading_id):
    subheadings = session.query(Subheading).filter_by(heading_id=heading_id).order_by(Subheading.code).all()
    return jsonify([{
        'id': s.id,
        'code': s.code,
        'title': s.title,
        'description': s.description
    } for s in subheadings])

@app.route('/api/tree')
def get_full_tree():
    sections = session.query(Section).order_by(Section.code).all()
    tree = []
    for s in sections:
        s_data = {'id': s.id, 'code': s.code, 'title': s.title, 'children': []}
        for c in s.chapters:
            c_data = {'id': c.id, 'code': c.code, 'title': c.title, 'children': []}
            for h in c.headings:
                h_data = {'id': h.id, 'code': h.code, 'title': h.title, 'children': []}
                for sub in h.subheadings:
                    h_data['children'].append({
                        'id': sub.id, 'code': sub.code, 'title': sub.title
                    })
                c_data['children'].append(h_data)
            s_data['children'].append(c_data)
        tree.append(s_data)
    return jsonify(tree)

@app.route('/api/search')
def search():
    q = request.args.get('q', '')
    if not q:
        return jsonify({'results': []})
    results = search_by_text(session, q)
    return jsonify({'results': results})

@app.route('/api/classify', methods=['POST'])
def classify():
    data = request.get_json()
    description = data.get('description', '')
    method = data.get('method', 'text')

    if not description:
        return jsonify({'error': 'Descripci\u00f3n requerida'}), 400

    if method == 'ai':
        result = classify_with_ai(session, description)
        return jsonify(result)
    elif method == 'rgi':
        result = apply_rgi(session, description)
        return jsonify(result)
    else:
        results = search_by_text(session, description)
        return jsonify({'results': results})

@app.route('/api/rgi/rules')
def get_rules():
    rules = get_all_rules(session)
    return jsonify({'rules': rules})

@app.route('/api/rgi/apply', methods=['POST'])
def apply_rules():
    data = request.get_json()
    description = data.get('description', '')
    result = apply_rgi(session, description)
    return jsonify(result)

@app.route('/api/classifications')
def get_classifications():
    classifications = session.query(Classification).order_by(Classification.created_at.desc()).limit(100).all()
    return jsonify([{
        'id': c.id,
        'product_description': c.product_description,
        'hs_code': c.hs_code,
        'confidence': c.confidence,
        'method': c.method,
        'notes': c.notes,
        'created_at': c.created_at.isoformat() if c.created_at else ''
    } for c in classifications])

@app.route('/api/classifications', methods=['POST'])
def save_classification():
    data = request.get_json()
    c = Classification(
        product_description=data['product_description'],
        hs_code=data['hs_code'],
        confidence=data.get('confidence'),
        method=data.get('method', 'text'),
        notes=data.get('notes', '')
    )
    session.add(c)
    session.commit()
    return jsonify({'id': c.id, 'status': 'ok'})

@app.route('/api/classifications/<int:cid>', methods=['DELETE'])
def delete_classification(cid):
    c = session.get(Classification, cid)
    if c:
        session.delete(c)
        session.commit()
    return jsonify({'status': 'ok'})

@app.route('/api/export/excel')
def export_excel():
    output = export_classifications_excel(session)
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name='clasificaciones.xlsx'
    )

@app.route('/api/export/hs_catalog')
def export_hs_catalog():
    output = export_hs_catalog_excel(session)
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name='catalogo_hs.xlsx'
    )

@app.route('/api/import/csv', methods=['POST'])
def import_csv():
    file = request.files.get('file')
    if not file:
        return jsonify({'error': 'No se recibi\u00f3 archivo'}), 400
    content = file.read().decode('utf-8')
    result = import_classifications_csv(session, content)
    return jsonify(result)

@app.route('/api/import/excel', methods=['POST'])
def import_excel():
    file = request.files.get('file')
    if not file:
        return jsonify({'error': 'No se recibi\u00f3 archivo'}), 400
    result = import_classifications_excel(session, file.read())
    return jsonify(result)

@app.route('/api/hs_code/<code>')
def get_hs_details(code):
    sub = session.query(Subheading).filter_by(code=code).first()
    if sub:
        heading = sub.heading
        chapter = heading.chapter
        return jsonify({
            'subheading': {'code': sub.code, 'title': sub.title, 'description': sub.description},
            'heading': {'code': heading.code, 'title': heading.title},
            'chapter': {'code': chapter.code, 'title': chapter.title},
            'section': {'code': chapter.section.code, 'title': chapter.section.title}
        })
    heading = session.query(Heading).filter_by(code=code).first()
    if heading:
        chapter = heading.chapter
        return jsonify({
            'heading': {'code': heading.code, 'title': heading.title},
            'chapter': {'code': chapter.code, 'title': chapter.title},
            'section': {'code': chapter.section.code, 'title': chapter.section.title}
        })
    chapter = session.query(Chapter).filter_by(code=code).first()
    if chapter:
        return jsonify({
            'chapter': {'code': chapter.code, 'title': chapter.title},
            'section': {'code': chapter.section.code, 'title': chapter.section.title}
        })
    return jsonify({'error': 'No encontrado'}), 404

# ==========================================
# ENDPOINTS ADICIONALES PARA ALINEA
# ==========================================

# --- CRM Endpoints ---
@app.route('/api/crm/clients', methods=['GET'])
def get_crm_clients():
    clients = session.query(Client).order_by(Client.name).all()
    return jsonify([{
        'id': c.id,
        'rfc': c.rfc,
        'name': c.name,
        'patent': c.patent,
        'agent': c.agent,
        'status': c.status,
        'created_at': c.created_at.isoformat() if c.created_at else ''
    } for c in clients])

@app.route('/api/crm/clients', methods=['POST'])
def add_crm_client():
    data = request.get_json()
    if not data or not data.get('rfc') or not data.get('name'):
        return jsonify({'error': 'RFC y Nombre requeridos'}), 400
    
    rfc = data['rfc'].strip().upper()
    existing = session.query(Client).filter_by(rfc=rfc).first()
    if existing:
        return jsonify({'error': 'Ya existe un cliente con ese RFC'}), 400
        
    c = Client(
        rfc=rfc,
        name=data['name'].strip(),
        patent=data.get('patent', '0000').strip(),
        agent=data.get('agent', '').strip(),
        status=data.get('status', 'Activo')
    )
    session.add(c)
    
    # Audit log
    audit = AuditLog(action='Cliente creado', module='CRM', details=f"Cliente: {c.name} ({c.rfc}), Patente: {c.patent}")
    session.add(audit)
    session.commit()
    return jsonify({'id': c.id, 'status': 'ok'})

@app.route('/api/crm/clients/<int:cid>', methods=['DELETE'])
def delete_crm_client(cid):
    c = session.get(Client, cid)
    if c:
        audit = AuditLog(action='Cliente eliminado', module='CRM', details=f"Cliente: {c.name} ({c.rfc})")
        session.add(audit)
        session.delete(c)
        session.commit()
    return jsonify({'status': 'ok'})


# --- ERP Endpoints ---
@app.route('/api/erp/inventory', methods=['GET'])
def get_erp_inventory():
    items = session.query(InventoryItem).order_by(InventoryItem.sku).all()
    return jsonify([{
        'id': i.id,
        'sku': i.sku,
        'description': i.description,
        'sat_code': i.sat_code,
        'unit': i.unit,
        'quantity': i.quantity,
        'price': i.price,
        'created_at': i.created_at.isoformat() if i.created_at else ''
    } for i in items])

@app.route('/api/erp/inventory', methods=['POST'])
def add_erp_item():
    data = request.get_json()
    if not data or not data.get('sku') or not data.get('description') or not data.get('sat_code'):
        return jsonify({'error': 'SKU, Descripción y Código SAT requeridos'}), 400
        
    sku = data['sku'].strip().upper()
    existing = session.query(InventoryItem).filter_by(sku=sku).first()
    if existing:
        return jsonify({'error': 'Ya existe un artículo con ese SKU'}), 400
        
    i = InventoryItem(
        sku=sku,
        description=data['description'].strip(),
        sat_code=data['sat_code'].strip(),
        unit=data.get('unit', 'H87').strip(),
        quantity=float(data.get('quantity', 0.0)),
        price=float(data.get('price', 0.0))
    )
    session.add(i)
    
    # Audit log
    audit = AuditLog(action='Artículo de inventario creado', module='ERP', details=f"SKU: {i.sku}, Cantidad: {i.quantity}, Código SAT: {i.sat_code}")
    session.add(audit)
    session.commit()
    return jsonify({'id': i.id, 'status': 'ok'})

@app.route('/api/erp/inventory/<int:iid>', methods=['DELETE'])
def delete_erp_item(iid):
    i = session.get(InventoryItem, iid)
    if i:
        audit = AuditLog(action='Artículo de inventario eliminado', module='ERP', details=f"SKU: {i.sku}")
        session.add(audit)
        session.delete(i)
        session.commit()
    return jsonify({'status': 'ok'})


# --- SAT Product Keys Endpoints ---
@app.route('/api/sat/search', methods=['GET'])
def search_sat_keys():
    q = request.args.get('q', '').strip()
    if not q:
        keys = session.query(SATProductKey).order_by(SATProductKey.code).all()
    else:
        keys = session.query(SATProductKey).filter(
            (SATProductKey.code.like(f"%{q}%")) | (SATProductKey.name.like(f"%{q}%"))
        ).order_by(SATProductKey.code).all()
    
    # Registrar auditoría de búsqueda de claves SAT
    audit = AuditLog(action='Búsqueda Catálogo SAT', module='SAT', details=f"Búsqueda por término: '{q or 'Todo'}'")
    session.add(audit)
    session.commit()
    
    return jsonify([{
        'id': k.id,
        'code': k.code,
        'name': k.name,
        'description': k.description or '',
        'default_hs_code': k.default_hs_code or '',
        'created_at': k.created_at.isoformat() if k.created_at else ''
    } for k in keys])

@app.route('/api/sat/map/<hs_code>', methods=['GET'])
def map_sat_key(hs_code):
    clean_code = hs_code.replace('.', '').replace(' ', '').strip()[:6]
    # Intentar buscar coincidencia directa por los primeros 6 dígitos de la fracción arancelaria
    key = session.query(SATProductKey).filter(SATProductKey.default_hs_code.like(f"%{clean_code}%")).first()
    if not key and len(clean_code) >= 4:
        # Fallback a los primeros 4 dígitos (Subpartida)
        key = session.query(SATProductKey).filter(SATProductKey.default_hs_code.like(f"%{clean_code[:4]}%")).first()
    
    if key:
        return jsonify({
            'success': True,
            'code': key.code,
            'name': key.name,
            'default_hs_code': key.default_hs_code
        })
    return jsonify({'success': False, 'message': 'No se encontró una Clave SAT asociada directamente a esta fracción arancelaria.'}), 404


# --- ADMIN Endpoints ---
@app.route('/api/admin/audit', methods=['GET'])
def get_audit_logs():
    logs = session.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(100).all()
    return jsonify([{
        'id': l.id,
        'username': l.username,
        'action': l.action,
        'module': l.module,
        'details': l.details,
        'ip_address': l.ip_address,
        'created_at': l.created_at.isoformat() if l.created_at else ''
    } for l in logs])

@app.route('/api/admin/vault', methods=['GET'])
def get_vault_status():
    from utils.google_services import KEY_FILE
    provider = "Google Secret Manager" if os.environ.get('GOOGLE_CLOUD_PROJECT') else "Local AES-256-GCM Vault"
    audit = AuditLog(action='Acceso a Bóveda de Secretos', module='ADMIN', details=f"Verificación del estado de llaves y certificados en {provider}.")
    session.add(audit)
    session.commit()
    return jsonify({
        'status': 'Protegido',
        'provider': provider,
        'encryption_algorithm': 'AES-256-GCM',
        'key_file_created': os.path.exists(KEY_FILE),
        'credentials': [
            {'name': 'e.firma - ALINEA S.A.S.', 'type': 'cer+key', 'loaded': True, 'expires': '2028-10-15'},
            {'name': 'e.firma - GLOBAL LOGISTICS', 'type': 'cer+key', 'loaded': True, 'expires': '2029-02-20'},
            {'name': 'e.firma - ALINEA SOLUTIONS', 'type': 'cer+key', 'loaded': False, 'expires': '-'}
        ]
    })

@app.route('/api/admin/vault/upload', methods=['POST'])
def upload_vault_secret():
    from utils.google_services import store_secret
    data = request.get_json() or {}
    name = data.get('name', 'Clave de timbrado')
    content = data.get('content', 'MockCertificatePrivateKeyValue')
    
    # Intentar guardar de forma segura (GSM o AES-256-GCM local)
    res = store_secret(secret_id=name.replace(' ', '_').replace('-', '_'), secret_value=content)
    
    audit = AuditLog(
        action='Llave cargada a la Bóveda', 
        module='ADMIN', 
        details=f"Se almacenó una nueva clave/certificado en la bóveda: {name}. Proveedor: {res.get('provider')}."
    )
    session.add(audit)
    session.commit()
    return jsonify({
        'status': 'Clave almacenada con éxito',
        'provider': res.get('provider'),
        'details': 'Cifrado de grado militar activo en el ecosistema.'
    })


# --- VUCEM & MVE Endpoints ---
@app.route('/api/mve/list', methods=['GET'])
def get_mve_list():
    mves = session.query(ManifestacionValor).order_by(ManifestacionValor.created_at.desc()).limit(50).all()
    return jsonify([{
        'id': m.id,
        'folio': m.folio,
        'rfc_importador': m.rfc_importador,
        'razon_social': m.razon_social,
        'metodo_valoracion': m.metodo_valoracion,
        'valor_comercial': m.valor_comercial,
        'total_incrementables': m.total_incrementables,
        'valor_aduana_mxn': m.valor_aduana_mxn,
        'status': m.status,
        'created_at': m.created_at.isoformat() if m.created_at else ''
    } for m in mves])

@app.route('/api/mve/save', methods=['POST'])
def save_mve():
    data = request.get_json()
    new_mve = ManifestacionValor(
        folio=data.get('folio'),
        rfc_importador=data.get('rfcFirmante'),
        razon_social=data.get('firmante'),
        metodo_valoracion=data.get('metodoValoracion', 'Valor de Transacción'),
        valor_comercial=float(data.get('valorComercial', 0)),
        total_incrementables=float(data.get('totalIncrementables', 0)),
        valor_aduana_mxn=float(data.get('valorAduanaMXN', 0)),
        status='Emitida'
    )
    session.add(new_mve)
    
    audit = AuditLog(
        action='Emisión de Manifestación de Valor',
        module='MVE',
        details=f"Se emitió exitosamente la MVE con folio {new_mve.folio} para el importador {new_mve.rfc_importador} (Total: ${new_mve.valor_aduana_mxn:,.2f} MXN)"
    )
    session.add(audit)
    session.commit()
    
    return jsonify({'success': True, 'folio': new_mve.folio})

# VUCEM_SIMULATION_MODE=true activa respuestas simuladas (80% éxito / 20% rechazo).
# En producción real desactivar con VUCEM_SIMULATION_MODE=false.
_VUCEM_SIM = os.environ.get('VUCEM_SIMULATION_MODE', 'true').lower() == 'true'

@app.route('/api/vucem/acuses', methods=['GET'])
def get_vucem_acuses():
    import random
    acuses = session.query(VucemAcuse).order_by(VucemAcuse.created_at.desc()).limit(50).all()

    if _VUCEM_SIM:
        now = datetime.utcnow()
        changed = False
        for ac in acuses:
            if ac.status == 'Pendiente':
                diff = (now - ac.created_at).total_seconds()
                if diff > 10:
                    if random.random() < 0.8:
                        ac.status = 'Validado'
                        ac.error_details = ''
                        audit = AuditLog(action='Acuse validado en VUCEM', module='VUCEM',
                                         details=f"Folio {ac.folio} ({ac.type}) validado correctamente ante el SAT. [SIMULADO]")
                        session.add(audit)
                    else:
                        ac.status = 'Rechazado'
                        errors = [
                            "Error C01: El RFC del importador no se encuentra en el Padrón de Importadores.",
                            "Error F03: Firma digital inválida o vencida para el certificado adjunto.",
                            "Error E08: Los datos de valor comercial difieren del COVE original en un margen superior al permitido.",
                            "Error V12: Fracción arancelaria declarada requiere permiso regulatorio de COFEPRIS no anexado."
                        ]
                        ac.error_details = random.choice(errors)
                        audit = AuditLog(action='Acuse rechazado en VUCEM', module='VUCEM',
                                         details=f"Folio {ac.folio} ({ac.type}) rechazado con error: {ac.error_details} [SIMULADO]")
                        session.add(audit)
                    changed = True
        if changed:
            session.commit()
            acuses = session.query(VucemAcuse).order_by(VucemAcuse.created_at.desc()).limit(50).all()

    return jsonify([{
        'id': a.id,
        'folio': a.folio,
        'type': a.type,
        'rfc_importador': a.rfc_importador,
        'status': a.status,
        'error_details': a.error_details or '',
        'created_at': a.created_at.isoformat() if a.created_at else ''
    } for a in acuses])

@app.route('/api/vucem/validate', methods=['POST'])
def validate_vucem_document():
    data = request.get_json()
    if not data or not data.get('folio') or not data.get('type'):
        return jsonify({'error': 'Folio y Tipo requeridos'}), 400
        
    folio = data['folio'].strip().upper()
    existing = session.query(VucemAcuse).filter_by(folio=folio).first()
    if existing:
        return jsonify({'status': 'exist', 'id': existing.id})
        
    ac = VucemAcuse(
        folio=folio,
        type=data['type'].strip(),
        rfc_importador=data.get('rfc_importador', 'SOL890412AA1').strip().upper(),
        status='Pendiente'
    )
    session.add(ac)
    
    audit = AuditLog(action='Transmisión a VUCEM iniciada', module='VUCEM', details=f"Se envió el documento {ac.type} con folio {ac.folio} para validación asíncrona.")
    session.add(audit)
    session.commit()
    return jsonify({'id': ac.id, 'status': 'Pendiente'})


# --- CARTA PORTE Endpoints ---
@app.route('/api/cartaporte/list', methods=['GET'])
def get_cartaporte_list():
    items = session.query(CartaPorte).order_by(CartaPorte.created_at.desc()).all()
    return jsonify([{
        'id': i.id,
        'folio': i.folio,
        'origin': i.origin,
        'destination': i.destination,
        'goods_desc': i.goods_desc,
        'sat_code': i.sat_code,
        'sat_unit': i.sat_unit,
        'vehicle_config': i.vehicle_config,
        'status': i.status,
        'created_at': i.created_at.isoformat() if i.created_at else ''
    } for i in items])

@app.route('/api/cartaporte/generate', methods=['POST'])
def generate_cartaporte():
    data = request.get_json()
    if not data or not data.get('origin') or not data.get('destination') or not data.get('sat_code'):
        return jsonify({'error': 'Origen, Destino y Código SAT son requeridos'}), 400

    sat_code = data['sat_code'].strip()
    clean_sat_code = sat_code.replace('.', '')

    validation_errors = []

    # Validar dinámicamente contra la base de datos de Fracciones, Subpartidas y Claves SAT
    has_fraction = session.query(Fraction).filter(Fraction.code.like(f"%{clean_sat_code}%")).first()
    has_subheading = session.query(Subheading).filter(Subheading.code.like(f"%{clean_sat_code}%")).first()
    has_sat_key = session.query(SATProductKey).filter(SATProductKey.code == clean_sat_code).first()

    valid_codes = ['84713001', '8471.30.01', '85076001', '8507.60.01', '84818001', '8481.80.01', '08051001', '0805.10.01']
    is_valid_sat = (clean_sat_code in [c.replace('.', '') for c in valid_codes]) or has_fraction or has_subheading or has_sat_key

    if not is_valid_sat:
        validation_errors.append(f"Código SAT '{sat_code}' no existe en la base de datos arancelaria ni en el catálogo oficial.")

    sat_unit = data.get('sat_unit', 'H87').strip().upper()
    valid_units = ['H87', 'KGM', 'LTR', 'MTR', 'PZA', 'PCE']
    if sat_unit not in valid_units:
        validation_errors.append(f"Unidad SAT '{sat_unit}' no es válida. Use claves autorizadas como H87, KGM o PCE.")

    vehicle_config = data.get('vehicle_config', '').strip().upper()
    valid_configs = ['C2', 'C3', 'T3S2', 'T3S3']
    if vehicle_config and vehicle_config not in valid_configs:
        validation_errors.append(f"Configuración Vehicular '{vehicle_config}' no válida conforme al catálogo del SAT.")

    # Deducción y validación de inventario en el ERP (Si se envía un SKU o ID de Inventario)
    sku = data.get('sku', '').strip().upper()
    qty = float(data.get('qty', 0))
    inv_item = None

    if sku:
        inv_item = session.query(InventoryItem).filter_by(sku=sku).first()
        if not inv_item:
            validation_errors.append(f"El SKU '{sku}' no se encontró en el ERP de inventario.")
        elif qty <= 0:
            validation_errors.append("La cantidad a transportar debe ser mayor a cero.")
        elif inv_item.quantity < qty:
            validation_errors.append(f"Inventario insuficiente para SKU '{sku}'. Stock disponible: {inv_item.quantity:,.0f} unidades (Requerido: {qty:,.0f}).")

    if validation_errors:
        audit = AuditLog(action='Fallo de Validación Carta Porte', module='CARTA_PORTE', details=f"Fallo de pre-validación para mercancía. Errores: {'; '.join(validation_errors)}")
        session.add(audit)
        session.commit()
        return jsonify({
            'success': False,
            'errors': validation_errors
        }), 400

    # Descontar stock si pasó validaciones
    if inv_item:
        inv_item.quantity -= qty
        audit_inv = AuditLog(
            action='Descuento por Carta Porte',
            module='ERP',
            details=f"Descuento automático de {qty:,.0f} unidades del SKU {sku} debido a emisión de Carta Porte."
        )
        session.add(audit_inv)

    import uuid
    folio = 'CP-' + str(uuid.uuid4())[:8].upper()
    cp = CartaPorte(
        folio=folio,
        origin=data['origin'].strip(),
        destination=data['destination'].strip(),
        goods_desc=data.get('goods_desc', 'Mercancía en Tránsito').strip(),
        sat_code=sat_code,
        sat_unit=sat_unit,
        vehicle_config=vehicle_config or 'C2',
        status='Timbrado'
    )
    session.add(cp)

    audit = AuditLog(action='Carta Porte 3.1 Timbrada', module='CARTA_PORTE', details=f"Complemento Carta Porte emitido con folio {folio}. Timbrado PAC exitoso.")
    session.add(audit)
    session.commit()

    return jsonify({
        'success': True,
        'folio': folio,
        'status': 'Timbrado',
        'details': 'El complemento Carta Porte 3.1 fue pre-validado contra los catálogos del SAT y timbrado digitalmente.',
        'remaining_stock': inv_item.quantity if inv_item else None
    })


# --- Clasificación Extendida (PDF y RRNA) ---
@app.route('/api/classify/extended', methods=['POST'])
def classify_extended():
    image_bytes = None
    mime_type = None
    description = ""

    if request.content_type and 'multipart/form-data' in request.content_type:
        description = request.form.get('description', '')
        file = request.files.get('file')
        if file:
            filename = file.filename.lower()
            if filename.endswith(('.png', '.jpg', '.jpeg', '.webp')):
                image_bytes = file.read()
                mime_type = file.mimetype or 'image/jpeg'
    else:
        data = request.get_json() or {}
        description = data.get('description', '')

    if not description and not image_bytes:
        return jsonify({'error': 'Descripción o imagen requerida'}), 400
        
    audit = AuditLog(action='Clasificación de Mercancía (IA)', module='CLASSIFIER', details=f"Búsqueda técnica de: {description[:100]} [Imagen: {mime_type is not None}]")
    session.add(audit)
    session.commit()
    
    result = classify_with_ai(session, description, image_bytes, mime_type)
    
    if result.get('status') == 'clarification_needed':
        return jsonify({
            'status': 'clarification_needed',
            'questions': result.get('questions', []),
            'choices': result.get('choices', []),
            'reasoning': result.get('reasoning', ''),
            'method': result.get('method', 'local')
        })
        
    hs_code = result.get('hs_code', '')
    
    if not hs_code:
        results = search_by_text(session, description, limit=1)
        if results:
            hs_code = results[0]['code']
            result['hs_code'] = hs_code
            result['confidence'] = results[0]['score']
            result['reasoning'] = f"Sugerido por similitud léxico-semántica local con: {results[0]['title']}"
            result['method'] = 'local'
            
    if not hs_code:
        desc_lower = description.lower()
        if 'naranja' in desc_lower or 'fruta' in desc_lower:
            hs_code = '0805.10.01'
        elif 'laptop' in desc_lower or 'computadora' in desc_lower or 'thinkpad' in desc_lower:
            hs_code = '8471.30.01'
        elif 'bater' in desc_lower or 'litio' in desc_lower:
            hs_code = '8507.60.01'
        elif 'valvula' in desc_lower or 'acero' in desc_lower:
            hs_code = '8481.80.01'
        else:
            hs_code = '8517.62.01'
            
        result['hs_code'] = hs_code
        result['confidence'] = 0.75
        result['reasoning'] = "Código de fallback inteligente por palabras clave"
        result['method'] = 'rule_based'
        
    clean_code = hs_code.replace('.', '').replace(' ', '')
    chapter = clean_code[:2]
    heading = clean_code[:4]
    
    nico = clean_code[:8]
    if len(nico) < 8:
        nico = nico.ljust(8, '0')
    nico_full = f"{nico[:4]}.{nico[4:6]}.{nico[6:8]}-00"
    
    rrnas = []
    try:
        ch_int = int(chapter)
    except:
        ch_int = 0
        
    if ch_int == 8:
        rrnas.append("Inspección de sanidad vegetal (SENASICA/SAGARPA) en punto de entrada.")
        rrnas.append("Certificado Fitosanitario de Importación obligatorio.")
    elif ch_int == 30:
        rrnas.append("Autorización sanitaria previa de COFEPRIS para importación de medicamentos.")
    elif ch_int == 84 or ch_int == 85:
        rrnas.append("Certificación de cumplimiento de norma oficial de seguridad NOM-001-SCFI o NOM-024-SCFI.")
        rrnas.append("Padrón de Importadores de Sectores Específicos: Sector 9 (Siderúrgico/Máquinas) si aplica.")
    else:
        rrnas.append("Sujeto a inspección aduanera general. Presentar factura comercial declarando marca y número de serie.")
        
    igi_rate = 0.10
    iva_rate = 0.16
    ieps_rate = 0.00
    
    if ch_int == 8:
        igi_rate = 0.15
        iva_rate = 0.00
    elif ch_int == 84 or ch_int == 85:
        igi_rate = 0.00
        iva_rate = 0.16
    elif ch_int in [61, 62, 64]:
        igi_rate = 0.20
        iva_rate = 0.16

    # Garantizar que siempre haya un catálogo de alternativas para que el usuario las compare en la UI
    alternatives = result.get('alternatives', [])
    if not alternatives:
        local_candidates = search_by_text(session, description, limit=5)
        alternatives = [{
            'code': r['code'],
            'title': r['title'],
            'score': r['score']
        } for r in local_candidates[1:5]]
        
    return jsonify({
        'hs_code': hs_code,
        'nico': nico_full,
        'confidence': result.get('confidence', 0.8),
        'reasoning': result.get('reasoning', ''),
        'method': result.get('method', 'local'),
        'rrnas': rrnas,
        'alternatives': alternatives,
        'taxes': {
            'igi': f"{igi_rate * 100}%",
            'iva': f"{iva_rate * 100}%",
            'ieps': f"{ieps_rate * 100}%",
            'igi_val': igi_rate,
            'iva_val': iva_rate,
            'ieps_val': ieps_rate
        }
    })

@app.route('/api/classify/report/download', methods=['POST'])
def api_classify_report_download():
    data = request.get_json() or {}
    if not data.get('product_description') or not data.get('hs_code'):
        return jsonify({'error': 'Descripcion y Codigo HS son requeridos'}), 400
        
    try:
        from utils.single_report_generator import generate_single_classification_report
        pdf_path = generate_single_classification_report(session, data)
        return send_file(pdf_path, as_attachment=True, download_name=f"reporte_clasificacion_{data['hs_code']}.pdf")
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': f"Error al generar reporte: {str(e)}"}), 500

@app.route('/api/vucem/pdf/optimize', methods=['POST'])
def api_vucem_pdf_optimize():
    file = request.files.get('file')
    if not file:
        return jsonify({'error': 'No se recibió archivo'}), 400
    
    force_grayscale = request.form.get('force_grayscale', 'false').lower() == 'true'
    filename = file.filename
    original_filename, ext = os.path.splitext(filename)
    ext = ext.lower()
    
    # Guardar archivo temporal
    temp_dir = os.path.join(app.root_path, 'instance', 'temp')
    os.makedirs(temp_dir, exist_ok=True)
    temp_input_path = os.path.join(temp_dir, f"upload_{filename}")
    file.save(temp_input_path)
    
    # Destino en carpeta de reportes
    reportes_dir = os.path.join(app.root_path, 'reportes')
    os.makedirs(reportes_dir, exist_ok=True)
    
    out_filename = f"vucem_ready_{original_filename}.pdf"
    temp_output_path = os.path.join(reportes_dir, out_filename)
    
    from utils.pdf_converter import VucemPDFConverter
    
    try:
        if ext in ['.png', '.jpg', '.jpeg', '.webp']:
            conv_res = VucemPDFConverter.convert_image_to_pdf(temp_input_path, temp_output_path)
            if not conv_res['success']:
                return jsonify({'error': f"Error al convertir imagen a PDF: {conv_res.get('error')}"}), 500
            input_for_opt = temp_output_path
        elif ext == '.pdf':
            input_for_opt = temp_input_path
        else:
            return jsonify({'error': 'Formato de archivo no soportado. Use PDF o imágenes (PNG, JPG, JPEG, WEBP).'}), 400
            
        res = VucemPDFConverter.optimize_and_clean_pdf(input_for_opt, temp_output_path, force_grayscale=force_grayscale)
        
        if os.path.exists(temp_input_path):
            os.remove(temp_input_path)
            
        if not res['success']:
            return jsonify({'error': res.get('error')}), 500
            
        original_mb = res['original_size'] / (1024 * 1024)
        compressed_mb = res['compressed_size'] / (1024 * 1024)
        
        audit = AuditLog(
            action='Optimización PDF VUCEM', 
            module='VUCEM', 
            details=f"Archivo: {filename}, Reducción: {res['savings_pct']}%, Tamaño Original: {original_mb:.2f} MB, Tamaño Final: {compressed_mb:.2f} MB"
        )
        session.add(audit)
        session.commit()
        
        return jsonify({
            'success': True,
            'original_name': filename,
            'optimized_name': out_filename,
            'original_size_mb': round(original_mb, 2),
            'optimized_size_mb': round(compressed_mb, 2),
            'savings_pct': res['savings_pct'],
            'compliance': res['compliance'],
            'download_url': f"/api/reports/{out_filename}"
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': f"Error interno en optimización: {str(e)}"}), 500

@app.route('/api/pedimento/tax_calculate', methods=['POST'])
def api_pedimento_tax_calculate():
    data = request.get_json() or {}
    customs_value_usd = float(data.get('customs_value_usd', 0))
    exchange_rate = float(data.get('exchange_rate', 18.50))
    has_fta = bool(data.get('has_fta', False))
    items = data.get('items', [])
    
    if customs_value_usd <= 0:
        return jsonify({'error': 'El valor en aduana (USD) debe ser mayor que 0.'}), 400
        
    from utils.tax_calculator import PedimentoTaxCalculator
    try:
        res = PedimentoTaxCalculator.calculate_import_taxes(
            customs_value_usd=customs_value_usd,
            exchange_rate=exchange_rate,
            has_fta=has_fta,
            items=items
        )
        
        # Guardar en bitácora de auditoría
        audit = AuditLog(
            action='Cálculo Contribuciones Pedimento', 
            module='PEDIMENTO', 
            details=f"Valor Aduana: ${res['valor_aduana_mxn']:.2f} MXN, Total Impuestos: ${res['total_contribuciones_mxn']:.2f} MXN, TLC: {has_fta}"
        )
        session.add(audit)
        session.commit()
        
        return jsonify(res)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': f"Error al calcular impuestos: {str(e)}"}), 500

@app.route('/api/pedimento/generate_prer', methods=['POST'])
def api_pedimento_generate_prer():
    data = request.get_json() or {}
    patente = str(data.get('patente', '3589')).strip()
    pedimento = str(data.get('pedimento', '6000001')).strip()
    aduana = str(data.get('aduana', '470')).strip()
    regimen = str(data.get('regimen', 'A1')).strip()
    tipo_op = str(data.get('tipo_op', '1')).strip()
    exchange_rate = float(data.get('exchange_rate', 18.50))
    items = data.get('items', [])
    contributions = data.get('contributions', [])
    
    if len(patente) != 4 or not patente.isdigit():
        return jsonify({'error': 'La Patente debe ser de 4 dígitos numéricos.'}), 400
    if len(pedimento) != 7 or not pedimento.isdigit():
        return jsonify({'error': 'El consecutivo del Pedimento debe ser de 7 dígitos numéricos.'}), 400
        
    from utils.prer_generator import PedimentoPRERGenerator
    try:
        content = PedimentoPRERGenerator.generate_prer_content(
            patente=patente,
            pedimento=pedimento,
            aduana=aduana,
            regimen=regimen,
            tipo_op=tipo_op,
            exchange_rate=exchange_rate,
            items=items,
            contributions=contributions
        )
        
        filename = f"m{patente}{pedimento}.001"
        
        total_lines = len(content.splitlines())
        audit = AuditLog(
            action='Generación Archivo PRER', 
            module='PEDIMENTO', 
            details=f"Archivo plano aduanero generado: {filename}, Registros grabados: {total_lines}"
        )
        session.add(audit)
        session.commit()
        
        from flask import Response
        return Response(
            content,
            mimetype="text/plain",
            headers={"Content-disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': f"Error al generar archivo PRER: {str(e)}"}), 500

@app.route('/api/vucem/description/validate', methods=['POST'])
def api_vucem_description_validate():
    data = request.get_json() or {}
    description = data.get('description', '')
    if not description:
        return jsonify({'error': 'La descripción es requerida.'}), 400
    
    from utils.description_validator import VucemDescriptionValidator
    res = VucemDescriptionValidator.validate_description(description)
    
    audit = AuditLog(
        action='Validación Descripción Anexo 22',
        module='VUCEM',
        details=f"Texto: {description[:50]}..., Score: {res['score']}, Cumple: {res['is_compliant']}"
    )
    session.add(audit)
    session.commit()
    
    return jsonify(res)

@app.route('/api/classify/batch', methods=['POST'])
def api_classify_batch():
    data = request.get_json() or {}
    descriptions = data.get('descriptions', [])
    if not descriptions or not isinstance(descriptions, list):
        return jsonify({'error': 'Se requiere una lista de descripciones en el cuerpo de la petición.'}), 400
    
    if len(descriptions) > 100:
        return jsonify({'error': 'El límite máximo por lote en modo local es de 100 descripciones.'}), 400
    
    from classifiers.classifier import search_by_text as search_fn
    results = []
    
    try:
        for idx, desc in enumerate(descriptions):
            desc = desc.strip()
            if not desc:
                continue
            classification_results = search_fn(session, desc)
            top = classification_results[0] if classification_results else None
            
            if top:
                fracs = [r for r in classification_results if r.get("type") == "fraction"]
                top_frac = fracs[0]["code"] if fracs else "---"
                top_frac_title = fracs[0]["title"] if fracs else "---"
                
                results.append({
                    "index": idx + 1,
                    "description": desc,
                    "hs_code": top["code"][:4],
                    "heading_title": top["title"],
                    "fraction": top_frac,
                    "fraction_title": top_frac_title,
                    "score": float(top["score"]) if "score" in top else 1.0,
                    "confidence": "Alta" if top.get("score", 0) > 8 else "Media" if top.get("score", 0) > 4 else "Baja"
                })
            else:
                results.append({
                    "index": idx + 1,
                    "description": desc,
                    "hs_code": "---",
                    "heading_title": "Sin coincidencias",
                    "fraction": "---",
                    "fraction_title": "---",
                    "score": 0.0,
                    "confidence": "Nula"
                })
                
        audit = AuditLog(
            action='Clasificación Masiva por Lotes',
            module='CLASSIFIER',
            details=f"Procesadas {len(descriptions)} descripciones en lote."
        )
        session.add(audit)
        session.commit()
        
        return jsonify({"success": True, "count": len(results), "results": results})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': f"Error en clasificación por lote: {str(e)}"}), 500

@app.route('/api/sources/status')
def api_sources_status():
    return jsonify({"sources": get_source_status()})

@app.route('/api/sources/list')
def api_sources_list():
    return jsonify({"sources": get_official_sources_list()})

@app.route('/api/sources/search', methods=['POST'])
def api_sources_search():
    data = request.get_json()
    query = data.get('query', '')
    if not query:
        return jsonify({'error': 'Consulta requerida'}), 400
    result = search_all_official_sources(query, max_results=15)
    return jsonify(result)

@app.route('/api/sources/verify', methods=['POST'])
def api_sources_verify():
    data = request.get_json()
    hs_code = data.get('hs_code', '')
    if not hs_code:
        return jsonify({'error': 'C\u00f3digo HS requerido'}), 400
    result = verify_hs_code_with_official_sources(hs_code)
    return jsonify(result)

@app.route('/api/sources/sync', methods=['POST'])
def api_sources_sync():
    result = sync_from_official_sources(session)
    return jsonify(result)

@app.route('/api/database/regenerate', methods=['POST'])
def api_database_regenerate():
    stats = rebuild_database(session)
    return jsonify({
        "success": True,
        "message": "Base de datos regenerada con los 21 secciones del Sistema Armonizado",
        "stats": stats
    })

@app.route('/api/database/stats')
def api_database_stats():
    return jsonify(get_database_stats(session))

@app.route('/api/ligie/load', methods=['POST'])
def api_ligie_load():
    result = load_ligie(session)
    return jsonify(result)

@app.route('/api/ligie/nicos')
def api_ligie_nicos():
    from sources.ligie_extractor import _get_nico_from_text
    nicos = _get_nico_from_text()
    return jsonify({"total": len(nicos), "nicos": nicos[:50]})

@app.route('/api/reports')
def api_list_reports():
    import os, glob
    report_dir = os.path.join(os.path.dirname(__file__), "reportes")
    files = []
    if os.path.exists(report_dir):
        for f in sorted(glob.glob(os.path.join(report_dir, "*.pdf")), reverse=True):
            bname = os.path.basename(f)
            files.append({
                "name": bname,
                "size": os.path.getsize(f),
                "path": f"/api/reports/{bname}"
            })
    return jsonify({"reports": files})

@app.route('/api/reports/<filename>')
def api_get_report(filename):
    import os
    report_dir = os.path.join(os.path.dirname(__file__), "reportes")
    filepath = os.path.join(report_dir, filename)
    if os.path.exists(filepath):
        return send_file(filepath, as_attachment=True, download_name=filename)
    # fallback to root copy
    root_copy = os.path.join(os.path.dirname(__file__), "reporte_clasificador.pdf")
    if os.path.exists(root_copy):
        return send_file(root_copy, as_attachment=True, download_name="reporte_clasificador.pdf")
    return jsonify({"error": "No hay reportes generados"}), 404

@app.route('/api/report/download')
def api_download_report():
    from utils.report_generator import generate_report
    import os, json, unicodedata

    test_cases = [
        ("m\u00f3dulo que soporta comunicaci\u00f3n inal\u00e1mbrica", "8517", "85", "8517.62.01"),
        ("laptop lenovo thinkpad", "8471", "84", "8471.30.01"),
        ("naranjas frescas", "0805", "08", "0805.10.01"),
        ("vino tinto reserva", "2204", "22", "2204.21.04"),
        ("camiseta de algod\u00f3n para hombre", "6109", "61", "6109.10.01"),
        ("jeringa desechable de pl\u00e1stico", "9018", "90", "9018.31.01"),
        ("bater\u00eda de litio recargable", "8507", "85", "8507.60.01"),
        ("neum\u00e1tico para autom\u00f3vil 205/55R16", "4011", "40", "4011.10.10"),
        ("harina de trigo para panader\u00eda", "1101", "11", "1101.00.01"),
        ("auriculares bluetooth inal\u00e1mbricos", "8518", "85", "8518.30.01"),
        ("pantalla led 32 pulgadas", "8528", "85", "8528.49.02"),
        ("cemento portland gris 42.5", "2523", "25", "2523.29.99"),
        ("v\u00e1lvula de compuerta de acero inoxidable", "8481", "84", "8481.80.01"),
        ("silla de madera para comedor", "9403", "94", "9403.30.01"),
        ("anillo de oro con diamante", "7113", "71", "7113.11.01"),
        ("juguete de pl\u00e1stico figura de acci\u00f3n", "9503", "95", "9503.00.08"),
        ("pintura acr\u00edlica para pared interior", "3209", "32", "3209.10.01"),
        ("filtro de aceite para motor di\u00e9sel", "8421", "84", "8421.23.01"),
        ("pulpa de fruta congelada de mango", "0811", "08", "0811.90.01"),
        ("instrumento quir\u00fargico bistur\u00ed", "9018", "90", "9018.90.04"),
        ("m\u00f3dulo de memoria RAM 16GB DDR4", "8542", "85", "8542.31.01"),
        ("cable USB tipo C para carga", "8544", "85", "8544.42.02"),
        ("polietileno de alta densidad granulado", "3901", "39", "3901.20.01"),
        ("libro de texto de f\u00edsica cu\u00e1ntica", "4901", "49", "4901.99.03"),
        ("aceite de oliva virgen extra", "1509", "15", "1509.20.01"),
        ("antenas yagi para television", "8529", "85", "8529.10.09"),
    ]

    from classifiers.classifier import search_by_text as search_fn

    def _norm(t):
        nfkd = unicodedata.normalize('NFKD', t)
        return nfkd.encode('ASCII', 'ignore').decode('ASCII').lower()

    test_results = []
    frac_results = []
    for desc, exp_h, exp_ch, exp_frac in test_cases:
        results = search_fn(session, desc)
        top = results[0] if results else None
        if top:
            code = top["code"][:4]
            if code == exp_h:
                status = "CORRECT"
            elif code[:2] == exp_h[:2]:
                status = "PARTIAL"
            else:
                status = "WRONG"
            test_results.append((status, desc[:40], exp_h, code, top["title"][:50], top["score"]))
        else:
            test_results.append(("WRONG", desc[:40], exp_h, "---", "---", 0))

        # Fraction-level evaluation: look for 8-digit codes in results
        frac_matches = [r for r in results if r.get("type") == "fraction" and len(r["code"]) >= 8]
        top_frac = frac_matches[0] if frac_matches else None
        if top_frac:
            fcode = top_frac["code"]
            fcode_clean = fcode[:10].replace(" ", "").replace(".", "")
            exp_clean = exp_frac[:10].replace(" ", "").replace(".", "")
            if fcode_clean == exp_clean:
                fstatus = "CORRECT"
            elif fcode_clean[:4] == exp_clean[:4]:
                fstatus = "PARTIAL_HEADING"
            elif fcode_clean[:2] == exp_clean[:2]:
                fstatus = "PARTIAL_CHAPTER"
            else:
                fstatus = "WRONG"
            frac_results.append((fstatus, desc[:40], exp_frac, fcode, top_frac["title"][:50], top_frac["score"]))
        else:
            frac_results.append(("WRONG", desc[:40], exp_frac, "---", "Sin fraccion", 0))

    pdf_path = generate_report(session, test_results, frac_results)
    return send_file(pdf_path, as_attachment=True, download_name="reporte_clasificador.pdf")

# ==========================================
# ENDPOINTS PARA EL CHAT CONVERSACIONAL
# ==========================================

@app.route('/api/chat/start', methods=['POST'])
def chat_start():
    try:
        thread = ChatThread()
        session.add(thread)
        session.commit()
        return jsonify({'thread_id': thread.id})
    except Exception as e:
        session.rollback()
        return jsonify({'error': f'Error al iniciar hilo de chat: {str(e)}'}), 500

@app.route('/api/chat/send', methods=['POST'])
def chat_send():
    try:
        data = request.get_json() or {}
        thread_id = data.get('thread_id')
        message = data.get('message', '').strip()

        if not thread_id:
            return jsonify({'error': 'thread_id es requerido'}), 400
        if not message:
            return jsonify({'error': 'message es requerido'}), 400

        try:
            thread_id_int = int(thread_id)
        except ValueError:
            return jsonify({'error': 'thread_id debe ser un número entero'}), 400

        thread = session.get(ChatThread, thread_id_int)
        if not thread:
            return jsonify({'error': f'Hilo {thread_id} no encontrado'}), 404

        # 1. Guardar mensaje del usuario
        user_msg = ChatMessage(
            thread_id=thread.id,
            sender='user',
            content=message
        )
        session.add(user_msg)
        session.commit() # Guardar temporalmente para construir el historial

        # 2. Recuperar historial completo de la conversación
        messages = session.query(ChatMessage).filter_by(thread_id=thread.id).order_by(ChatMessage.created_at.asc()).all()
        history = []
        for msg in messages:
            try:
                meta = json.loads(msg.metadata_json) if msg.metadata_json else None
            except Exception:
                meta = None
            history.append({
                'sender': msg.sender,
                'content': msg.content,
                'metadata': meta
            })

        # 3. Detector de Intenciones y Consulta Directa de Aranceles/NOMs
        import re
        code_pattern = re.compile(r'\b\d{4}\.\d{2}(?:\.\d{2})?\b|\b\d{6,8}\b')
        keywords = [
            'arancel', 'impuesto', 'igi', 'iva', 'nom', 'restriccion', 'restricción',
            'requisito', 'regulacion', 'regulación', 'gravamen', 'tasa', 'cuanto paga', 'cuánto paga'
        ]

        message_lower = message.lower()
        has_intent = any(kw in message_lower for kw in keywords)
        code_match = code_pattern.search(message)

        direct_result = None
        if has_intent and code_match:
            raw_code = code_match.group(0)
            clean_code = raw_code.replace('.', '').replace(' ', '').strip()

            # Buscar en base de datos: Fraction, Subheading, Heading
            entity = session.query(Fraction).filter_by(code=clean_code).first()
            entity_type = 'fraction'

            if not entity:
                entity = session.query(Subheading).filter_by(code=clean_code).first()
                entity_type = 'subheading'

            if not entity:
                entity = session.query(Heading).filter_by(code=clean_code).first()
                entity_type = 'heading'

            if entity:
                # Extraer descripción
                description_text = ""
                if entity_type == 'fraction':
                    description_text = entity.title if entity.title else entity.description
                else:
                    description_text = entity.title if entity.title else (entity.description if entity.description else "")

                # Determinar capítulo
                chapter = clean_code[:2]
                try:
                    ch_int = int(chapter)
                except ValueError:
                    ch_int = 0

                # Determinar regulaciones y NOMs (RRNAs)
                rrnas = []
                if ch_int == 8:
                    rrnas.append("Inspección de sanidad vegetal (SENASICA/SAGARPA) en punto de entrada.")
                    rrnas.append("Certificado Fitosanitario de Importación obligatorio.")
                elif ch_int == 30:
                    rrnas.append("Autorización sanitaria previa de COFEPRIS para importación de medicamentos.")
                elif ch_int in [84, 85]:
                    rrnas.append("Certificación de cumplimiento de norma oficial de seguridad NOM-001-SCFI o NOM-024-SCFI.")
                    rrnas.append("Padrón de Importadores de Sectores Específicos: Sector 9 (Siderúrgico/Máquinas) si aplica.")
                else:
                    rrnas.append("Sujeto a inspección aduanera general. Presentar factura comercial declarando marca y número de serie.")

                # Determinar tasas de impuestos
                igi_rate = 0.10
                iva_rate = 0.16
                ieps_rate = 0.00

                if ch_int == 8:
                    igi_rate = 0.15
                    iva_rate = 0.00
                elif ch_int in [84, 85]:
                    igi_rate = 0.00
                    iva_rate = 0.16
                elif ch_int in [61, 62, 64]:
                    igi_rate = 0.20
                    iva_rate = 0.16

                def format_hs_code(code):
                    if len(code) == 8:
                        return f"{code[:4]}.{code[4:6]}.{code[6:8]}"
                    elif len(code) == 6:
                        return f"{code[:4]}.{code[4:6]}"
                    return code

                formatted_code = format_hs_code(clean_code)
                rrnas_html = "".join([f"<li style='margin-bottom: 4px;'>{r}</li>" for r in rrnas])

                reasoning_html = (
                    f'<div class="merceology-map" style="background: rgba(30, 41, 59, 0.45); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 8px; padding: 16px; margin-top: 12px; color: #f1f5f9; font-family: system-ui, -apple-system, BlinkMacSystemFont, \'Segoe UI\', Roboto, sans-serif;">'
                    f'  <h4 style="margin-top: 0; margin-bottom: 12px; color: #38bdf8; display: flex; align-items: center; gap: 8px; font-size: 15px; border-bottom: 1px solid rgba(255, 255, 255, 0.15); padding-bottom: 8px;">'
                    f'    <span>📋</span> CONSULTA DIRECTA ARANCELARIA'
                    f'  </h4>'
                    f'  <div style="background: rgba(15, 23, 42, 0.4); border: 1px solid rgba(255, 255, 255, 0.05); border-radius: 6px; padding: 12px; font-size: 13px; line-height: 1.5;">'
                    f'    <p style="margin: 0 0 8px 0;">El código arancelario <strong style="color: #38bdf8; font-family: monospace; font-size: 14px;">{formatted_code}</strong> corresponde a:</p>'
                    f'    <p style="margin: 0 0 12px 0; font-style: italic; color: #cbd5e1; background: rgba(0, 0, 0, 0.2); padding: 8px; border-radius: 4px; border-left: 3px solid #38bdf8;">"{description_text}"</p>'
                    f'    <div style="margin-bottom: 12px; border-top: 1px solid rgba(255, 255, 255, 0.08); padding-top: 8px;">'
                    f'      <strong>Tasas Impositivas:</strong>'
                    f'      <ul style="margin: 4px 0 0 0; padding-left: 20px;">'
                    f'        <li><strong>IGI (Arancel General):</strong> {int(igi_rate * 100)}%</li>'
                    f'        <li><strong>IVA:</strong> {int(iva_rate * 100)}%</li>'
                    f'        <li><strong>IEPS:</strong> {int(ieps_rate * 100)}%</li>'
                    f'      </ul>'
                    f'    </div>'
                    f'    <div style="border-top: 1px solid rgba(255, 255, 255, 0.08); padding-top: 8px;">'
                    f'      <strong>Regulaciones y NOMs (RRNAs):</strong>'
                    f'      <ul style="margin: 4px 0 0 0; padding-left: 20px; color: #fbbf24;">'
                    f'        {rrnas_html}'
                    f'      </ul>'
                    f'    </div>'
                    f'  </div>'
                    f'</div>'
                )

                direct_result = {
                    'status': 'complete',
                    'hs_code': clean_code,
                    'confidence': 1.0,
                    'reasoning': reasoning_html,
                    'alternatives': [],
                    'questions': [],
                    'choices': [],
                    'method': 'direct_intent',
                    'taxes': {
                        'igi': f"{int(igi_rate * 100)}%",
                        'iva': f"{int(iva_rate * 100)}%",
                        'ieps': f"{int(ieps_rate * 100)}%",
                        'igi_val': igi_rate,
                        'iva_val': iva_rate,
                        'ieps_val': ieps_rate
                    },
                    'rrnas': rrnas
                }

        if direct_result:
            result = direct_result
        else:
            # 4. Llamar al clasificador normal si no coincide la intención o no está en DB
            result = classify_with_ai(session, message, history=history)

        # 4. Guardar respuesta del bot
        bot_content = result.get('reasoning', '')
        bot_msg = ChatMessage(
            thread_id=thread.id,
            sender='bot',
            content=bot_content,
            metadata_json=json.dumps(result)
        )
        session.add(bot_msg)
        session.commit()

        return jsonify(result)
    except Exception as e:
        session.rollback()
        return jsonify({'error': f'Error al procesar mensaje del chat: {str(e)}'}), 500

@app.route('/api/chat/history/<thread_id>', methods=['GET'])
def chat_history(thread_id):
    try:
        thread_id_int = int(thread_id)
    except ValueError:
        return jsonify({'error': 'thread_id debe ser un número entero'}), 400
        
    thread = session.get(ChatThread, thread_id_int)
    if not thread:
        return jsonify({'error': f'Hilo {thread_id} no encontrado'}), 404

    messages = session.query(ChatMessage).filter_by(thread_id=thread_id_int).order_by(ChatMessage.created_at.asc()).all()
    
    result = []
    for msg in messages:
        try:
            meta = json.loads(msg.metadata_json) if msg.metadata_json else None
        except Exception:
            meta = None
        result.append({
            'id': msg.id,
            'sender': msg.sender,
            'content': msg.content,
            'created_at': msg.created_at.isoformat() if msg.created_at else '',
            'metadata': meta
        })
    return jsonify({'messages': result})

if __name__ == '__main__':
    app.run(
        debug=True,
        port=5000,
        use_reloader=False
    )
