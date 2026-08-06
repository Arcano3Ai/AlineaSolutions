# Clasificador Arancelario Experto Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implementar un sistema de clasificación arancelaria con búsqueda RAG (semántica) sobre leyes y búsqueda estructurada en la TIGIE/NICOs, con una UI moderna en React y Backend en FastAPI (Puerto 4001).

**Architecture:** Servidor FastAPI para procesamiento de datos (Pandas + ChromaDB) y Cliente React (Vite) para la interfaz híbrida de búsqueda y diagnóstico.

**Tech Stack:** Python (FastAPI, Pandas, LangChain, ChromaDB, PyMuPDF), TypeScript (React, Vite).

---

## File Structure

### Backend (`server/`)
- `server/main.py`: Punto de entrada FastAPI (Puerto 4001).
- `server/engine/rag.py`: Lógica de indexación y búsqueda semántica (ChromaDB).
- `server/engine/tarifa.py`: Lógica de búsqueda en Excels (Pandas).
- `server/models.py`: Esquemas de datos Pydantic.

### Frontend (`client/`)
- `client/src/App.tsx`: Layout principal (Sidebar + Main Area).
- `client/src/components/SearchArea.tsx`: Buscador con sugerencias.
- `client/src/components/DiagnosisPanel.tsx`: Componente de lógica RGI.
- `client/src/components/LegalPanel.tsx`: Panel lateral con sustento legal.

---

## Tasks

### Task 1: Backend Environment & Scaffold

**Files:**
- Create: `server/requirements.txt`
- Create: `server/main.py`
- Test: `server/tests/test_health.py`

- [ ] **Step 1: Crear `requirements.txt`**
```text
fastapi
uvicorn
pandas
openpyxl
langchain
chromadb
pymupdf
sentence-transformers
pydantic
```

- [ ] **Step 2: Crear el servidor base en `server/main.py`**
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Clasificador Experto API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health():
    return {"status": "ok", "port": 4001}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=4001)
```

- [ ] **Step 3: Verificar salud del servidor**
Run: `python -m uvicorn server.main:app --port 4001` y en otra terminal `curl http://localhost:4001/health`
Expected: `{"status": "ok", "port": 4001}`

### Task 2: RAG Engine (Indexación de Leyes)

**Files:**
- Create: `server/engine/rag.py`
- Modify: `server/main.py`

- [ ] **Step 1: Implementar `server/engine/rag.py`**
```python
import fitz # PyMuPDF
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings

class RAGEngine:
    def __init__(self):
        self.embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        self.vector_db = None
        
    def index_pdf(self, pdf_path):
        doc = fitz.open(pdf_path)
        text = ""
        for page in doc:
            text += page.get_text()
        
        splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
        chunks = splitter.split_text(text)
        self.vector_db = Chroma.from_texts(chunks, self.embeddings, persist_directory="./chroma_db")
        
    def search(self, query):
        if not self.vector_db: return []
        return self.vector_db.similarity_search(query, k=3)

rag_engine = RAGEngine()
```

- [ ] **Step 2: Integrar indexación en el arranque (ej: Ley Aduanera 2026)**
```python
# En server/main.py
from server.engine.rag import rag_engine
import os

@app.on_event("startup")
async def startup_event():
    pdf_path = "conocimiento_clasificador_experto/normativa/Ley_Aduanera_2026.pdf"
    if os.path.exists(pdf_path):
        rag_engine.index_pdf(pdf_path)
```

### Task 3: Tarifa Engine (Búsqueda en Excel)

**Files:**
- Create: `server/engine/tarifa.py`

- [ ] **Step 1: Implementar búsqueda en `NICO_2024_Alt.xlsx`**
```python
import pandas as pd
import os

class TarifaEngine:
    def __init__(self):
        self.df = None
        path = "conocimiento_clasificador_experto/tarifas_y_nicos/NICO_2024_Alt.xlsx"
        if os.path.exists(path):
            self.df = pd.read_excel(path)
            
    def query_nico(self, term):
        if self.df is None: return []
        # Búsqueda simple por palabra en descripción
        results = self.df[self.df['descripcion'].str.contains(term, case=False, na=False)]
        return results.head(5).to_dict('records')

tarifa_engine = TarifaEngine()
```

### Task 4: UI Scaffold (React)

**Files:**
- Create: `client/` via Vite

- [ ] **Step 1: Scaffold con Vite**
Run: `npm create vite@latest client -- --template react-ts`
Run: `cd client && npm install`

- [ ] **Step 2: Estilo Base en `client/src/App.css`**
```css
:root { --bg: #1a1a1a; --text: #e0e0e0; --accent: #3498db; }
body { background: var(--bg); color: var(--text); font-family: sans-serif; }
.app-container { display: flex; height: 100vh; }
.sidebar { width: 250px; border-right: 1px solid #333; padding: 20px; }
.main { flex: 1; padding: 40px; }
.legal-panel { width: 300px; border-left: 1px solid #333; padding: 20px; }
```

### Task 5: Integración Final (Búsqueda Híbrida)

- [ ] **Step 1: Endpoint `/api/expert-search` en Backend**
- [ ] **Step 2: Componente de búsqueda en Frontend conectando al 4001**

---
*Plan verificado bajo estándares Arcano Solutions.*
