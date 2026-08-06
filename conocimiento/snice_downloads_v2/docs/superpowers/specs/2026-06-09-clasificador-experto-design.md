# Spec: Clasificador Arancelario Experto (RAG + Local)

**Estado:** Borrador / Pendiente de Aprobación
**Dueño:** Gemini CLI (Modo Pickle Rick)
**Puerto:** 4001 (Backend)

## 1. Objetivo
Crear una herramienta local de nivel experto que asista en la clasificación arancelaria de mercancías en México, integrando búsqueda semántica en leyes (RAG) y búsqueda estructurada en la TIGIE/NICOs.

## 2. Requisitos Funcionales
- **Buscador Semántico (Modo Experto):** Indexación de `Ley_Aduanera_2026.pdf` y `RGCE_2025.pdf` usando ChromaDB/FAISS.
- **Motor de NICOs:** Consulta de archivos Excel (`NICO_2024_Alt.xlsx`, correlaciones) para sugerir fracciones exactas.
- **Asistente de Diagnóstico:** Flujo basado en las 6 Reglas Generales Interpretativas (RGI) para resolver dudas de clasificación.
- **Visualizador de RRNA:** Mostrar NOMs y regulaciones no arancelarias asociadas a la fracción.

## 3. Arquitectura Técnica
- **Backend (Python/FastAPI):**
  - Puerto: 4001
  - Librerías: `fastapi`, `uvicorn`, `pandas`, `langchain`, `chromadb`, `pymupdf`.
  - Endpoint `/search`: Búsqueda híbrida (Semántica + Keywords).
  - Endpoint `/classify`: Motor de lógica RGI.
- **Frontend (React/TypeScript):**
  - Puerto: 5173 (Vite default)
  - UI: Vanilla CSS con estética "Industrial/Senior" (Dark mode por defecto).
  - Componentes: Sidebar de historial, Main Search, Diagnosis Panel, Legal Side-panel.

## 4. Estrategia de Datos
El sistema consumirá la carpeta `conocimiento_clasificador_experto/` ya organizada:
- Los PDFs se fragmentarán e indexarán en una DB vectorial local.
- Los Excels se cargarán en memoria vía DataFrames de Pandas para velocidad.

## 5. Próximos Pasos (Plan de Ejecución)
1.  **Server Setup:** Inicializar entorno Python y dependencias.
2.  **RAG Engine:** Script de indexación local de leyes.
3.  **API Endpoints:** Implementar lógica de búsqueda en Excels.
4.  **Frontend:** Scaffold de React y conexión con el API en 4001.

---
*Documento de diseño para el proyecto "Vive Libre".*
