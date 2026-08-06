import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './App.css';

interface LegalSnippet {
  content: string;
  metadata: any;
}

interface TarifaSuggestion {
  fraccion?: string;
  nico?: string;
  descripcion?: string;
  [key: string]: any;
}

function App() {
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<{
    legal_support: LegalSnippet[];
    tarifa_suggestions: TarifaSuggestion[];
  } | null>(null);

  const handleSearch = async () => {
    if (query.length < 3) return;
    setLoading(true);
    try {
      const response = await axios.get(`http://localhost:4001/api/search?q=${query}`);
      setResults(response.data);
    } catch (error) {
      console.error("Error buscando:", error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app-container">
      {/* Sidebar */}
      <aside className="sidebar">
        <div className="logo-section">
          <h2>VIVE LIBRE</h2>
          <p>CLASIFICADOR EXPERTO</p>
        </div>
        <hr style={{ borderColor: '#333', marginBottom: '20px' }} />
        <div className="history-list">
          <p style={{ fontSize: '0.7rem', color: '#666', marginBottom: '10px' }}>CONSULTAS RECIENTES</p>
          <div className="history-item">Estructuras de acero</div>
          <div className="history-item">Dispositivos médicos</div>
          <div className="history-item">Polímeros de etileno</div>
        </div>
      </aside>

      {/* Main Area */}
      <main className="main-content">
        <div className="search-box-wrapper">
          <div className="search-container">
            <input 
              type="text" 
              placeholder="Describe la mercancía técnicamente..." 
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
            />
            <button onClick={handleSearch} disabled={loading}>
              {loading ? 'ANALIZANDO...' : 'CLASIFICAR'}
            </button>
          </div>
        </div>

        <div className="results-area">
          {results ? (
            results.tarifa_suggestions.length > 0 ? (
              results.tarifa_suggestions.map((s, i) => (
                <div key={i} className="suggestion-card">
                  <div className="suggestion-header">
                    <span className="fraction-code">{s.fraccion || s.nico || 'NICO Pendiente'}</span>
                    <div>
                      <span className="tag tag-nom">NOM-001</span>
                      <span className="tag tag-permiso">PERMISO SE</span>
                    </div>
                  </div>
                  <p style={{ fontSize: '0.95rem' }}>{s.descripcion || Object.values(s)[0]}</p>
                </div>
              ))
            ) : (
              <p style={{ textAlign: 'center', opacity: 0.5 }}>No se encontraron fracciones exactas. Intente otra descripción.</p>
            )
          ) : (
            <div style={{ textAlign: 'center', marginTop: '50px', opacity: 0.3 }}>
              <h1>🔍</h1>
              <p>Inicie una búsqueda para ver sugerencias arancelarias</p>
            </div>
          )}
        </div>
      </main>

      {/* Legal Panel */}
      <section className="legal-panel">
        <h3>📚 Sustento Legal (RAG)</h3>
        {results?.legal_support.map((l, i) => (
          <div key={i} className="legal-snippet">
            <strong>Referencia {i + 1}</strong>
            <p>{l.content}</p>
          </div>
        )) || (
          <p style={{ fontSize: '0.85rem', opacity: 0.5 }}>Los fundamentos legales de la Ley Aduanera y RGCE aparecerán aquí.</p>
        )}
      </section>
    </div>
  );
}

export default App;
