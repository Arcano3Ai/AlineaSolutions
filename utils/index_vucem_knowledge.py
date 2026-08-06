import os, sys, glob, json
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

VUCEM_DIR = r"C:\Users\sergi\vucem_rag_knowledge"
DB_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "conocimiento", "vucem_knowledge_db")
os.makedirs(DB_DIR, exist_ok=True)

# Track which PDFs are already indexed
INDEX_LOG = os.path.join(DB_DIR, "indexed_files.json")
indexed = set()
if os.path.exists(INDEX_LOG):
    indexed = set(json.load(open(INDEX_LOG, "r")))

def extract_text(pdf_path):
    import fitz
    doc = fitz.open(pdf_path)
    text = "".join(page.get_text() for page in doc)
    doc.close()
    return text

def index_batch(pdf_files, batch_name):
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    from langchain_community.vectorstores import Chroma
    from langchain_huggingface import HuggingFaceEmbeddings

    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)
    
    # Load existing DB if any
    db = Chroma(persist_directory=DB_DIR, embedding_function=embeddings) if os.path.exists(os.path.join(DB_DIR, "chroma.sqlite3")) else None

    all_chunks = []
    all_metadatas = []
    
    for pdf_path in pdf_files:
        rel = os.path.relpath(pdf_path, VUCEM_DIR)
        if rel in indexed:
            print(f"  [SKIP] {rel} (ya indexado)")
            continue
        try:
            text = extract_text(pdf_path).strip()
            if len(text) < 50:
                print(f"  [SKIP] {rel} — muy poco texto")
                indexed.add(rel)
                continue
            chunks = splitter.split_text(text)
            for c in chunks:
                all_chunks.append(c)
                all_metadatas.append({"source": rel})
            indexed.add(rel)
            print(f"  [OK]   {rel} -> {len(chunks)} chunks")
        except Exception as e:
            print(f"  [ERR]  {rel}: {e}")

    if all_chunks:
        if db:
            db.add_texts(texts=all_chunks, metadatas=all_metadatas)
        else:
            db = Chroma.from_texts(texts=all_chunks, embedding=embeddings, metadatas=all_metadatas, persist_directory=DB_DIR)
        db.persist()
    
    json.dump(sorted(indexed), open(INDEX_LOG, "w"))
    print(f"\nBatch '{batch_name}' completo. Total indexados: {len(indexed)}")

# Find all PDFs
all_pdfs = glob.glob(os.path.join(VUCEM_DIR, "**", "*.pdf"), recursive=True)
print(f"Total PDFs: {len(all_pdfs)}, ya indexados: {len(indexed)}")

# Process in batches by directory
by_dir = {}
for p in all_pdfs:
    rel = os.path.relpath(p, VUCEM_DIR)
    d = os.path.dirname(rel) or "raiz"
    by_dir.setdefault(d, []).append(p)

for d, files in sorted(by_dir.items()):
    pending = [f for f in files if os.path.relpath(f, VUCEM_DIR) not in indexed]
    if not pending:
        print(f"\n[{d}] {len(files)} archivos, todos ya indexados")
        continue
    print(f"\n[{d}] {len(pending)}/{len(files)} pendientes")
    index_batch(pending, d)

print(f"\nIndexacion completa. Total: {len(indexed)} archivos")
