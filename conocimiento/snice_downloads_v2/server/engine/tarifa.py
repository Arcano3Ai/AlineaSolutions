import pandas as pd
import os
import glob

class TarifaEngine:
    def __init__(self):
        self.df = None
        # Buscar el archivo de NICOs más reciente en la carpeta de conocimiento
        pattern = "conocimiento_clasificador_experto/tarifas_y_nicos/*NICO*.xlsx"
        files = glob.glob(pattern)
        
        if files:
            path = files[0]
            print(f"Cargando base de datos de Tarifa: {path}")
            try:
                # Intentamos leer el Excel. Ajustamos nombres de columnas si es necesario.
                self.df = pd.read_excel(path)
                # Normalizar nombres de columnas a minúsculas
                self.df.columns = [str(c).lower().strip() for c in self.df.columns]
            except Exception as e:
                print(f"Error cargando Excel: {e}")
        else:
            print("Aviso: No se encontró base de datos de NICOs en Excel.")
            
    def query_nico(self, term: str):
        if self.df is None: return []
        
        # Búsqueda heurística por palabras clave en la descripción
        # Intentamos encontrar columnas comunes: 'descripcion', 'mercancia', 'nombre'
        col_desc = next((c for c in self.df.columns if 'desc' in c or 'merc' in c), None)
        
        if not col_desc:
            return [{"error": "No se encontró columna de descripción en el Excel"}]
            
        mask = self.df[col_desc].str.contains(term, case=False, na=False)
        results = self.df[mask].head(10)
        
        # Convertir a lista de diccionarios limpia
        return results.to_dict('records')

tarifa_engine = TarifaEngine()
