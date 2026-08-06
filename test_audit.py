import json
import sys
import os
from datetime import datetime, timedelta

# Asegurar que el directorio del proyecto esté en el PATH
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

from app import app, session
from database.models import AuditLog, Client, InventoryItem, VucemAcuse, CartaPorte, ManifestacionValor

def run_audit_tests():
    client = app.test_client()
    print("==================================================================")
    # 0. Limpieza previa de cualquier dato de prueba anterior para evitar conflictos de claves únicas
    session.query(Client).filter_by(rfc="TEST990101AA1").delete()
    session.query(InventoryItem).filter(InventoryItem.sku.in_(["SKU-TEST-AUDIT", "SKU-TEMP-CP"])).delete()
    session.query(VucemAcuse).filter_by(folio="VUCEM-TEST-001").delete()
    session.query(ManifestacionValor).filter_by(folio="MVE-TEST-001").delete()
    session.query(CartaPorte).filter(CartaPorte.goods_desc == "Mercancia de prueba de auditoria").delete()
    session.commit()

    print("Iniciando pruebas de integración del sistema de Auditoría (Local)")
    print("==================================================================")

    # --- Caso 1: Acceso a la Bóveda de Secretos (GET) ---
    print("\n[Test 1] Accediendo a la Bóveda de Secretos...")
    res = client.get('/api/admin/vault')
    assert res.status_code == 200, "Fallo al acceder a la boveda"
    
    # --- Caso 2: Carga de secretos a la Bóveda (POST) ---
    print("[Test 2] Cargando llave a la Bóveda...")
    res = client.post('/api/admin/vault/upload', json={
        "name": "e.firma - TEST CLIENT",
        "content": "MockPrivateKeyContentForTestingAuditLogsOnly"
    })
    assert res.status_code == 200, "Fallo al cargar llave a la bóveda"

    # --- Caso 3: Creación de Cliente en el CRM (POST) ---
    print("[Test 3] Creando cliente de prueba en CRM...")
    res = client.post('/api/crm/clients', json={
        "rfc": "TEST990101AA1",
        "name": "CLIENTE PRUEBA AUDITORIA",
        "patent": "9999",
        "agent": "Lic. Test Agent",
        "status": "Activo"
    })
    assert res.status_code == 200, "Fallo al crear cliente"

    # --- Caso 4: Eliminación de Cliente en el CRM (DELETE) ---
    print("[Test 4] Eliminando cliente creado en CRM...")
    # Obtener ID
    res = client.get('/api/crm/clients')
    clients = json.loads(res.data)
    target_client = next((c for c in clients if c["rfc"] == "TEST990101AA1"), None)
    assert target_client is not None, "Cliente no encontrado para eliminación"
    
    res = client.delete(f'/api/crm/clients/{target_client["id"]}')
    assert res.status_code == 200, "Fallo al eliminar cliente"

    # --- Caso 5: Creación de Artículo en el ERP (POST) ---
    print("[Test 5] Creando artículo de inventario en ERP...")
    res = client.post('/api/erp/inventory', json={
        "sku": "SKU-TEST-AUDIT",
        "description": "Articulo de prueba de auditoria",
        "sat_code": "8471.30.01",
        "unit": "H87",
        "quantity": 100.0,
        "price": 50.00
    })
    assert res.status_code == 200, "Fallo al crear artículo de inventario"

    # --- Caso 6: Eliminación de Artículo en el ERP (DELETE) ---
    print("[Test 6] Eliminando artículo de inventario en ERP...")
    res = client.get('/api/erp/inventory')
    items = json.loads(res.data)
    target_item = next((i for i in items if i["sku"] == "SKU-TEST-AUDIT"), None)
    assert target_item is not None, "Artículo no encontrado para eliminación"

    res = client.delete(f'/api/erp/inventory/{target_item["id"]}')
    assert res.status_code == 200, "Fallo al eliminar artículo"

    # --- Caso 7: Clasificación extendida con IA/Búsqueda (POST) ---
    print("[Test 7] Ejecutando clasificación extendida...")
    res = client.post('/api/classify/extended', json={
        "description": "Computadora portatil con pantalla led y procesador intel core i7"
    })
    assert res.status_code == 200, "Fallo en clasificación extendida"

    # --- Caso 8: Guardado de Manifestación de Valor (POST) ---
    print("[Test 8] Guardando Manifestación de Valor (MVE)...")
    res = client.post('/api/mve/save', json={
        "folio": "MVE-TEST-001",
        "rfcFirmante": "SOL890412AA1",
        "firmante": "ALINEA S.A.S.",
        "metodoValoracion": "Valor de Transaccion",
        "valorComercial": 1000.00,
        "totalIncrementables": 200.00,
        "valorAduanaMXN": 1200.00
    })
    assert res.status_code == 200, "Fallo al guardar MVE"

    # --- Caso 9: Fallo de Validación de Carta Porte (POST) ---
    print("[Test 9] Forzando fallo de validación en Carta Porte...")
    res = client.post('/api/cartaporte/generate', json={
        "origin": "Mexico DF",
        "destination": "Monterrey",
        "goods_desc": "Mercancia invalida",
        "sat_code": "CODIGO_INEXISTENTE_99999",
        "sat_unit": "XYZ",
        "vehicle_config": "CONFIG_INEXISTENTE"
    })
    assert res.status_code == 400, "Debería haber fallado con código 400"
    data = json.loads(res.data)
    print(f"        -> Fallo capturado con éxito: {data['errors']}")

    # --- Caso 10: Generación exitosa de Carta Porte y deducción de Stock (POST) ---
    print("[Test 10] Emitiendo Carta Porte válida con deducción de stock en ERP...")
    # Crear artículo temporal
    res = client.post('/api/erp/inventory', json={
        "sku": "SKU-TEMP-CP",
        "description": "Articulo para prueba de carta porte",
        "sat_code": "8471.30.01",
        "unit": "H87",
        "quantity": 50.0,
        "price": 1000.00
    })
    assert res.status_code == 200, "Fallo al crear artículo temporal en ERP"

    # Generar Carta Porte que consume 10 unidades
    res = client.post('/api/cartaporte/generate', json={
        "origin": "Ciudad de Mexico",
        "destination": "Guadalajara",
        "goods_desc": "Mercancia de prueba de auditoria",
        "sat_code": "8471.30.01",
        "sat_unit": "H87",
        "vehicle_config": "C2",
        "sku": "SKU-TEMP-CP",
        "qty": 10.0
    })
    assert res.status_code == 200, "Fallo al generar Carta Porte válida"
    cp_data = json.loads(res.data)
    print(f"        -> Carta Porte generada folio: {cp_data['folio']}, Stock restante: {cp_data['remaining_stock']}")
    assert cp_data['remaining_stock'] == 40.0, "El stock restante debería ser 40"

    # --- Caso 11: Inicio de Validación VUCEM e iteración de simulación asíncrona ---
    print("[Test 11] Enviando documento a VUCEM para validación asíncrona...")
    res = client.post('/api/vucem/validate', json={
        "folio": "VUCEM-TEST-001",
        "type": "COVE",
        "rfc_importador": "SOL890412AA1"
    })
    assert res.status_code == 200, "Fallo al iniciar VUCEM"
    
    # Simular paso del tiempo alterando directamente la base de datos (backdate >10 segundos)
    db_acuse = session.query(VucemAcuse).filter_by(folio="VUCEM-TEST-001").first()
    assert db_acuse is not None, "Acuse no guardado en base de datos"
    db_acuse.created_at = datetime.utcnow() - timedelta(seconds=15)
    session.commit()

    # Llamar a get_vucem_acuses para que el loop de simulación resuelva el acuse Pendiente -> Validado/Rechazado
    print("        -> Forzando resolución asíncrona mediante llamada al pool de acuses...")
    res = client.get('/api/vucem/acuses')
    assert res.status_code == 200, "Fallo al consultar acuses"
    acuses = json.loads(res.data)
    resolved_acuse = next((a for a in acuses if a["folio"] == "VUCEM-TEST-001"), None)
    assert resolved_acuse is not None, "Acuse de prueba no encontrado en lista"
    print(f"        -> Estado de validación VUCEM resuelto: {resolved_acuse['status']}")
    if resolved_acuse['status'] == 'Rechazado':
        print(f"           Detalle del error del SAT: {resolved_acuse['error_details']}")

    # --- Caso 12: Optimización de PDF para VUCEM (POST) ---
    print("[Test 12] Optimizando PDF para VUCEM...")
    pdf_path = os.path.join(PROJECT_ROOT, "reporte_fracciones.pdf")
    if os.path.exists(pdf_path):
        with open(pdf_path, 'rb') as f:
            res = client.post('/api/vucem/pdf/optimize', data={
                'file': (f, 'reporte_fracciones.pdf'),
                'force_grayscale': 'true'
            })
        print(f"        -> Status Code: {res.status_code}")
        print(f"        -> Response Data: {res.data.decode('utf-8', errors='ignore')}")
        assert res.status_code == 200, "Fallo al optimizar PDF para VUCEM"
        opt_data = json.loads(res.data)
        print(f"        -> PDF optimizado con éxito. Nombre: {opt_data['optimized_name']}, Reducción: {opt_data['savings_pct']}%")
        
        # Limpiar archivo generado en reportes
        generated_path = os.path.join(PROJECT_ROOT, "reportes", opt_data['optimized_name'])
        if os.path.exists(generated_path):
            os.remove(generated_path)
    else:
        print("        -> [SKIP] reporte_fracciones.pdf no encontrado")

    # --- Caso 13: Cálculo de Contribuciones Pedimento (POST) ---
    print("\n[Test 13] Ejecutando cálculo de contribuciones de importación...")
    res = client.post('/api/pedimento/tax_calculate', json={
        "customs_value_usd": 10000.00,
        "exchange_rate": 18.50,
        "has_fta": False,
        "items": [
            {
                "hs_code": "8471.30.01",
                "customs_value_item_usd": 6000.00,
                "description": "Laptop Lenovo ThinkPad"
            },
            {
                "hs_code": "2208.90.03",
                "customs_value_item_usd": 4000.00,
                "description": "Tequila 100% de Agave"
            }
        ]
    })
    assert res.status_code == 200, "Fallo al calcular contribuciones"
    tax_data = json.loads(res.data)
    print(f"        -> Total Contribuciones calculadas: ${tax_data['total_contribuciones_mxn']} MXN")
    assert tax_data['total_contribuciones_mxn'] > 0, "Las contribuciones deberían ser mayores que 0"

    # --- Caso 14: Generación de Archivo Plano PRER (POST) ---
    print("\n[Test 14] Generando archivo plano de prevalidación PRER (Anexo 22)...")
    res = client.post('/api/pedimento/generate_prer', json={
        "patente": "3589",
        "pedimento": "6000001",
        "aduana": "470",
        "regimen": "A1",
        "exchange_rate": 18.50,
        "items": [
            {
                "hs_code": "84713001",
                "value_usd": 6000.00,
                "customs_value_mxn": 111000.00
            },
            {
                "hs_code": "22089003",
                "value_usd": 4000.00,
                "customs_value_mxn": 74000.00
            }
        ],
        "contributions": [
            {"clave": 1, "concepto": "IGI", "fp": 0, "importe": 0.0},
            {"clave": 3, "concepto": "DTA", "fp": 0, "importe": 1480.0},
            {"clave": 15, "concepto": "PRV", "fp": 0, "importe": 310.0},
            {"clave": 50, "concepto": "IVA", "fp": 0, "importe": 29680.0},
            {"clave": 99, "concepto": "CNT", "fp": 0, "importe": 70.0}
        ]
    })
    assert res.status_code == 200, "Fallo al generar archivo plano PRER"
    prer_content = res.data.decode('utf-8')
    print("        -> Archivo plano generado con éxito. Vista previa de registros:")
    for line in prer_content.splitlines()[:5]:
        print(f"           {line}")
    assert "500|3589|" in prer_content, "Debería contener registro de encabezado 500"
    assert "801|3589|" in prer_content, "Debería contener registro de fin 801"

    # --- Caso 15: Validación de Descripciones Anexo 22 (POST) ---
    print("\n[Test 15] Evaluando descripciones con el Validador Anexo 22...")
    # Prueba 1: Descripción insuficiente
    res_bad = client.post('/api/vucem/description/validate', json={"description": "partes"})
    assert res_bad.status_code == 200, "Fallo al validar descripción mala"
    data_bad = json.loads(res_bad.data)
    print(f"        -> [Descripción Insuficiente] Cumple: {data_bad['is_compliant']}, Score: {data_bad['score']}")
    assert data_bad['is_compliant'] == False, "Debería marcarse como no-cumplimiento"
    assert len(data_bad['warnings']) > 0, "Debería reportar alertas"

    # Prueba 2: Descripción suficiente
    res_good = client.post('/api/vucem/description/validate', json={"description": "Computadora portatil con pantalla led y procesador intel core i7, Marca Lenovo, Modelo Thinkpad, Serie 98765A"})
    assert res_good.status_code == 200, "Fallo al validar descripción buena"
    data_good = json.loads(res_good.data)
    print(f"        -> [Descripción Suficiente] Cumple: {data_good['is_compliant']}, Score: {data_good['score']}")
    assert data_good['is_compliant'] == True, "Debería marcarse como cumplimiento"

    # --- Caso 16: Clasificación Masiva por Lotes (POST) ---
    print("\n[Test 16] Procesando lote masivo de mercancías (Multiclasificador)...")
    res_batch = client.post('/api/classify/batch', json={
        "descriptions": [
            "Laptops Lenovo Core i7 16GB",
            "Tequila añejo reposado 750ml",
            "Naranjas valencia frescas"
        ]
    })
    assert res_batch.status_code == 200, "Fallo en clasificación masiva"
    data_batch = json.loads(res_batch.data)
    print(f"        -> Lote procesado. Cantidad: {data_batch['count']}")
    assert data_batch['success'] == True, "Debería reportar éxito"
    assert data_batch['count'] == 3, "Debería reportar 3 resultados"

    # ==================================================================
    # VERIFICACIÓN FINAL DE LOGS EN LA TABLA DE AUDITORÍA
    # ==================================================================
    print("\n==================================================================")
    print("Verificando registros generados en la tabla AuditLog...")
    print("==================================================================")

    res = client.get('/api/admin/audit')
    assert res.status_code == 200, "Fallo al recuperar logs de auditoría"
    audit_logs = json.loads(res.data)

    # Imprimir últimos 15 logs para inspección visual
    print(f"Total de registros de auditoría recuperados: {len(audit_logs)}")
    print("\nÚltimos logs registrados (orden cronológico inverso):")
    
    # Filtrar por acciones realizadas en este test para evitar ruido histórico
    expected_actions = [
        "Acceso a Bóveda de Secretos",
        "Llave cargada a la Bóveda",
        "Cliente creado",
        "Cliente eliminado",
        "Artículo de inventario creado",
        "Artículo de inventario eliminado",
        "Clasificación de Mercancía (IA)",
        "Emisión de Manifestación de Valor",
        "Fallo de Validación Carta Porte",
        "Descuento por Carta Porte",
        "Carta Porte 3.1 Timbrada",
        "Transmisión a VUCEM iniciada",
        "Acuse validado en VUCEM",
        "Acuse rechazado en VUCEM",
        "Optimización PDF VUCEM",
        "Cálculo Contribuciones Pedimento",
        "Generación Archivo PRER",
        "Validación Descripción Anexo 22",
        "Clasificación Masiva por Lotes"
    ]

    count = 0
    for log in audit_logs:
        # Si la acción pertenece a la suite de tests
        if any(act in log["action"] for act in expected_actions) or "VUCEM" in log["action"]:
            count += 1
            print(f"[{log['created_at']}] [{log['module']}] Accion: {log['action']}")
            print(f"           Detalles: {log['details']}")
            print("-" * 66)

    # Limpieza final del artículo temporal y MVE
    session.query(InventoryItem).filter_by(sku="SKU-TEMP-CP").delete()
    session.query(VucemAcuse).filter_by(folio="VUCEM-TEST-001").delete()
    session.query(ManifestacionValor).filter_by(folio="MVE-TEST-001").delete()
    session.query(CartaPorte).filter(CartaPorte.goods_desc == "Mercancia de prueba de auditoria").delete()
    session.commit()

    print(f"\nPruebas completadas exitosamente. Se verificaron {count} eventos de auditoría en base de datos.")
    print("==================================================================")

if __name__ == "__main__":
    run_audit_tests()
