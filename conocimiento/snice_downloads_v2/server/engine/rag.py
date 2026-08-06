import fitz # PyMuPDF
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
import os

class RAGEngine:
    def __init__(self):
        # Usamos un modelo ligero de embeddings local
        self.embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        self.vector_db = None
        self.db_path = "./chroma_db"
        
    def index_pdf(self, pdf_path: str):
        if not os.path.exists(pdf_path):
            print(f"Error: No se encontró el archivo {pdf_path}")
            return False
            
        print(f"Indexando normativa: {pdf_path}...")
        doc = fitz.open(pdf_path)
        text = ""
        for page in doc:
            text += page.get_text()
        
        # Dividir el texto en fragmentos manejables para la búsqueda semántica
        splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)
        chunks = splitter.split_text(text)
        
        # Crear base de datos vectorial local
        self.vector_db = Chroma.from_texts(
            texts=chunks, 
            embedding=self.embeddings, 
            persist_directory=self.db_path
        )
        print("Indexación completada con éxito.")
        return True
        
    def search(self, query: str):
        if not self.vector_db:
            # Intentar cargar DB existente si existe
            if os.path.exists(self.db_path):
                self.vector_db = Chroma(persist_directory=self.db_path, embedding_function=self.embeddings)
            else:
                return []
        
        results = self.vector_db.similarity_search(query, k=4)
        return [{"content": res.page_content, "metadata": res.metadata} for res in results]

rag_engine = RAGEngine()
