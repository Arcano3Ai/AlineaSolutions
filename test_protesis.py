import sys
sys.path.insert(0, r"C:\Users\sergi\MisArchivosLocales\Clasificador AI")
from database.models import init_db, get_session, Fraction
from classifiers.classifier import _score_terms, _tokenize, _normalize, _semantic_similarity, _get_embedding_model

session = get_session(init_db())

codes = ['90213101', '81082001']
query = (
    "Prótesis de Rodilla de Titanio. "
    "Dispositivo médico de reemplazo articular total de rodilla, constituido por componentes "
    "femorales y tibiales de aleación de titanio y cobalto-cromo, y un inserto de polietileno."
)
tokens = _tokenize(query)

print("Comparación de puntuaciones para la prótesis:")
for code in codes:
    f = session.query(Fraction).filter_by(code=code).first()
    if f:
        text = f"{f.title} | {f.description or ''}"
        score = _score_terms(tokens, text, f.code)
        sim = _semantic_similarity(query, [text])[0]
        sem_points = max(0.0, float(sim)) * 100.0
        combined = score * 0.50 + sem_points * 0.50
        print(f"\nCódigo {code}:")
        print(f"  Título: {f.title}")
        print(f"  Léxico Score: {score}")
        print(f"  Similitud Semántica: {sim:.4f}")
        print(f"  Score Combinado: {combined:.2f}")

session.close()
