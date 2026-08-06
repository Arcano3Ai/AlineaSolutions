from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from server.engine.rag import rag_engine
from server.engine.tarifa import tarifa_engine
import os

app = FastAPI(title="Clasificador Experto API - Modo RAG")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    # Indexar la Ley Aduanera al iniciar para tener el conocimiento listo
    pdf_path = "conocimiento_clasificador_experto/normativa/Ley_Aduanera_2026.pdf"
    if os.path.exists(pdf_path):
        rag_engine.index_pdf(pdf_path)

@app.get("/health")
async def health():
    return {"status": "ok", "port": 4001, "db_ready": rag_engine.vector_db is not None}

@app.get("/api/search")
async def expert_search(q: str = Query(..., min_length=3)):
    """
    Búsqueda híbrida:
    1. Semántica en Leyes (RAG)
    2. Estructurada en Tarifa (NICOs)
    """
    legal_results = rag_engine.search(q)
    tarifa_results = tarifa_engine.query_nico(q)
    
    return {
        "query": q,
        "legal_support": legal_results,
        "tarifa_suggestions": tarifa_results
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=4001)
