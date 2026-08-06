import os, sys, glob, json
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

VUCEM_DIR = r"C:\Users\sergi\vucem_rag_knowledge"
DB_DIR = os.path.join(os.path.dirname(__file__), "..", "conocimiento", "vucem_knowledge_db")
os.makedirs(DB_DIR, exist_ok=True)

INDEX_LOG = os.path.join(DB_DIR, "indexed_files.json")
indexed = set(json.load(open(INDEX_LOG))) if os.path.exists(INDEX_LOG) else set()

def extract_text(pdf_path):
    import fitz
    doc = fitz.open(pdf_path)
    text = "".join(page.get_text() for page in doc)
    doc.close()
    return text

def index_one(pdf_path):
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    from langchain_community.vectorstores import Chroma
    from langchain_huggingface import HuggingFaceEmbeddings

    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)
    
    db = Chroma(persist_directory=DB_DIR, embedding_function=embeddings) if os.path.exists(os.path.join(DB_DIR, "chroma.sqlite3")) else None

    text = extract_text(pdf_path).strip()
    if len(text) < 50:
        return 0
    chunks = splitter.split_text(text)
    metadatas = [{"source": os.path.relpath(pdf_path, VUCEM_DIR)} for _ in chunks]
    
    if db:
        db.add_texts(texts=chunks, metadatas=metadatas)
    else:
        db = Chroma.from_texts(texts=chunks, embedding=embeddings, metadatas=metadatas, persist_directory=DB_DIR)
    return len(chunks)

# Priority: index the most important legal docs for tariff classification
priority = [
    r"Marco_Legal\Reglamento de la Ley Aduanera.pdf",
    r"Marco_Legal\Reglamento de la Ley de Comercio Exterior.pdf",
    r"Marco_Legal\RGCE_2024.pdf",
    r"Marco_Legal\Anexo_22_RGCE_2024.pdf",
    r"Marco_Legal\LEY de Comercio Exterior.pdf",
    r"Marco_Legal\LEY de los Impuestos Generales de Importacion y de Exportacion.pdf",
    r"Marco_Legal\LEY Aduanera.pdf",
    r"LAdua.pdf",
    r"LeyAduaneraVigenteVsReforma2025.pdf",
]

for rel in priority:
    pdf_path = os.path.join(VUCEM_DIR, rel)
    if not os.path.exists(pdf_path):
        print(f"  [MISS] {rel}")
        continue
    if rel in indexed:
        print(f"  [DONE] {rel}")
        continue
    try:
        n = index_one(pdf_path)
        indexed.add(rel)
        json.dump(sorted(indexed), open(INDEX_LOG, "w"))
        print(f"  [OK]   {rel} -> {n} chunks")
    except Exception as e:
        print(f"  [ERR]  {rel}: {e}")

print(f"\nTotal indexados: {len(indexed)}")
