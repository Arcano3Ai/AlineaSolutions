"""
Clasificador Arancelario Unificado
Consolida la búsqueda textual (léxica + semántica), la clasificación por IA (OpenAI o local)
con recuperación legal (RAG) y la lógica de las Reglas Generales de Interpretación (RGI).
"""

import os
import re
import json
import traceback
import unicodedata
import numpy as np
from database.models import Section, Chapter, Heading, Subheading, Fraction, RGIRule

# --- Configuración y Constantes de IA ---
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')
USE_OPENAI = bool(OPENAI_API_KEY)
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')
USE_GEMINI = bool(GEMINI_API_KEY)

PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
SNICE_RAG_PATH = os.path.join(PROJECT_ROOT, "database", "vector_db", "snice_chroma_db")
VUCEM_RAG_PATH = os.path.join(PROJECT_ROOT, "database", "vector_db", "vucem_chroma_db")

# Variable global única para instanciación en caché del modelo de SentenceTransformers
_EMBEDDING_MODEL = None

def _get_embedding_model():
    """Carga y retorna de manera perezosa (lazy load) la instancia global del modelo de embeddings."""
    global _EMBEDDING_MODEL
    if _EMBEDDING_MODEL is None:
        from sentence_transformers import SentenceTransformer
        _EMBEDDING_MODEL = SentenceTransformer('all-MiniLM-L6-v2')
    return _EMBEDDING_MODEL


class SharedEmbeddings:
    """Wrapper para compartir el modelo SentenceTransformer con Chroma/LangChain sin inicializar HuggingFaceEmbeddings."""
    def __init__(self, model):
        self.model = model

    def embed_documents(self, texts):
        embs = self.model.encode(texts, show_progress_bar=False)
        return embs.tolist()

    def embed_query(self, text):
        emb = self.model.encode(text, show_progress_bar=False)
        return emb.tolist()


# --- Diccionarios de Normalización y Vocabulario ---
STOP_WORDS = {
    "de", "la", "los", "las", "del", "el", "en", "y", "a", "para", "por",
    "con", "que", "es", "un", "una", "su", "se", "no", "lo", "al", "como",
    "mas", "pero", "sus", "le", "ya", "este", "entre", "todo", "esta",
    "sin", "era", "son", "ser", "han", "tiene", "m\u00e1s", "todo",
}

SYNONYMS = {
    "computadora": "computadora laptop pc ordenador procesador servidor tablet computadoras",
    "laptop": "computadora portatil laptop notebook ordenador procesador pc",
    "smartphone": "telefono smartphone celular movil receptor transmisor",
    "celular": "celular telefono smartphone movil receptor transmisor",
    "telefono": "telefono smartphone celular movil receptor transmisor",
    "auriculares": "auriculares audifonos cascos receptor microfono",
    "bisturi": "instrumento medico quirurgico bisturi",
    "jeringa": "jeringa aguja inyectable plastico desechable",
    "usb": "usb cable conector memoria almacenamiento",
    "ram": "ram memoria semiconductor chips",
    "cpu": "procesador cpu microprocesador circuito integrado semiconductor",
    "wifi": "wifi inalambrica bluetooth antena receptor transmisor emisor",
    "hdmi": "hdmi cable conector interfaz video",
    "led": "led pantalla monitor diodo emisor luz display oled",
    "pantalla": "pantalla monitor tv television led lcd oled display panel",
    "monitor": "pantalla monitor tv television led lcd oled display panel",
    "acero": "acero metal aleacion hierro",
    "inoxidable": "inoxidable corrosion",
    "valvula": "valvula griferia llave compuerta paso regulador canilla grifo",
    "filtro": "filtro purificador separador colador tamiz depurador",
    "bomba": "bomba compresor succion inyeccion hidraulico aspiracion",
    "tornillo": "tornillo perno tuerca remache sujetador pasador",
    "tuerca": "tuerca arandela sujecion perno",
    "engranaje": "engranaje rueda dentada reductor transmision piñon",
    "rodamiento": "rodamiento balero cojinete ruleman rodamiento bolas rodillos",
    "interruptor": "interruptor switch relé rele conmutador",
    "conector": "conector enchufe clavija regleta terminal acoplamiento",
    "supercapacitor": "supercapacitor condensador capacitor capacitador almacenamiento energia",
    "ultracapacitor": "supercapacitor condensador capacitor capacitador almacenamiento energia",
    "fresca": "fresca fresco refrigerado natural sin cocinar conservado",
    "congelado": "congelado helado preservado frio",
    "mueble": "mueble silla mesa sofa asiento mobiliario",
    "silla": "silla mueble asiento butaca banco",
    "juguete": "juguete muneca figura juego entretenimiento diversion infantil",
    "cable": "cable alambre conductor aislamiento electrico cobre aluminio",
    "pintura": "pintura barniz laca esmalte acrilico recubrimiento colorante",
    "libro": "libro texto impreso folleto catalogo obra",
    "bateria": "bateria acumulador pila litio niquel plomo recargable",
    "motor": "motor de explosion de combustion de piston embolo gasolina diesel",
    "diesel": "diesel motor encendido por compresion",
    "aceite": "aceite lubricante grasa lubricantes mineral vegetal sintetico",
    "automovil": "automovil auto coche vehiculo camioneta camion turismo turismo",
    "coche": "automovil auto coche vehiculo de pasajeros",
    "calzado": "calzado zapato bota tenis sandalia chancla",
    "zapato": "calzado zapato bota tenis bota cuero sintetico",
    "prenda": "prenda ropa vestir camisa playera pantalon sueter abrigo textil t-shirt",
    "oro": "oro plata joya metal precioso orfebreria",
    "diamante": "diamante piedra preciosa joya gema cristal",
    "aguacate": "aguacate aguacates paltas hass fresco fresca",
    "maiz": "maiz maizales elote grano amarillo forrajero",
    "tequila": "tequila mezcal licor bebida alcoholica espirituosa agave",
    "mezcal": "mezcal tequila licor bebida alcoholica espirituosa agave",
    "pluma": "pluma boligrafo lapicero estilografica plumas lapiceros boligrafos",
    "plumas": "pluma boligrafo lapicero estilografica plumas lapiceros boligrafos",
}


# --- Funciones Auxiliares de Procesamiento Léxico ---
def _normalize(text):
    nfkd = unicodedata.normalize('NFKD', text)
    return nfkd.encode('ASCII', 'ignore').decode('ASCII').lower().strip()


def _tokenize(text):
    return [w for w in re.findall(r'[a-z0-9]+', _normalize(text)) if len(w) > 1]


def _expand_query(text):
    """Expande la consulta agregando sinónimos definidos."""
    words = _tokenize(text)
    expanded = set(words)
    for w in words:
        if w in SYNONYMS:
            expanded.update(SYNONYMS[w].split())
    return list(expanded)


def _score_terms(query_tokens, text, code):
    text_lower = _normalize(text)
    code_lower = _normalize(code) if code else ""

    # Expansión de tokens
    expanded_tokens = _expand_query(" ".join(query_tokens))
    primary_tokens = query_tokens

    # Coincidencia de frase exacta (Boost máximo)
    full_query = " ".join(primary_tokens)
    if full_query in text_lower:
        return 50

    # Coincidencia de código directo
    code_score = 10 if full_query in code_lower else 0
    if code_score and len(full_query) >= 4:
        return 50

    matched_primary = 0
    score = code_score

    def _stem_match(word, target):
        return word in target or (len(word) >= 5 and target.startswith(word[:5]))

    for word in primary_tokens:
        if word in STOP_WORDS or len(word) < 3:
            continue
        
        if _stem_match(word, text_lower):
            matched_primary += 1
            score += 5
            # Boost si se encuentra en la cabecera (antes del separador '|')
            title_part = _normalize(text.split("|")[0] if "|" in text else text)
            if _stem_match(word, title_part):
                score += 2
                # Exact or plural/singular keyword match boost in LIGIE header title
                # Evitamos dar boost masivo a palabras meramente descriptivas o genéricas
                GENERIC_WORDS = {
                    "fresco", "fresca", "frescos", "frescas", "refrigerado", "refrigerada", "refrigerados", "refrigeradas",
                    "congelado", "congelada", "congelados", "congeladas", "consumo", "humano", "humanos", "animal", "animales",
                    "para", "los", "demas", "preparaciones", "preparacion", "tipo", "partes", "parte", "piezas", "pieza",
                    "uso", "fines", "destinada", "destinado", "importacion", "exportacion", "importaciones", "exportaciones",
                    "inferior", "superior", "igual", "exceda", "exceder", "excedente", "titulo", "título", "contenido", 
                    "peso", "diametro", "diámetro", "espesor", "grados", "grado", "porcentaje", "unidades", "medida",
                    "presentados", "presentadas", "forma", "formas", "clase", "clases", "caracteristicas", "características",
                    "los", "las", "que", "no", "esten", "estén", "con", "un", "una", "de", "del", "por", "los", "las"
                }
                title_words = re.findall(r'[a-z0-9]+', title_part)
                for tw in title_words:
                    if len(word) >= 3 and len(tw) >= 3:
                        if word in GENERIC_WORDS:
                            continue
                        # Si coinciden exactamente o difieren en s (singular/plural)
                        if word == tw or word == tw + "s" or tw == word + "s" or word == tw[:-1] or tw == word[:-1]:
                            score += 45
                            break

    # Match de sinónimos expandidos
    for word in expanded_tokens:
        if word not in primary_tokens and _stem_match(word, text_lower):
            score += 2

    # Penalización suave si faltan palabras principales importantes (solo para búsquedas cortas <= 5 palabras clave)
    if len(primary_tokens) <= 5 and len(primary_tokens) >= 3 and matched_primary < max(1, len(primary_tokens) * 0.25):
        missing_important = sum(
            1 for w in primary_tokens
            if w not in STOP_WORDS and len(w) >= 3 and w not in text_lower
        )
        score -= missing_important * 2

    # Bonus por proximidad de términos clave
    content_tokens = [w for w in primary_tokens if w not in STOP_WORDS and len(w) >= 3]
    if len(content_tokens) >= 2 and score > 0:
        text_words = text_lower.split()
        all_pos = {w: [] for w in content_tokens}
        for i, tw in enumerate(text_words):
            for w in content_tokens:
                if _stem_match(w, tw):
                    all_pos[w].append(i)
        found_close = False
        pair_count = 0
        for i in range(len(content_tokens)):
            for j in range(i+1, len(content_tokens)):
                wi = content_tokens[i]
                wj = content_tokens[j]
                if all_pos[wi] and all_pos[wj]:
                    min_dist = min(abs(pi - pj) for pi in all_pos[wi] for pj in all_pos[wj])
                    if min_dist <= 3:
                        pair_count += 1
                        found_close = True
        if pair_count >= 2:
            score += 20
        elif found_close:
            score += 8

    if score > 0 and score < 3:
        score = 3

    return max(0, score)


def _semantic_similarity(query, texts):
    """Calcula similitud coseno entre un query y una lista de textos mediante embeddings."""
    model = _get_embedding_model()
    q_emb = model.encode([query], normalize_embeddings=True, show_progress_bar=False)[0]
    t_embs = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
    sims = np.dot(t_embs, q_emb)
    return sims


# --- Motores de Recuperación Legal (RAG) ---
def _search_single_rag(db_path, query, top_k, emb_model=None):
    from langchain_community.vectorstores import Chroma
    if not os.path.exists(os.path.join(db_path, "chroma.sqlite3")):
        return []
    
    if emb_model is None:
        model = _get_embedding_model()
        embeddings = SharedEmbeddings(model)
    else:
        embeddings = emb_model
        
    db = Chroma(persist_directory=db_path, embedding_function=embeddings)
    results = db.similarity_search(query, k=top_k)
    return [r.page_content for r in results]


def search_rag(product_description, top_k=3, emb_model=None):
    """Busca en ambas tiendas vectoriales locales el contexto regulatorio relevante."""
    results = []
    try:
        results += _search_single_rag(SNICE_RAG_PATH, product_description, top_k, emb_model)
    except Exception:
        pass
    try:
        results += _search_single_rag(VUCEM_RAG_PATH, product_description, top_k, emb_model)
    except Exception:
        pass
    return results[:top_k * 2]


# --- Métodos de Clasificación y Búsqueda del API ---
def search_by_text(session, query, limit=50):
    """Realiza la búsqueda léxica y aplica re-ranking semántico local."""
    query_raw = query.strip()
    query = _normalize(query_raw)
    if not query or len(query) < 2:
        return []

    tokens = _tokenize(query_raw)
    if not tokens:
        return []

    # Expansión de sinónimos primarios para evitar brechas léxicas (ej. pluma -> bolígrafo)
    ESCRITURA_TERMS = {"pluma", "boligrafo", "bolígrafo", "lapicero", "estilografica", "estilográfica"}
    if any(t in tokens for t in ESCRITURA_TERMS):
        tokens.extend(["boligrafo", "boligrafos", "lapicero", "lapiceros", "estilografica"])


    results = []
    seen_codes = set()

    # Búsqueda en Subheadings
    for sub in session.query(Subheading).all():
        text = f"{sub.title} | {sub.description or ''}"
        code = sub.code
        s = _score_terms(tokens, text, code)
        if s > 0:
            heading = sub.heading
            chapter = heading.chapter
            seen_codes.add(code)
            results.append({
                'type': 'subheading',
                'code': code,
                'title': sub.title,
                'description': sub.description or '',
                'chapter_code': chapter.code,
                'chapter_title': chapter.title,
                'heading_code': heading.code,
                'score': s
            })

    # Búsqueda en Headings
    for h in session.query(Heading).all():
        if any(c.startswith(h.code[:4]) for c in seen_codes):
            continue
        text = f"{h.title} | {h.description or ''}"
        code = h.code
        s = _score_terms(tokens, text, code)
        if s > 0:
            chapter = h.chapter
            seen_codes.add(code)
            results.append({
                'type': 'heading',
                'code': code,
                'title': h.title,
                'description': h.description or '',
                'chapter_code': chapter.code,
                'chapter_title': chapter.title,
                'score': s
            })

    # Búsqueda en Fractions (NICO 8-dígitos)
    for f in session.query(Fraction).all():
        code = f.code
        sub = f.subheading
        heading = sub.heading if sub else None
        chapter = heading.chapter if heading else None

        parent_text = ""
        if sub:
            parent_text += f" {sub.title or ''} {sub.description or ''}"
        if heading:
            parent_text += f" {heading.title or ''} {heading.description or ''}"
        if chapter:
            parent_text += f" {chapter.title or ''}"

        text = f"{f.title} | {f.description or ''} | {parent_text}"
        s = _score_terms(tokens, text, code)
        if s > 0:
            results.append({
                'type': 'fraction',
                'code': code,
                'title': f.title or '',
                'description': f.description or '',
                'chapter_code': chapter.code if chapter else "",
                'chapter_title': chapter.title if chapter else "",
                'heading_code': heading.code if heading else "",
                'score': s
            })

    results.sort(key=lambda x: x['score'], reverse=True)
    # Seleccionamos un pool de hasta 40 candidatos léxicos para que el re-ranking semántico los evalúe
    top = results[:40]

    # Re-ranking Semántico
    try:
        texts_to_rank = []
        for r in top:
            txt = f"{r['title']} {r.get('description','')} {r.get('chapter_title','')}"
            texts_to_rank.append(txt[:512])
        if texts_to_rank:
            sims = _semantic_similarity(query_raw, texts_to_rank)
            for i, r in enumerate(top):
                kw = r['score']
                cosine_sim = float(sims[i])
                # Normalizar similitud coseno (-1 a 1) a una escala positiva de 0 a 100 puntos
                sem_points = max(0.0, cosine_sim) * 100.0
                r['sem_score'] = round(cosine_sim, 4)
                # Puntuación combinada óptima de grado de búsqueda híbrida: 50% Léxico + 50% Semántico
                r['combined_score'] = round(kw * 0.50 + sem_points * 0.50, 1)
            top.sort(key=lambda x: x['combined_score'], reverse=True)
            for r in top:
                r['score'] = r['combined_score']
    except Exception:
        pass

    return top[:limit]


def classify_with_ai(session, product_description, image_bytes=None, mime_type=None, history=None):
    """Ejecuta clasificación asistida por IA inteligente (Gemini, OpenAI o Transformers local con RAG)."""
    if USE_GEMINI:
        return _classify_with_gemini(session, product_description, image_bytes, mime_type, history)
    elif USE_OPENAI:
        return _classify_with_openai(session, product_description, history)
    else:
        return _classify_with_transformers(session, product_description, history)


def _classify_with_gemini(session, product_description, image_bytes=None, mime_type=None, history=None):
    try:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
        
        # Recuperar contexto RAG local
        rag_context = search_rag(product_description, top_k=3)
        rag_text = "\n".join(rag_context) if rag_context else "Sin información RAG adicional."
        
        # Recuperar candidatos de búsqueda léxica
        lexical_results = search_by_text(session, product_description, limit=15)
        hs_context = "\n".join([f"{r['code']}: {r['title']} (Score: {r['score']})" for r in lexical_results])
        
        # Formatear el historial de la conversación
        history_text = ""
        if history:
            for msg in history:
                role = "Usuario" if msg['sender'] == 'user' else "Asistente / Bot"
                history_text += f"{role}: {msg['content']}\n"
        
        prompt = f"""Eres un clasificador arancelario experto en la LIGIE (Ley de los Impuestos Generales de Importación y de Exportación de México) y el Sistema Armonizado.
Dada la siguiente descripción de mercancía (y opcionalmente una imagen/foto adjunta), determina el código arancelario (HS Code a 6 o 8 dígitos) más apropiado.

IMPORTANTE: Si la descripción o la imagen son ambiguas, vagas o carecen de detalles técnicos críticos (como el material, uso, potencia, composición) para clasificar con un nivel de confianza >= 0.8, debes marcar "status": "clarification_needed" y formular de 3 a 5 preguntas clave específicas o de aclaración progresiva de forma secuencial en el campo "questions" para que el usuario aclare el producto y poder dar una fracción exacta. También puedes proporcionar opciones rápidas en el campo "choices" (una lista de strings con opciones que resuelvan la ambigüedad) si consideras que facilitan al usuario la aclaración directa.

Mercancía actual a clasificar: {product_description}

Historial de aclaraciones y conversación previa con el usuario:
{history_text or "No hay historial previo."}

Candidatos arancelarios locales sugeridos:
{hs_context}

Contexto normativo y regulatorio RAG:
{rag_text}

Tu respuesta DEBE ser únicamente un objeto JSON válido con el siguiente formato:
{{
  "status": "complete" o "clarification_needed",
  "hs_code": "código arancelario de 6 u 8 dígitos sin puntos si está completo, o vacío si necesita aclaración",
  "confidence": nivel de confianza entre 0.0 y 1.0,
  "reasoning": "un bloque HTML hermoso y estilizado que representa un 'MAPA DE RAZONAMIENTO MERCIOLÓGICO' completo, estructurado y explicativo. Si es clarification_needed, explica qué falta desde una perspectiva merciológica",
  "questions": [
     "pregunta 1...",
     "pregunta 2..."
  ],
  "choices": [
     "opción rápida 1...",
     "opción rápida 2..."
  ]
}}

INSTRUCCIONES CLAVE PARA EL CAMPO "reasoning":
1. Debe contener HTML válido, con estilos en línea (inline-styles) limpios e integrados, diseñado para pantallas oscuras/modernas (fondos semitransparentes oscuros como rgba(30, 41, 59, 0.5), bordes finos, fuentes legibles como system-ui, colores acentuados elegantes como el azul cielo/cian #38bdf8).
2. Estructura el mapa merciológico en las siguientes secciones visuales claramente definidas mediante un grid de 2x2 o tarjetas estructuradas:
   - "1. Naturaleza de la mercancía": Identificación comercial y técnica de qué tipo de bien es.
   - "2. Materia constitutiva": Análisis de qué materiales o componentes la constituyen y su relevancia para la clasificación arancelaria.
   - "3. Función y uso": Propósito, aplicación y mecanismo de acción del producto.
   - "4. Presentación": Estado, empaque, ensamblaje o acondicionamiento de la mercancía.
3. Agrega un bloque de "Justificación Legal y Reglas de Interpretación (RGI)":
   - Sección y Capítulo aplicable de la LIGIE con su título.
   - Partida y Subpartida con justificación legal explícita.
   - Reglas Generales de Interpretación (RGI) específicas aplicadas (por ejemplo: RGI 1, RGI 2a, RGI 3b, RGI 6) detallando por qué se seleccionaron.
4. Si la clasificación es sobre dispositivos médicos, electrónica compleja, partes industriales, partes automotrices, etc., explica con particular rigor técnico por qué NO se clasifica bajo materias primas o metales simples, sino bajo su partida específica de uso."""

        contents = [prompt]
        if image_bytes and mime_type:
            contents.append({
                "mime_type": mime_type,
                "data": image_bytes
            })

        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(
            contents,
            generation_config=genai.GenerationConfig(
                response_mime_type="application/json",
                temperature=0.1
            )
        )
        result = json.loads(response.text)
        return {
            'status': result.get('status', 'complete'),
            'hs_code': result.get('hs_code', '').replace('.', '').strip(),
            'confidence': float(result.get('confidence', 0.8)),
            'reasoning': result.get('reasoning', 'Clasificado mediante Google Gemini 1.5.'),
            'questions': result.get('questions', []),
            'choices': result.get('choices', []),
            'method': 'gemini'
        }
    except Exception as e:
        # Fallback inmediato y transparente al motor local si hay algún error
        return _classify_with_transformers(session, product_description, history)


def _classify_with_openai(session, product_description, history=None):
    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)

        subheadings = session.query(Subheading).limit(200).all()
        hs_context = "\n".join([f"{s.code}: {s.title}" for s in subheadings])

        rag_context = search_rag(product_description)
        rag_text = "\n".join(rag_context[:2]) if rag_context else ""

        prompt = f"""Eres un clasificador arancelario experto en el Sistema Armonizado.
Dada la siguiente descripción de mercancía, determina el código HS más apropiado (6 dígitos).

Mercancía: {product_description}

Códigos disponibles (muestra):
{hs_context}

{"Contexto legal relevante:" + rag_text if rag_text else ""}

Responde SOLO con un JSON válido en este formato:
{{"hs_code": "XXXXXX", "confidence": 0.95, "reasoning": "breve explicación"}}"""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        result = json.loads(response.choices[0].message.content)
        return {
            'status': 'complete',
            'hs_code': result.get('hs_code', ''),
            'confidence': result.get('confidence', 0),
            'reasoning': result.get('reasoning', ''),
            'questions': [],
            'method': 'openai'
        }
    except Exception as e:
        return {'status': 'complete', 'hs_code': '', 'confidence': 0, 'reasoning': f'Error: {str(e)}', 'questions': [], 'method': 'openai'}


def _classify_with_transformers(session, product_description, history=None):
    try:
        # Diccionario de ambigüedad merciológica para Uniclasificador (opción múltiple)
        AMBIGUOUS_MAP = {
            "pluma": {
                "question": "El término 'pluma' es ambiguo en la LIGIE. Por favor, seleccione la naturaleza de su mercancía:",
                "choices": [
                    "Bolígrafo / pluma de plástico para escritura en oficina",
                    "Café tipo Pluma Hidalgo (cosechado en México)",
                    "Plumas de ave naturales para adorno u ornamento"
                ]
            },
            "bateria": {
                "question": "El término 'batería' es ambiguo en la LIGIE. Por favor, seleccione la naturaleza de su mercancía:",
                "choices": [
                    "Batería recargable de iones de litio (acumulador eléctrico)",
                    "Batería de cocina de acero inoxidable (utensilio)",
                    "Batería musical de percusión (instrumento)"
                ]
            },
            "batería": {
                "question": "El término 'batería' es ambiguo en la LIGIE. Por favor, seleccione la naturaleza de su mercancía:",
                "choices": [
                    "Batería recargable de iones de litio (acumulador eléctrico)",
                    "Batería de cocina de acero inoxidable (utensilio)",
                    "Batería musical de percusión (instrumento)"
                ]
            },
            "valvula": {
                "question": "El término 'válvula' es ambiguo en la LIGIE. Por favor, seleccione la naturaleza de su mercancía:",
                "choices": [
                    "Válvula de acero de compuerta para control de fluidos",
                    "Válvula cardíaca de reemplazo (dispositivo médico/prótesis)"
                ]
            },
            "válvula": {
                "question": "El término 'válvula' es ambiguo en la LIGIE. Por favor, seleccione la naturaleza de su mercancía:",
                "choices": [
                    "Válvula de acero de compuerta para control de fluidos",
                    "Válvula cardíaca de reemplazo (dispositivo médico/prótesis)"
                ]
            },
            "naranja": {
                "question": "El término 'naranja' es ambiguo en la LIGIE. Por favor, seleccione la naturaleza de su mercancía:",
                "choices": [
                    "Naranjas frescas para consumo alimenticio",
                    "Aceite esencial de naranja para perfumería/cosméticos"
                ]
            }
        }

        # Analizar coincidencia de ambigüedad si la consulta es corta (menos de 4 palabras significativas)
        words = [w.lower().strip(",.!?") for w in product_description.split() if w.lower() not in STOP_WORDS]
        for kw, data in AMBIGUOUS_MAP.items():
            if kw in words and len(words) <= 3:
                # Comprobar si ya existe alguna de las aclaraciones en la descripción
                has_clarification = any(c.lower() in product_description.lower() for c in data["choices"])
                
                # Comprobar si ya se eligió una opción rápida del historial
                chosen_option = None
                if not has_clarification and history:
                    for msg in history:
                        if msg['sender'] == 'user':
                            msg_content = msg['content'].strip().lower()
                            for choice in data["choices"]:
                                if choice.lower() in msg_content:
                                    chosen_option = choice
                                    break
                        if chosen_option:
                            break

                if chosen_option:
                    product_description = chosen_option
                    words = [w.lower().strip(",.!?") for w in product_description.split() if w.lower() not in STOP_WORDS]
                elif not has_clarification:
                    return {
                        'status': 'clarification_needed',
                        'hs_code': '',
                        'confidence': 0.4,
                        'reasoning': 'Se ha detectado ambigüedad o homonimia merciológica en el término ingresado. El Uniclasificador requiere resolver la naturaleza del producto.',
                        'questions': [data["question"]],
                        'choices': data["choices"],
                        'method': 'local'
                    }

        # Si la consulta es muy corta o vaga (menos de 2 palabras significativas), pedir aclaraciones
        if len(words) <= 1:
            return {
                'status': 'clarification_needed',
                'hs_code': '',
                'confidence': 0.3,
                'reasoning': 'La descripción provista es demasiado corta o ambigua para clasificar localmente de forma precisa.',
                'questions': [
                    '¿De qué material está hecho el producto (acero, plástico, aluminio, vidrio, etc.)?',
                    '¿Cuál es la función, aplicación o uso principal del artículo?',
                    '¿Cuenta con especificaciones técnicas clave (como voltaje, diámetro, capacidad o potencia)?'
                ],
                'choices': [],
                'method': 'local'
            }

        # Usamos la búsqueda combinada (léxica + semántica con re-ranking de embeddings)
        results = search_by_text(session, product_description, limit=40)
        if not results:
            return {'status': 'complete', 'hs_code': '', 'confidence': 0, 'reasoning': 'No se encontraron candidatos', 'questions': [], 'method': 'local'}

        # --- REGLA ADUANERA DE DESAMBIGUACIÓN SEMÁNTICA (HOMONIMIA / PLUMA) ---
        # Si contiene "pluma" pero también términos de oficina/escritura/plástico/tinta,
        # evitar clasificar en Capítulo 09 (Café) y priorizar Capítulo 96 (Bolígrafos).
        desc_lower = product_description.lower()
        ESCRITURA_KEYWORDS = ["plastico", "plástico", "escribir", "escritura", "boligrafo", "bolígrafo", "lapicero", "oficina", "escritorio", "tinta"]
        is_instrumento_escritura = (
            ("pluma" in desc_lower or "boligrafo" in desc_lower or "bolígrafo" in desc_lower or "lapicero" in desc_lower)
            and any(w in desc_lower for w in ESCRITURA_KEYWORDS)
        )
        if is_instrumento_escritura:
            WRONG_CHAPTERS = {"09", "32", "39", "67"}
            for r in results:
                if r.get("chapter_code") in WRONG_CHAPTERS:
                    r["score"] -= 100
            results.sort(key=lambda x: x["score"], reverse=True)


        # --- SISTEMA EXPERTO MERCEOLÓGICO: PRIORIZACIÓN POR FUNCIÓN (RGI 1 & 3b) ---
        # Mapeo específico de palabras clave de alta especialización funcional a sus Capítulos autorizados
        FUNCTIONAL_MAP = {
            "96": ["boligrafo", "bolígrafo", "pluma", "lapicero", "boligrafos", "lapiceros", "estilografica", "estilográfica"],
            "90": ["protesis", "prótesis", "medico", "médico", "quirurgico", "quirúrgico", "reemplazo articular"],
            "84": ["valvula", "válvula", "bomba", "motor", "engranaje", "compresor"],
            "85": ["interruptor", "conector", "bateria", "batería", "capacitor", "supercapacitor"]
        }
        
        target_chapters = []
        for ch_code, keywords in FUNCTIONAL_MAP.items():
            if any(k in product_description.lower() for k in keywords):
                target_chapters.append(ch_code)

        # Y si hay candidatos de capítulos metalúrgicos (73-81) o plásticos (39) compitiendo con los capítulos funcionales detectados:
        if target_chapters:
            functional_results = [r for r in results if r.get('chapter_code', '') in target_chapters]
            material_results   = [r for r in results if r.get('chapter_code', '') in ['39', '73', '74', '75', '76', '81']]

            # Si existe al menos un candidato funcional, promoverlo al primer lugar (RGI 3b – Carácter Esencial)
            if functional_results:
                top_func = functional_results[0]
                if top_func in results:
                    results.remove(top_func)
                results.insert(0, top_func)

                # Si también hay competencia de material, registrar razonamiento RGI 3b explícito
                if material_results:
                    top_material = material_results[0]
                    top = results[0]
                    raw_score = float(top.get('score', 0))
                    confidence = min(1.0, max(0.1, raw_score / 60.0))
                    alternatives = [{'code': r['code'], 'title': r['title'], 'score': r['score']} for r in results[1:5]]
                    return {
                        'status': 'complete',
                        'hs_code': top['code'],
                        'confidence': confidence,
                        'reasoning': (
                            f"<b>Función detectada:</b> Capítulo {top_func['chapter_code']} ({top_func['title'][:60]}). "
                            f"<b>RGI 3b:</b> La función especializada prima sobre la materia constitutiva (Cap {top_material['chapter_code']})."
                        ),
                        'alternatives': alternatives,
                        'questions': [],
                        'method': 'local'
                    }


        top = results[0]
        raw_score = float(top.get('score', 0))
        confidence = min(1.0, max(0.1, raw_score / 60.0))

        alternatives = []
        for r in results[1:5]:
            alternatives.append({
                'code': r['code'],
                'title': r['title'],
                'score': r['score']
            })

        reasoning_html = (
            f'<div class="merceology-map" style="background: rgba(30, 41, 59, 0.45); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 8px; padding: 16px; margin-top: 12px; color: #f1f5f9; font-family: system-ui, -apple-system, BlinkMacSystemFont, \'Segoe UI\', Roboto, sans-serif;">'
            f'  <h4 style="margin-top: 0; margin-bottom: 12px; color: #38bdf8; display: flex; align-items: center; gap: 8px; font-size: 15px; border-bottom: 1px solid rgba(255, 255, 255, 0.15); padding-bottom: 8px;">'
            f'    <span>📋</span> MAPA DE RAZONAMIENTO LÉXICO-SEMÁNTICO LOCAL'
            f'  </h4>'
            f'  <div style="background: rgba(15, 23, 42, 0.4); border: 1px solid rgba(255, 255, 255, 0.05); border-radius: 6px; padding: 12px; font-size: 13px; line-height: 1.5;">'
            f'    <div style="margin-bottom: 6px;"><strong>Coincidencia Sugerida:</strong> <span style="color: #38bdf8; font-family: monospace; font-weight: bold;">{top["code"]}</span> - {top["title"]}</div>'
            f'    <div style="margin-bottom: 6px;"><strong>Confianza del Motor:</strong> {confidence * 100:.0f}% ({top["score"]:.1f} puntos combinados)</div>'
            f'    <div style="margin-top: 8px; border-top: 1px solid rgba(255, 255, 255, 0.08); padding-top: 8px; color: #94a3b8; font-size: 12px;">'
            f'      Este resultado se obtuvo mediante similitud léxico-semántica local con el modelo <code>all-MiniLM-L6-v2</code>. Conforme a la <strong>RGI 1</strong>, la descripción técnica de la mercancía presenta una fuerte afinidad lingüística y técnica con la partida seleccionada.'
            f'    </div>'
            f'  </div>'
            f'</div>'
        )

        return {
            'status': 'complete',
            'hs_code': top['code'],
            'confidence': confidence,
            'reasoning': reasoning_html,
            'alternatives': alternatives,
            'questions': [],
            'method': 'local'
        }
    except Exception as e:
        return {'status': 'complete', 'hs_code': '', 'confidence': 0, 'reasoning': f'Error: {str(e)}', 'questions': [], 'method': 'local'}


# --- Lógica de las Reglas Generales de Interpretación (RGI) ---
def get_all_rules(session):
    """Consulta la base de datos y retorna la lista ordenada de las reglas RGI."""
    rules = session.query(RGIRule).order_by(RGIRule.rule_number).all()
    return [{
        'id': r.id,
        'rule_number': r.rule_number,
        'title': r.title,
        'content': r.content,
        'examples': r.examples,
    } for r in rules]


def apply_rgi(session, product_description):
    """Evalúa la descripción y sugiere la aplicación paso a paso de las reglas RGI."""
    rules = get_all_rules(session)
    suggestions = []
    for rule in rules:
        rn = rule['rule_number']
        if rn == 1:
            suggestions.append(f"RGI 1: Analiza los textos de las partidas y Notas. Busca si '{product_description}' coincide exactamente con alguna partida.")
        elif rn == 2:
            suggestions.append(f"RGI 2: Si '{product_description}' es un artículo incompleto pero con las características esenciales, clasifícalo como el completo.")
        elif rn == 3:
            suggestions.append(f"RGI 3: Si '{product_description}' podría clasificarse en varias partidas, elige la más específica (3a), o la que le dé carácter esencial (3b), o la última en numeración (3c).")
        elif rn == 4:
            suggestions.append(f"RGI 4: Si ninguna regla anterior aplica, clasifica '{product_description}' por analogía con la mercancía más similar.")
        elif rn == 5:
            suggestions.append(f"RGI 5: Si '{product_description}' incluye un envase o estuche, evalúa si se clasifica junto con el artículo.")
        elif rn == 6:
            suggestions.append(f"RGI 6: Una vez determinada la partida (4 dígitos), aplica las reglas anteriores a nivel de subpartida (6-8 dígitos).")
    return {"rules": rules, "suggestions": suggestions}
