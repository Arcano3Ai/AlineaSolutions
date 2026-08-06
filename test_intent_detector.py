import json
from app import app, session
from database.models import ChatThread, ChatMessage, Fraction, Subheading, Heading

client = app.test_client()

def test_intent_detector():
    print("--- Iniciando pruebas del Detector de Intenciones ---")
    
    # 1. Crear un hilo de chat
    res = client.post('/api/chat/start')
    assert res.status_code == 200, "No se pudo iniciar el chat"
    thread_data = json.loads(res.data)
    thread_id = thread_data['thread_id']
    print(f"Hilo de chat creado con ID: {thread_id}")

    # Sembrar una fracción de prueba en la base de datos si no existe
    # para asegurar que la consulta directa funcione
    test_code = "85171201"
    existing_frac = session.query(Fraction).filter_by(code=test_code).first()
    if not existing_frac:
        sub = session.query(Subheading).filter_by(code="851712").first()
        if not sub:
            h = Heading(code="8517", title="Partida 8517", description="Partida 8517")
            session.add(h)
            session.flush()
            sub = Subheading(code="851712", title="Subpartida 851712", description="Subpartida 851712", heading_id=h.id)
            session.add(sub)
            session.flush()
        frac = Fraction(
            code=test_code,
            title="Teléfonos para redes celulares o de otras redes inalámbricas",
            description="Teléfonos para redes celulares o de otras redes inalámbricas | Contexto",
            subheading_id=sub.id
        )
        session.add(frac)
        session.commit()
        print(f"Fracción de prueba {test_code} sembrada en base de datos.")

    # Caso 1: Consulta directa de aranceles exitosa (intención + código válido)
    msg = "Cuál es el arancel e impuesto de la fracción 8517.12.01?"
    print(f"Enviando mensaje Caso 1: '{msg}'")
    res = client.post('/api/chat/send', json={
        'thread_id': thread_id,
        'message': msg
    })
    assert res.status_code == 200, f"Error en chat send: {res.data}"
    data = json.loads(res.data)
    print("Respuesta recibida:")
    print(json.dumps(data, indent=2))
    
    # Verificaciones
    assert data['status'] == 'complete', "Status debería ser 'complete'"
    assert data['hs_code'] == '85171201', "El código detectado debería ser '85171201'"
    assert data['method'] == 'direct_intent', "El método debería ser 'direct_intent'"
    assert 'Tasas Impositivas' in data['reasoning'], "El reasoning debería contener las tasas impositivas en HTML"
    assert data['taxes']['igi'] == '0%', "El IGI debería ser 0% (capítulo 85)"
    assert data['taxes']['iva'] == '16%', "El IVA debería ser 16%"
    print("Caso 1: PASADO\n")

    # Caso 2: Intención detectada pero código no existe en DB (cae a flujo normal/IA)
    msg = "Dime el arancel del código 9999.99.99"
    print(f"Enviando mensaje Caso 2: '{msg}'")
    res = client.post('/api/chat/send', json={
        'thread_id': thread_id,
        'message': msg
    })
    assert res.status_code == 200, f"Error en chat send: {res.data}"
    data = json.loads(res.data)
    # Debería usar el método local o gemini
    print(f"Método de resolución: {data.get('method')}")
    assert data.get('method') != 'direct_intent', "No debería usar 'direct_intent' porque 99999999 no existe en DB"
    print("Caso 2: PASADO\n")

    # Caso 3: Código presente pero sin intención clara (cae a flujo normal/IA)
    msg = "Tengo una importación de 85171201 para embarcar mañana"
    print(f"Enviando mensaje Caso 3: '{msg}'")
    res = client.post('/api/chat/send', json={
        'thread_id': thread_id,
        'message': msg
    })
    assert res.status_code == 200, f"Error en chat send: {res.data}"
    data = json.loads(res.data)
    print(f"Método de resolución: {data.get('method')}")
    assert data.get('method') != 'direct_intent', "No debería usar 'direct_intent' porque no hay intención arancelaria"
    print("Caso 3: PASADO\n")

    # Verificar mensajes en base de datos
    messages = session.query(ChatMessage).filter_by(thread_id=thread_id).order_by(ChatMessage.created_at.asc()).all()
    print(f"Total de mensajes en hilo {thread_id}: {len(messages)}")
    assert len(messages) == 6, f"Esperaba 6 mensajes en BD, encontré {len(messages)}"
    
    # Comprobar metadatos del primer bot msg
    bot_msg = messages[1]
    assert bot_msg.sender == 'bot'
    meta = json.loads(bot_msg.metadata_json)
    assert meta['method'] == 'direct_intent'
    assert meta['status'] == 'complete'
    assert meta['hs_code'] == '85171201'
    print("Verificación de Base de Datos: PASADA\n")

    print("--- Todas las pruebas del Detector de Intenciones han pasado con éxito! ---")

if __name__ == '__main__':
    test_intent_detector()
