import re

class VucemDescriptionValidator:
    """
    Validador de descripciones necesarias y suficientes conforme a las reglas del SAT 
    (Anexo 22 de las RGCE) para evitar multas de 'datos inexactos' (Art. 184 III L.A.).
    """

    FORBIDDEN_GENERICS = [
        "partes", "refacciones", "accesorios", "equipo", "aparato", "maquina", "material",
        "productos", "mercancia", "articulos", "herramienta", "pieza", "dispositivo", "sistema"
    ]

    BRAND_KEYWORDS = ["marca", "brand", "mca", "make"]
    MODEL_KEYWORDS = ["modelo", "model", "mod", "style"]
    SERIAL_KEYWORDS = ["serie", "serial", "s/n", "sn", "n/s", "ns"]

    @classmethod
    def validate_description(cls, description):
        if not description or not isinstance(description, str):
            return {
                "is_compliant": False,
                "score": 0,
                "warnings": ["La descripción está vacía o es inválida."],
                "suggestions": ["Ingrese una descripción detallada de la mercancía."]
            }

        desc_lower = description.lower()
        warnings = []
        suggestions = []
        score = 100

        # 1. Regla: Longitud mínima (requiere al menos 15 caracteres)
        if len(description.strip()) < 15:
            score -= 30
            warnings.append("Descripción excesivamente corta para identificar la mercancía.")
            suggestions.append("Amplíe el detalle indicando qué es, cómo funciona y de qué material está hecho.")

        # 2. Regla: Términos genéricos prohibidos o vacíos
        found_generics = [g for g in cls.FORBIDDEN_GENERICS if g in desc_lower]
        if found_generics:
            words = desc_lower.split()
            if len(words) <= 3:
                score -= 40
                warnings.append(f"Uso crítico de término genérico prohibido sin calificar: '{found_generics[0]}'.")
                suggestions.append(f"No declare únicamente '{found_generics[0]}'. Especifique su naturaleza (ej. 'partes de computadora portátil' en lugar de 'partes').")
            else:
                score -= 15
                warnings.append(f"Uso de término genérico: '{found_generics[0]}'. Asegúrese de que esté debidamente calificado.")
                suggestions.append("Califique los términos genéricos detallando su uso específico en la industria.")

        # 3. Regla: Declaración de Marca
        has_brand = any(k in desc_lower for k in cls.BRAND_KEYWORDS)
        if not has_brand:
            score -= 15
            warnings.append("Falta declarar explícitamente la Marca comercial del fabricante.")
            suggestions.append("Agregue la marca del fabricante (ej. 'Marca: Apple' o 'Marca: S/M' si no tiene marca comercial).")

        # 4. Regla: Declaración de Modelo
        has_model = any(k in desc_lower for k in cls.MODEL_KEYWORDS)
        if not has_model:
            # Búsqueda manual de alguna combinación alfanumérica típica de modelo para evitar falsos negativos
            has_alphanumeric_model = any(len(w) > 3 and any(c.isdigit() for c in w) and any(c.isalpha() for c in w) for w in description.split())
            if not has_alphanumeric_model:
                score -= 15
                warnings.append("Falta declarar el Modelo comercial del fabricante.")
                suggestions.append("Indique el modelo comercial de la mercancía (ej. 'Modelo: ThinkPad-E14' o 'Modelo: S/M').")

        # 5. Regla: Declaración de Número de Serie (maquinaria, vehículos y electrónicos)
        has_serial = any(k in desc_lower for k in cls.SERIAL_KEYWORDS)
        if any(w in desc_lower for w in ["laptop", "computadora", "motor", "telefono", "pantalla", "bateria", "vehiculo"]) and not has_serial:
            score -= 10
            warnings.append("Falta indicar Número de Serie (Requerido para electrónicos, maquinaria y activos fijos).")
            suggestions.append("Declare el número de serie único del fabricante (ej. 'Serie: 98765A' o 'Serie: No aplica').")

        score = max(0, score)
        is_compliant = score >= 70

        return {
            "is_compliant": is_compliant,
            "score": score,
            "warnings": warnings,
            "suggestions": suggestions
        }
