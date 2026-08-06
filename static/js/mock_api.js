// ==========================================
// Alinea Solutions - Mock API Client-Side
// Permite que la aplicación funcione 100% estática en GitHub Pages
// ==========================================

// Guardar referencia al fetch original
window.realFetch = window.fetch;

// Configuración de la API Key de Gemini
window.saveGeminiApiKey = function(key) {
    localStorage.setItem('gemini_api_key', key.trim());
    console.log("Gemini API Key guardada localmente.");
};

// Cargar clave almacenada en el campo de configuración
document.addEventListener('DOMContentLoaded', () => {
    const keyInput = document.getElementById('gemini-api-key-input');
    if (keyInput) {
        const savedKey = localStorage.getItem('gemini_api_key') || '';
        keyInput.value = savedKey;
    }
});

// Variables globales para la LIGIE en caché
let cachedHsCatalog = null;
let cachedNicoDescriptions = null;

// Cargar catálogo LIGIE local desde archivos JSON
async function ensureCatalogLoaded() {
    if (!cachedHsCatalog) {
        try {
            const res = await window.realFetch('data/hs_codes.json');
            cachedHsCatalog = await res.json();
            console.log("Catálogo LIGIE (hs_codes.json) cargado en memoria.");
        } catch (e) {
            console.error("Error cargando hs_codes.json:", e);
            cachedHsCatalog = { sections: [] };
        }
    }
    if (!cachedNicoDescriptions) {
        try {
            const res = await window.realFetch('data/nico_real_descriptions.json');
            cachedNicoDescriptions = await res.json();
            console.log("Descripciones NICO (nico_real_descriptions.json) cargadas en memoria.");
        } catch (e) {
            console.error("Error cargando nico_real_descriptions.json:", e);
            cachedNicoDescriptions = { by_8digit: {} };
        }
    }
}

// Inicializar localStorage si está vacío
function seedLocalStorage() {
    if (!localStorage.getItem('crm_clients')) {
        localStorage.setItem('crm_clients', JSON.stringify([
            {id: 1, rfc: 'SOL890412AA1', name: 'ALINEA S.A.S. DE C.V.', patent: '3589', agent: 'Lic. Roberto Delgado', status: 'Activo', created_at: new Date().toISOString()},
            {id: 2, rfc: 'EXP990101BB3', name: 'GLOBAL LOGISTICS MEXICO', patent: '4012', agent: 'Dra. Alicia Mendoza', status: 'Activo', created_at: new Date().toISOString()},
            {id: 3, rfc: 'ARQ150403CC4', name: 'ALINEA SOLUTIONS S.A. DE C.V.', patent: '1650', agent: 'Ing. Sergio Montes', status: 'Activo', created_at: new Date().toISOString()}
        ]));
    }
    if (!localStorage.getItem('erp_inventory')) {
        localStorage.setItem('erp_inventory', JSON.stringify([
            {id: 1, sku: 'LAP-THINK-001', description: 'Laptop Lenovo ThinkPad T14 AMD Ryzen 7', sat_code: '8471.30.01', unit: 'H87', quantity: 150.0, price: 1200.00, created_at: new Date().toISOString()},
            {id: 2, sku: 'BATT-LITH-100', description: 'Batería de Litio Recargable 3.7V 2000mAh', sat_code: '8507.60.01', unit: 'H87', quantity: 5000.0, price: 8.50, created_at: new Date().toISOString()},
            {id: 3, sku: 'VALV-STEEL-08', description: 'Válvula de compuerta de acero inoxidable 2 pulgadas', sat_code: '8481.80.01', unit: 'H87', quantity: 45.0, price: 350.00, created_at: new Date().toISOString()},
            {id: 4, sku: 'ORANGE-FRESH-A', description: 'Naranjas frescas tipo Valencia calidad exportación', sat_code: '0805.10.01', unit: 'KGM', quantity: 12000.0, price: 0.85, created_at: new Date().toISOString()}
        ]));
    }
    if (!localStorage.getItem('audit_logs')) {
        localStorage.setItem('audit_logs', JSON.stringify([
            {id: 1, username: 'sistema', action: 'Inicialización del sistema', module: 'ADMIN', details: 'Ecosistema de Alinea SA de CV cargado en modo estático local.', created_at: new Date().toISOString(), ip_address: '127.0.0.1'},
            {id: 2, username: 'sistema', action: 'Carga de catálogo arancelario', module: 'CLASSIFIER', details: 'Se cargó el catálogo HS básico con 21 secciones en cliente.', created_at: new Date().toISOString(), ip_address: '127.0.0.1'}
        ]));
    }
    if (!localStorage.getItem('vucem_acuses')) {
        localStorage.setItem('vucem_acuses', JSON.stringify([]));
    }
    if (!localStorage.getItem('cartaporte_list')) {
        localStorage.setItem('cartaporte_list', JSON.stringify([]));
    }
    if (!localStorage.getItem('mve_list')) {
        localStorage.setItem('mve_list', JSON.stringify([]));
    }
    if (!localStorage.getItem('classifications')) {
        localStorage.setItem('classifications', JSON.stringify([]));
    }
}

seedLocalStorage();

// Añadir una entrada a la bitácora de auditoría
function addAuditLog(action, module, details) {
    const logs = JSON.parse(localStorage.getItem('audit_logs') || '[]');
    logs.unshift({
        id: Date.now(),
        username: sessionStorage.getItem('alinea_user') || 'admin',
        action: action,
        module: module,
        details: details,
        created_at: new Date().toISOString(),
        ip_address: '127.0.0.1'
    });
    localStorage.setItem('audit_logs', JSON.stringify(logs));
}

// Validador de descripciones del Anexo 22 en JS
function validateDescriptionLocal(description) {
    if (!description || typeof description !== 'string') {
        return {
            is_compliant: false,
            score: 0,
            warnings: ["La descripción está vacía o es inválida."],
            suggestions: ["Ingrese una descripción detallada de la mercancía."]
        };
    }

    const descLower = description.toLowerCase();
    const warnings = [];
    const suggestions = [];
    let score = 100;

    const FORBIDDEN_GENERICS = [
        "partes", "refacciones", "accesorios", "equipo", "aparato", "maquina", "material",
        "productos", "mercancia", "articulos", "herramienta", "pieza", "dispositivo", "sistema"
    ];
    const BRAND_KEYWORDS = ["marca", "brand", "mca", "make"];
    const MODEL_KEYWORDS = ["modelo", "model", "mod", "style"];
    const SERIAL_KEYWORDS = ["serie", "serial", "s/n", "sn", "n/s", "ns"];

    // 1. Longitud mínima
    if (description.trim().length < 15) {
        score -= 30;
        warnings.push("Descripción excesivamente corta para identificar la mercancía.");
        suggestions.push("Amplíe el detalle indicando qué es, cómo funciona y de qué material está hecho.");
    }

    // 2. Términos genéricos
    let foundGeneric = FORBIDDEN_GENERICS.find(g => descLower.includes(g));
    if (foundGeneric) {
        const words = descLower.split(/\s+/);
        if (words.length <= 3) {
            score -= 40;
            warnings.push(`Uso crítico de término genérico prohibido sin calificar: '${foundGeneric}'.`);
            suggestions.push(`No declare únicamente '${foundGeneric}'. Especifique su naturaleza (ej. 'partes de computadora portátil' en lugar de 'partes').`);
        } else {
            score -= 15;
            warnings.push(`Uso de término genérico: '${foundGeneric}'. Asegúrese de que esté debidamente calificado.`);
            suggestions.push("Califique los términos genéricos detallando su uso específico en la industria.");
        }
    }

    // 3. Marca
    const hasBrand = BRAND_KEYWORDS.some(k => descLower.includes(k));
    if (!hasBrand) {
        score -= 15;
        warnings.push("Falta declarar explícitamente la Marca comercial del fabricante.");
        suggestions.push("Agregue la marca del fabricante (ej. 'Marca: Apple' o 'Marca: S/M' si no tiene marca comercial).");
    }

    // 4. Modelo
    const hasModel = MODEL_KEYWORDS.some(k => descLower.includes(k));
    if (!hasModel) {
        const hasAlphanumericModel = description.split(/\s+/).some(w => w.length > 3 && /\d/.test(w) && /[a-zA-Z]/.test(w));
        if (!hasAlphanumericModel) {
            score -= 15;
            warnings.push("Falta declarar el Modelo comercial del fabricante.");
            suggestions.push("Indique el modelo comercial de la mercancía (ej. 'Modelo: ThinkPad-E14' o 'Modelo: S/M').");
        }
    }

    // 5. Serie
    const hasSerial = SERIAL_KEYWORDS.some(k => descLower.includes(k));
    const isElectronic = ["laptop", "computadora", "motor", "telefono", "pantalla", "bateria", "vehiculo"].some(w => descLower.includes(w));
    if (isElectronic && !hasSerial) {
        score -= 10;
        warnings.push("Falta indicar Número de Serie (Requerido para electrónicos, maquinaria y activos fijos).");
        suggestions.push("Declare el número de serie único del fabricante (ej. 'Serie: 98765A' o 'Serie: No aplica').");
    }

    score = Math.max(0, score);
    return {
        is_compliant: score >= 70,
        score: score,
        warnings: warnings,
        suggestions: suggestions
    };
}

// Diccionarios de stop words y sinónimos para el buscador local JS
const STOP_WORDS = new Set([
    "de", "la", "los", "las", "del", "el", "en", "y", "a", "para", "por",
    "con", "que", "es", "un", "una", "su", "se", "no", "lo", "al", "como",
    "mas", "pero", "sus", "le", "ya", "este", "entre", "todo", "esta",
    "sin", "era", "son", "ser", "han", "tiene", "más"
]);

const SYNONYMS = {
    "computadora": "computadora laptop pc ordenador procesador servidor tablet computadoras",
    "laptop": "computadora portatil laptop notebook ordenador procesador pc",
    "smartphone": "telefono smartphone celular movil receptor transmisor",
    "celular": "celular telefono smartphone movil receptor transmisor",
    "telefono": "telefono smartphone celular movil receptor transmisor",
    "bateria": "bateria acumulador pila litio niquel plomo recargable",
    "batería": "bateria acumulador pila litio niquel plomo recargable",
    "valvula": "valvula griferia llave compuerta paso regulador canilla grifo",
    "válvula": "valvula griferia llave compuerta paso regulador canilla grifo",
    "naranja": "naranjas frescas para consumo alimenticio aceites esenciales"
};

// Normalizar y tokenizar texto
function normalizeText(text) {
    return text.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().trim();
}

function tokenize(text) {
    return normalizeText(text).split(/[^a-z0-9]+/).filter(w => w.length > 1);
}

function expandQuery(tokens) {
    const expanded = new Set(tokens);
    for (const w of tokens) {
        if (SYNONYMS[w]) {
            SYNONYMS[w].split(/\s+/).forEach(t => expanded.add(t));
        }
    }
    return Array.from(expanded);
}

// Búsqueda léxica local en JavaScript cargando del JSON
async function performLocalSearch(query) {
    await ensureCatalogLoaded();
    const queryNormalized = normalizeText(query);
    const tokens = tokenize(query);
    if (tokens.length === 0) return [];

    const expandedTokens = expandQuery(tokens);
    const results = [];

    // Recorrer el catálogo HS
    for (const section of cachedHsCatalog.sections) {
        for (const chapter of section.chapters) {
            for (const heading of chapter.headings) {
                // Comprobar Partida
                let headingScore = computeMatchScore(tokens, expandedTokens, heading.title + " " + heading.description, heading.code);
                if (headingScore > 0) {
                    results.push({
                        type: 'heading',
                        code: heading.code,
                        title: heading.title,
                        description: heading.description || '',
                        chapter_code: chapter.code,
                        chapter_title: chapter.title,
                        score: headingScore
                    });
                }

                for (const subheading of heading.subheadings) {
                    // Comprobar Subpartida
                    let subScore = computeMatchScore(tokens, expandedTokens, subheading.title + " " + subheading.description, subheading.code);
                    if (subScore > 0) {
                        results.push({
                            type: 'subheading',
                            code: subheading.code,
                            title: subheading.title,
                            description: subheading.description || '',
                            chapter_code: chapter.code,
                            chapter_title: chapter.title,
                            heading_code: heading.code,
                            score: subScore
                        });
                    }

                    // Buscar fracciones arancelarias hijas de esta subpartida en nico_real_descriptions.json
                    const subCodeRaw = subheading.code; // ej. 850760
                    const subCodeWithDot = `${subCodeRaw.slice(0,4)}.${subCodeRaw.slice(4,6)}`;
                    
                    for (const [fracCode, fracDesc] of Object.entries(cachedNicoDescriptions.by_8digit)) {
                        if (fracCode.startsWith(subCodeWithDot) || fracCode.replace(/\./g, '').startsWith(subCodeRaw)) {
                            let fracScore = computeMatchScore(tokens, expandedTokens, fracDesc + " " + subheading.title + " " + heading.title, fracCode);
                            if (fracScore > 0) {
                                results.push({
                                    type: 'fraction',
                                    code: fracCode.replace(/\./g, ''),
                                    title: fracDesc,
                                    description: `Fracción arancelaria de la subpartida ${subheading.title}`,
                                    chapter_code: chapter.code,
                                    chapter_title: chapter.title,
                                    heading_code: heading.code,
                                    score: fracScore
                                });
                            }
                        }
                    }
                }
            }
        }
    }

    results.sort((a, b) => b.score - a.score);
    return results.slice(0, 50);
}

// Calcular la puntuación de coincidencia léxica
function computeMatchScore(queryTokens, expandedTokens, text, code) {
    const textLower = normalizeText(text);
    const codeLower = normalizeText(code);
    
    const fullQuery = queryTokens.join(" ");
    
    // Coincidencia exacta de frase
    if (textLower.includes(fullQuery)) return 50;
    if (codeLower.includes(fullQuery.replace(/\./g, '')) && fullQuery.length >= 4) return 50;

    let score = 0;
    let matchedWords = 0;

    for (const word of queryTokens) {
        if (STOP_WORDS.has(word) || word.length < 3) continue;
        if (textLower.includes(word)) {
            matchedWords++;
            score += 5;
            // Boost si coincide al inicio del texto
            if (textLower.startsWith(word)) score += 5;
        }
    }

    // Boost por sinónimos
    for (const word of expandedTokens) {
        if (!queryTokens.includes(word) && textLower.includes(word)) {
            score += 2;
        }
    }

    return score;
}

// Mapeo de impuestos aduaneros ficticios por capítulo
function getMockTaxes(code) {
    const cap = code.slice(0, 2);
    let igi = 0.10;
    let iva = 0.16;
    let ieps = 0.00;

    if (cap === "84" || cap === "85") {
        igi = 0.00; // Tratados
    } else if (cap === "08" || cap === "09") {
        igi = 0.20; // Alimentos protegidos
        iva = 0.00; // Tasa cero
    } else if (cap === "22") {
        igi = 0.20;
        ieps = 0.265; // Bebidas alcoholicas
    }

    return {
        igi: `${Math.round(igi * 100)}%`,
        iva: `${Math.round(iva * 100)}%`,
        ieps: `${Math.round(ieps * 100)}%`,
        igi_val: igi,
        iva_val: iva,
        ieps_val: ieps
    };
}

// Mapeo de regulaciones no arancelarias (RRNAs)
function getMockRRNAs(code) {
    const cap = code.slice(0, 2);
    if (cap === "90") {
        return ["Autorización de la Comisión Federal para la Protección contra Riesgos Sanitarios (COFEPRIS)."];
    } else if (cap === "85" && (code.startsWith("8507") || code.startsWith("8506"))) {
        return ["NOM-212-SCFI-2017 (Características de seguridad de pilas y baterías).", "Aviso automático de importación (SE)."];
    } else if (cap === "08") {
        return ["Certificado Fitosanitario de Importación (SENASICA).", "Inspección ocular en punto de entrada."];
    } else if (cap === "96") {
        return ["Aviso automático de importación ante la Secretaría de Economía (SE)."];
    }
    return ["Sin RRNAs críticas detectadas en el punto de entrada."];
}

// Simular el clasificador local de RGI 3b para desambiguación interactiva
function applyLocalExpertRules(description, results) {
    const descLower = description.toLowerCase();
    
    // Diccionario de ambigüedad
    const AMBIGUOUS_MAP = {
        "pluma": {
            question: "El término 'pluma' es ambiguo en la LIGIE. Por favor, seleccione la naturaleza de su mercancía:",
            choices: [
                "Bolígrafo / pluma de plástico para escritura en oficina",
                "Café tipo Pluma Hidalgo (cosechado en México)",
                "Plumas de ave naturales para adorno u ornamento"
            ]
        },
        "bateria": {
            question: "El término 'batería' es ambiguo en la LIGIE. Por favor, seleccione la naturaleza de su mercancía:",
            choices: [
                "Batería recargable de iones de litio (acumulador eléctrico)",
                "Batería de cocina de acero inoxidable (utensilio)",
                "Batería musical de percusión (instrumento)"
            ]
        },
        "batería": {
            question: "El término 'batería' es ambiguo en la LIGIE. Por favor, seleccione la naturaleza de su mercancía:",
            choices: [
                "Batería recargable de iones de litio (acumulador eléctrico)",
                "Batería de cocina de acero inoxidable (utensilio)",
                "Batería musical de percusión (instrumento)"
            ]
        },
        "valvula": {
            question: "El término 'válvula' es ambiguo en la LIGIE. Por favor, seleccione la naturaleza de su mercancía:",
            choices: [
                "Válvula de acero de compuerta para control de fluidos",
                "Válvula cardíaca de reemplazo (dispositivo médico/prótesis)"
            ]
        },
        "válvula": {
            question: "El término 'válvula' es ambiguo en la LIGIE. Por favor, seleccione la naturaleza de su mercancía:",
            choices: [
                "Válvula de acero de compuerta para control de fluidos",
                "Válvula cardíaca de reemplazo (dispositivo médico/prótesis)"
            ]
        }
    };

    const words = descLower.split(/\s+/).map(w => w.replace(/[,.!?]/g, ''));
    for (const [kw, data] of Object.entries(AMBIGUOUS_MAP)) {
        if (words.includes(kw) && words.length <= 3) {
            // Verificar si el usuario ya ingresó alguna opción
            const hasChoice = data.choices.some(c => descLower.includes(c.toLowerCase().slice(0, 15)));
            if (!hasChoice) {
                return {
                    status: 'clarification_needed',
                    hs_code: '',
                    confidence: 0.4,
                    reasoning: 'Se ha detectado ambigüedad o homonimia merciológica en el término ingresado. El Clasificador requiere resolver la naturaleza del producto.',
                    questions: [data.question],
                    choices: data.choices,
                    method: 'local_expert'
                };
            }
        }
    }

    // Regla de priorización por función (RGI 3b)
    const FUNCTIONAL_MAP = {
        "96": ["boligrafo", "bolígrafo", "pluma", "lapicero", "boligrafos", "lapiceros"],
        "90": ["protesis", "prótesis", "medico", "médico", "quirurgico", "quirúrgico", "articular"],
        "84": ["valvula", "válvula", "bomba", "motor", "engranaje", "compresor"],
        "85": ["interruptor", "conector", "bateria", "batería", "capacitor", "supercapacitor"]
    };

    let targetChapters = [];
    for (const [ch, keywords] of Object.entries(FUNCTIONAL_MAP)) {
        if (keywords.some(k => descLower.includes(k))) {
            targetChapters.push(ch);
        }
    }

    if (targetChapters.length > 0 && results.length > 0) {
        const functionalResults = results.filter(r => targetChapters.includes(r.chapter_code));
        const materialResults = results.filter(r => ['39', '73', '74', '75', '76', '81'].includes(r.chapter_code));

        if (functionalResults.length > 0) {
            const topFunc = functionalResults[0];
            const idx = results.indexOf(topFunc);
            if (idx > -1) results.splice(idx, 1);
            results.unshift(topFunc); // Promover al principio

            if (materialResults.length > 0) {
                const topMat = materialResults[0];
                return {
                    status: 'complete',
                    hs_code: topFunc.code,
                    confidence: 0.9,
                    reasoning: `<b>Función detectada:</b> Capítulo ${topFunc.chapter_code} (${topFunc.title}). <br><b>RGI 3b:</b> La función especializada prima sobre la materia constitutiva (Capítulo ${topMat.chapter_code}).`,
                    alternatives: results.slice(1, 5).map(r => ({code: r.code, title: r.title, score: r.score})),
                    questions: [],
                    choices: [],
                    method: 'local_expert'
                };
            }
        }
    }

    return null;
}

// Clasificación usando la API de Gemini desde el navegador
async function classifyWithGeminiDirect(apiKey, description, history = []) {
    const localResults = await performLocalSearch(description);
    const hsContext = localResults.slice(0, 10).map(r => `${r.code}: ${r.title} (Score: ${r.score})`).join("\n");

    let historyText = "";
    if (history && history.length > 0) {
        historyText = history.map(m => `${m.sender === 'user' ? 'Usuario' : 'Asistente'}: ${m.content}`).join("\n");
    }

    const prompt = `Eres un clasificador arancelario experto en la LIGIE (Ley de los Impuestos Generales de Importación y de Exportación de México) y el Sistema Armonizado.
Dada la siguiente descripción de mercancía, determina el código arancelario (HS Code a 6 o 8 dígitos) más apropiado.

IMPORTANTE: Si la descripción es ambigua, vaga o carece de detalles técnicos críticos (como el material, uso, potencia, composición) para clasificar con un nivel de confianza >= 0.8, debes marcar "status": "clarification_needed" y formular de 3 a 5 preguntas clave específicas o de aclaración progresiva de forma secuencial en el campo "questions" para que el usuario aclare el producto y poder dar una fracción exacta. También puedes proporcionar opciones rápidas en el campo "choices" (una lista de strings con opciones que resuelvan la ambigüedad) si consideras que facilitan al usuario la aclaración directa.

Mercancía actual a clasificar: ${description}

Historial de aclaraciones y conversación previa con el usuario:
${historyText || "No hay historial previo."}

Candidatos arancelarios locales sugeridos:
${hsContext}

Tu respuesta DEBE ser únicamente un objeto JSON válido con el siguiente formato:
{
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
}

INSTRUCCIONES CLAVE PARA EL CAMPO "reasoning":
1. Debe contener HTML válido, con estilos en línea (inline-styles) limpios e integrados, diseñado para pantallas oscuras/modernas (fondos semitransparentes oscuros como rgba(30, 41, 59, 0.5), bordes finos, fuentes legibles como system-ui, colores acentuados elegantes como el azul cielo/cian #38bdf8).
2. Estructura el mapa merciológico en las siguientes secciones visuales claramente definidas:
   - "1. Naturaleza de la mercancía": Identificación comercial y técnica de qué tipo de bien es.
   - "2. Materia constitutiva": Análisis de qué materiales o componentes la constituyen y su relevancia para la clasificación arancelaria.
   - "3. Función y uso": Propósito, aplicación y mecanismo de acción del producto.
   - "4. Presentación": Estado, empaque, ensamblaje o acondicionamiento de la mercancía.
3. Agrega un bloque de "Justificación Legal y Reglas de Interpretación (RGI)":
   - Sección y Capítulo aplicable de la LIGIE con su título.
   - Partida y Subpartida con justificación legal explícita.
   - Reglas Generales de Interpretación (RGI) específicas aplicadas (por ejemplo: RGI 1, RGI 2a, RGI 3b, RGI 6) detallando por qué se seleccionaron.`;

    try {
        const res = await window.realFetch(`https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=${apiKey}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                contents: [{
                    parts: [{
                        text: prompt
                    }]
                }],
                generationConfig: {
                    responseMimeType: 'application/json',
                    temperature: 0.1
                }
            })
        });

        if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);

        const data = await res.json();
        const jsonText = data.candidates[0].content.parts[0].text;
        const result = JSON.parse(jsonText);

        const cleanCode = (result.hs_code || '').replace(/\./g, '').trim();
        return {
            status: result.status || 'complete',
            hs_code: cleanCode,
            confidence: parseFloat(result.confidence || 0.8),
            reasoning: result.reasoning || 'Clasificado mediante Google Gemini en el cliente.',
            questions: result.questions || [],
            choices: result.choices || [],
            method: 'gemini_direct',
            taxes: getMockTaxes(cleanCode),
            rrnas: getMockRRNAs(cleanCode)
        };
    } catch (e) {
        console.error("Error en clasificación Gemini directa:", e);
        // Fallback inmediato a motor local
        return null;
    }
}

// INTERCEPTAR TODAS LAS SOLICITUDES FETCH DE LA API
window.fetch = async function(url, options = {}) {
    const urlStr = url.toString();

    // Si no es una llamada a la API local, dejar que pase a la red de forma normal
    if (!urlStr.startsWith('/api/')) {
        return window.realFetch(url, options);
    }

    console.log(`[MOCK API] Interceptado: ${urlStr} [Metodo: ${options.method || 'GET'}]`);

    // Parsear el body si existe
    let bodyData = null;
    if (options.body) {
        try {
            bodyData = JSON.parse(options.body);
        } catch (e) {}
    }

    let responseData = null;
    let status = 200;

    // --- ENRUTAMIENTO DE ENDPOINTS MOCKEADOS ---

    // 1. Estadísticas de Base de Datos
    if (urlStr.startsWith('/api/database/stats')) {
        const clients = JSON.parse(localStorage.getItem('crm_clients') || '[]');
        const items = JSON.parse(localStorage.getItem('erp_inventory') || '[]');
        const classifications = JSON.parse(localStorage.getItem('classifications') || '[]');
        const cartas = JSON.parse(localStorage.getItem('cartaporte_list') || '[]');
        responseData = {
            sections: 21,
            chapters: 97,
            headings: 1220,
            subheadings: 5410,
            classifications: classifications.length,
            clients: clients.length,
            inventory: items.length,
            cartas: cartas.length
        };
    }

    // 2. CRM Clientes (GET, POST, DELETE)
    else if (urlStr.startsWith('/api/crm/clients')) {
        const clients = JSON.parse(localStorage.getItem('crm_clients') || '[]');
        
        if (options.method === 'POST') {
            const data = bodyData;
            const newClient = {
                id: Date.now(),
                rfc: data.rfc.toUpperCase().trim(),
                name: data.name.trim(),
                patent: data.patent || '0000',
                agent: data.agent || '',
                status: data.status || 'Activo',
                created_at: new Date().toISOString()
            };
            clients.unshift(newClient);
            localStorage.setItem('crm_clients', JSON.stringify(clients));
            addAuditLog("Cliente creado", "CRM", `Cliente: ${newClient.name} (${newClient.rfc}), Patente: ${newClient.patent}`);
            responseData = { id: newClient.id, status: 'ok' };
        } 
        else if (options.method === 'DELETE') {
            const id = parseInt(urlStr.split('/').pop());
            const client = clients.find(c => c.id === id);
            const filtered = clients.filter(c => c.id !== id);
            localStorage.setItem('crm_clients', JSON.stringify(filtered));
            if (client) {
                addAuditLog("Cliente eliminado", "CRM", `Cliente: ${client.name} (${client.rfc})`);
            }
            responseData = { status: 'ok' };
        } 
        else {
            responseData = clients;
        }
    }

    // 3. ERP Inventario (GET, POST, DELETE)
    else if (urlStr.startsWith('/api/erp/inventory')) {
        const items = JSON.parse(localStorage.getItem('erp_inventory') || '[]');

        if (options.method === 'POST') {
            const data = bodyData;
            const newItem = {
                id: Date.now(),
                sku: data.sku.toUpperCase().trim(),
                description: data.description.trim(),
                sat_code: data.sat_code.trim(),
                unit: data.unit || 'H87',
                quantity: parseFloat(data.quantity || 0),
                price: parseFloat(data.price || 0),
                created_at: new Date().toISOString()
            };
            items.unshift(newItem);
            localStorage.setItem('erp_inventory', JSON.stringify(items));
            addAuditLog("Artículo de inventario creado", "ERP", `SKU: ${newItem.sku}, Cantidad: ${newItem.quantity}, Código SAT: ${newItem.sat_code}`);
            responseData = { id: newItem.id, status: 'ok' };
        } 
        else if (options.method === 'DELETE') {
            const id = parseInt(urlStr.split('/').pop());
            const item = items.find(i => i.id === id);
            const filtered = items.filter(i => i.id !== id);
            localStorage.setItem('erp_inventory', JSON.stringify(filtered));
            if (item) {
                addAuditLog("Artículo de inventario eliminado", "ERP", `SKU: ${item.sku}`);
            }
            responseData = { status: 'ok' };
        } 
        else {
            responseData = items;
        }
    }

    // 4. Bitácora de Auditoría
    else if (urlStr.startsWith('/api/admin/audit')) {
        responseData = JSON.parse(localStorage.getItem('audit_logs') || '[]');
    }

    // 5. Bóveda de Secretos
    else if (urlStr.startsWith('/api/admin/vault')) {
        if (options.method === 'POST') {
            const data = bodyData;
            addAuditLog("Llave cargada a la Bóveda", "ADMIN", `Se cargó la llave privada/certificado: ${data.name}`);
            responseData = { status: 'ok' };
        } else {
            addAuditLog("Acceso a Bóveda de Secretos", "ADMIN", "Verificación del estado de llaves y certificados en Local Vault.");
            responseData = { keys: [{ id: 1, name: 'e.firma - ALINEA SOLUTIONS', status: 'Válido' }] };
        }
    }

    // 6. VUCEM Acuses y Validación
    else if (urlStr.startsWith('/api/vucem/acuses')) {
        responseData = JSON.parse(localStorage.getItem('vucem_acuses') || '[]');
    } 
    else if (urlStr.startsWith('/api/vucem/validate')) {
        const data = bodyData;
        const acuses = JSON.parse(localStorage.getItem('vucem_acuses') || '[]');
        const newAcuse = {
            id: Date.now(),
            folio: data.folio || `E2E-COVE-${Math.floor(Math.random() * 900000 + 100000)}`,
            type: data.type || 'COVE',
            rfc_importador: data.rfc_importador || 'SOL890412AA1',
            status: 'Validado',
            error_details: null,
            created_at: new Date().toISOString()
        };
        acuses.unshift(newAcuse);
        localStorage.setItem('vucem_acuses', JSON.stringify(acuses));
        addAuditLog("Transmisión a VUCEM iniciada", "VUCEM", `Se envió el documento ${newAcuse.type} con folio ${newAcuse.folio} para validación.`);
        addAuditLog("Acuse validado en VUCEM", "VUCEM", `Folio ${newAcuse.folio} (${newAcuse.type}) validado correctamente ante el SAT.`);
        responseData = { status: 'ok', folio: newAcuse.folio };
    }

    // 7. Carta Porte (Listado y Timbrado)
    else if (urlStr.startsWith('/api/cartaporte/list')) {
        responseData = JSON.parse(localStorage.getItem('cartaporte_list') || '[]');
    }
    else if (urlStr.startsWith('/api/cartaporte/generate')) {
        const data = bodyData;
        const cpList = JSON.parse(localStorage.getItem('cartaporte_list') || '[]');
        const newCP = {
            id: Date.now(),
            folio: `CP-${Math.floor(Math.random() * 90000000 + 10000000).toString(16).toUpperCase()}`,
            origin: data.origin,
            destination: data.destination,
            goods_desc: data.goods_desc,
            sat_code: data.sat_code,
            sat_unit: data.sat_unit,
            vehicle_config: data.vehicle_config,
            status: 'Timbrado',
            created_at: new Date().toISOString()
        };
        cpList.unshift(newCP);
        localStorage.setItem('cartaporte_list', JSON.stringify(cpList));

        // Descontar inventario localmente
        const items = JSON.parse(localStorage.getItem('erp_inventory') || '[]');
        const targetItem = items.find(i => i.sat_code === data.sat_code);
        if (targetItem) {
            targetItem.quantity = Math.max(0, targetItem.quantity - 1);
            localStorage.setItem('erp_inventory', JSON.stringify(items));
            addAuditLog("Descuento por Carta Porte", "ERP", `Descuento automático de 1 unidades del SKU ${targetItem.sku} debido a emisión de Carta Porte.`);
        }

        addAuditLog("Carta Porte 3.1 Timbrada", "CARTA_PORTE", `Complemento Carta Porte emitido con folio ${newCP.folio}. Timbrado PAC exitoso.`);
        responseData = { status: 'ok', folio: newCP.folio };
    }

    // 8. Manifestación de Valor (MVE)
    else if (urlStr.startsWith('/api/mve/list')) {
        responseData = JSON.parse(localStorage.getItem('mve_list') || '[]');
    }
    else if (urlStr.startsWith('/api/mve/save')) {
        const data = bodyData;
        const mveList = JSON.parse(localStorage.getItem('mve_list') || '[]');
        const newMVE = {
            id: Date.now(),
            folio: data.folio || `E2E-MVE-${Math.floor(Math.random() * 900000 + 100000)}`,
            rfc_importador: data.rfcFirmante || 'SOL890412AA1',
            razon_social: data.firmante || 'IMPORTADOR ALINEA',
            metodo_valoracion: data.metodoValoracion || 'Valor de Transacción',
            valor_comercial: parseFloat(data.valorComercial || 0),
            total_incrementables: parseFloat(data.totalIncrementables || 0),
            valor_aduana_mxn: parseFloat(data.valorAduanaMXN || 0),
            status: 'Emitida'
        };
        mveList.unshift(newMVE);
        localStorage.setItem('mve_list', JSON.stringify(mveList));
        addAuditLog("Emisión de Manifestación de Valor", "MVE", `Se emitió exitosamente la MVE con folio ${newMVE.folio} para el importador ${newMVE.rfc_importador} (Total: $${newMVE.valor_aduana_mxn.toLocaleString()} MXN)`);
        responseData = { status: 'ok', folio: newMVE.folio };
    }

    // 9. Búsqueda y Clasificación Local
    else if (urlStr.startsWith('/api/search')) {
        const query = new URL(`http://localhost${urlStr}`).searchParams.get('q') || '';
        const results = await performLocalSearch(query);
        responseData = { results: results };
    }
    else if (urlStr.startsWith('/api/tree')) {
        await ensureCatalogLoaded();
        // Generar un árbol simple con las secciones
        responseData = cachedHsCatalog.sections.map(s => ({
            id: s.code,
            code: s.code,
            title: s.title,
            children: s.chapters.map(c => ({
                id: c.code,
                code: c.code,
                title: c.title,
                children: c.headings.map(h => ({
                    id: h.code,
                    code: h.code,
                    title: h.title,
                    children: h.subheadings.map(sub => ({
                        id: sub.code,
                        code: sub.code,
                        title: sub.title
                    }))
                }))
            }))
        }));
    }
    else if (urlStr.startsWith('/api/hs_code/')) {
        const code = urlStr.split('/').pop().replace(/\./g, '');
        await ensureCatalogLoaded();
        
        let foundDetails = null;

        // Buscar en el catálogo en caché
        for (const sec of cachedHsCatalog.sections) {
            for (const ch of sec.chapters) {
                if (ch.code === code) {
                    foundDetails = { chapter: { code: ch.code, title: ch.title }, section: { code: sec.code, title: sec.title } };
                    break;
                }
                for (const h of ch.headings) {
                    if (h.code === code) {
                        foundDetails = { heading: { code: h.code, title: h.title }, chapter: { code: ch.code, title: ch.title }, section: { code: sec.code, title: sec.title } };
                        break;
                    }
                    for (const sub of h.subheadings) {
                        if (sub.code === code) {
                            foundDetails = { subheading: { code: sub.code, title: sub.title, description: sub.description }, heading: { code: h.code, title: h.title }, chapter: { code: ch.code, title: ch.title }, section: { code: sec.code, title: sec.title } };
                            break;
                        }
                    }
                }
            }
        }

        // Si no se encuentra en el árbol, buscar si es una fracción en descriptions
        if (!foundDetails && cachedNicoDescriptions.by_8digit[code]) {
            foundDetails = {
                subheading: { code: code, title: cachedNicoDescriptions.by_8digit[code], description: "Fracción Arancelaria (NICO)" }
            };
        }

        if (foundDetails) {
            responseData = foundDetails;
        } else {
            status = 404;
            responseData = { error: 'No encontrado' };
        }
    }

    // 10. Reglas Generales de Interpretación (RGI)
    else if (urlStr.startsWith('/api/rgi/rules')) {
        responseData = {
            rules: [
                {rule_number: 1, title: "Títulos de Secciones/Capítulos indicativos", content: "Los títulos de las Secciones, de los Capítulos o de los Subcapítulos solo tienen un valor indicativo..."},
                {rule_number: 2, title: "Artículos incompletos o mezclados", content: "Cualquier referencia a un artículo en una partida comprende también al artículo incompleto o sin terminar..."},
                {rule_number: 3, title: "Mercancías clasificables en dos o más partidas", content: "a) La partida más específica... b) Carácter esencial... c) Último orden..."},
                {rule_number: 4, title: "Clasificación por analogía", content: "Las mercancías que no puedan clasificarse aplicando las reglas anteriores se clasifican en la partida con mayor analogía..."},
                {rule_number: 5, title: "Estuches y continentes", content: "Los estuches y continentes diseñados para contener un artículo se clasifican con él..."},
                {rule_number: 6, title: "Clasificación a nivel subpartida", content: "La clasificación en subpartidas está determinada por los textos de las subpartidas y Notas..."}
            ]
        };
    }
    else if (urlStr.startsWith('/api/rgi/apply')) {
        const desc = bodyData.description;
        responseData = {
            suggestions: [
                `RGI 1: Comprobar partidas específicas para '${desc}'.`,
                `RGI 2: ¿Presenta las características esenciales del artículo terminado?`,
                `RGI 3: Elegir partida por carácter esencial o especificidad técnica.`,
                `RGI 4: Analizar la mercancía por analogía.`,
                `RGI 5: Validar si cuenta con envases reutilizables.`,
                `RGI 6: Clasificar a nivel de subpartida (6-8 dígitos).`
            ]
        };
    }

    // 11. Saved Classifications
    else if (urlStr.startsWith('/api/classifications')) {
        const classifications = JSON.parse(localStorage.getItem('classifications') || '[]');

        if (options.method === 'POST') {
            const data = bodyData;
            const newClassification = {
                id: Date.now(),
                product_description: data.product_description,
                hs_code: data.hs_code,
                confidence: data.confidence || 0.9,
                method: data.method || 'local_expert',
                notes: data.notes || '',
                created_at: new Date().toISOString()
            };
            classifications.unshift(newClassification);
            localStorage.setItem('classifications', JSON.stringify(classifications));
            addAuditLog("Clasificación de Mercancía (IA)", "CLASSIFIER", `Búsqueda técnica de: ${newClassification.product_description} [Imagen: False]`);
            responseData = { id: newClassification.id, status: 'ok' };
        } 
        else if (options.method === 'DELETE') {
            const id = parseInt(urlStr.split('/').pop());
            const filtered = classifications.filter(c => c.id !== id);
            localStorage.setItem('classifications', JSON.stringify(filtered));
            responseData = { status: 'ok' };
        } 
        else {
            responseData = classifications;
        }
    }

    // 12. Validar descripción Anexo 22
    else if (urlStr.startsWith('/api/vucem/description/validate')) {
        const data = bodyData;
        const result = validateDescriptionLocal(data.description);
        addAuditLog("Validación Descripción Anexo 22", "VUCEM", `Texto: ${data.description.slice(0, 40)}..., Score: ${result.score}, Cumple: ${result.is_compliant}`);
        responseData = result;
    }

    // 13. Clasificación Masiva (Por lotes)
    else if (urlStr.startsWith('/api/classify/batch')) {
        const data = bodyData; // { descriptions: [...] }
        const results = [];
        for (const desc of data.descriptions) {
            const localRes = await performLocalSearch(desc);
            if (localRes.length > 0) {
                results.push({
                    description: desc,
                    hs_code: localRes[0].code,
                    confidence: 0.85,
                    reasoning: `Clasificación local en lote: ${localRes[0].title}`
                });
            } else {
                results.push({
                    description: desc,
                    hs_code: '',
                    confidence: 0.0,
                    reasoning: 'No se encontraron coincidencias locales.'
                });
            }
        }
        addAuditLog("Clasificación Masiva por Lotes", "CLASSIFIER", `Procesadas ${data.descriptions.length} descripciones en lote.`);
        responseData = { results: results };
    }

    // 14. Clasificador con IA (Chat / Individual)
    else if (urlStr.startsWith('/api/chat/start')) {
        responseData = { thread_id: Date.now() };
    }
    else if (urlStr.startsWith('/api/chat/send') || urlStr.startsWith('/api/classify/extended') || urlStr.startsWith('/api/classify')) {
        const data = bodyData || {};
        const description = data.description || data.message || '';
        const history = data.history || [];

        const localResults = await performLocalSearch(description);
        
        // Evaluar reglas del sistema experto merciológico local (RGI 3b y ambigüedades)
        let finalResult = applyLocalExpertRules(description, localResults);

        if (!finalResult) {
            // Si el experto no determinó una desambiguación, procedemos a Gemini si hay API key
            const apiKey = localStorage.getItem('gemini_api_key');
            if (apiKey) {
                console.log("[MOCK API] Realizando clasificación real con Gemini...");
                const geminiRes = await classifyWithGeminiDirect(apiKey, description, history);
                if (geminiRes) {
                    finalResult = geminiRes;
                }
            }
        }

        // Si no se usó Gemini o falló, usar clasificación local estándar
        if (!finalResult) {
            console.log("[MOCK API] Realizando clasificación léxica local fallback...");
            if (localResults.length > 0) {
                const top = localResults[0];
                const taxes = getMockTaxes(top.code);
                const rrnas = getMockRRNAs(top.code);

                const reasoningHtml = `
                    <div class="merceology-map" style="background: rgba(30, 41, 59, 0.45); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 8px; padding: 16px; margin-top: 12px; color: #f1f5f9; font-family: system-ui, -apple-system, sans-serif;">
                        <h4 style="margin-top: 0; margin-bottom: 12px; color: #38bdf8; display: flex; align-items: center; gap: 8px; font-size: 15px; border-bottom: 1px solid rgba(255, 255, 255, 0.15); padding-bottom: 8px;">
                            <span>📋</span> MAPA DE RAZONAMIENTO LÉXICO ESTÁTICO (OFFLINE)
                        </h4>
                        <div style="background: rgba(15, 23, 42, 0.4); border: 1px solid rgba(255, 255, 255, 0.05); border-radius: 6px; padding: 12px; font-size: 13px; line-height: 1.5;">
                            <div style="margin-bottom: 6px;"><strong>Coincidencia Sugerida:</strong> <span style="color: #38bdf8; font-family: monospace; font-weight: bold;">${top.code}</span> - ${top.title}</div>
                            <div style="margin-bottom: 6px;"><strong>Confianza:</strong> ${Math.round(Math.min(0.95, top.score / 60) * 100)}%</div>
                            <div style="margin-top: 8px; border-top: 1px solid rgba(255, 255, 255, 0.08); padding-top: 8px; color: #94a3b8; font-size: 12px;">
                                Clasificación realizada de manera local (offline) basada en similitud de términos del catálogo arancelario. Conforme a la <strong>RGI 1</strong>, la partida está determinada por los textos de las subpartidas.
                            </div>
                        </div>
                    </div>
                `;

                finalResult = {
                    status: 'complete',
                    hs_code: top.code,
                    confidence: Math.min(0.95, top.score / 60),
                    reasoning: reasoningHtml,
                    alternatives: localResults.slice(1, 5).map(r => ({code: r.code, title: r.title, score: r.score})),
                    questions: [],
                    choices: [],
                    method: 'local_offline',
                    taxes: taxes,
                    rrnas: rrnas
                };
            } else {
                finalResult = {
                    status: 'complete',
                    hs_code: '',
                    confidence: 0.0,
                    reasoning: 'No se encontraron candidatos arancelarios en el catálogo local offline.',
                    alternatives: [],
                    questions: [],
                    choices: [],
                    method: 'local_offline'
                };
            }
        }

        // Registrar en auditoría
        addAuditLog("Clasificación de Mercancía (IA)", "CLASSIFIER", `Búsqueda técnica de: ${description.slice(0, 45)}... [Modo: ${finalResult.method}]`);
        responseData = finalResult;
    }

    // 15. Estatus de Sincronización y Fuentes Oficiales
    else if (urlStr.startsWith('/api/sources/status')) {
        responseData = {
            sources: [
                { name: 'SNICE (México)', status: 'Online', last_sync: new Date().toLocaleDateString() },
                { name: 'TARIC (Unión Europea)', status: 'Online', last_sync: new Date().toLocaleDateString() }
            ]
        };
    }
    else if (urlStr.startsWith('/api/sources/sync')) {
        addAuditLog("Sincronización de Fuentes", "CLASSIFIER", "Se inició sincronización con base de datos del SNICE.");
        responseData = { status: 'ok', added_records: 15 };
    }
    else if (urlStr.startsWith('/api/sources/verify')) {
        responseData = { verified: true, source: 'SNICE', notes: 'Fracción arancelaria vigente en la LIGIE 2026.' };
    }
    else if (urlStr.startsWith('/api/sources/search')) {
        responseData = { results: [] };
    }

    // --- RESPUESTA EN MOCK RESPONSE ---
    const mockResponse = new Response(JSON.stringify(responseData), {
        status: status,
        headers: { 'Content-Type': 'application/json' }
    });

    return mockResponse;
};
