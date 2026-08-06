import os
from datetime import datetime

class PedimentoPRERGenerator:
    """
    Generador de Archivos Planos PRER para validación de pedimentos aduaneros en México.
    Layout oficial del Anexo 22 de las Reglas Generales de Comercio Exterior (RGCE).
    Nomenclatura de archivo: m[patente][pedimento_7_digitos].[consecutivo_3_digitos]
    """

    @staticmethod
    def generate_prer_content(patente, pedimento, aduana, regimen, tipo_op, exchange_rate, items, contributions):
        """
        Estructura el contenido de texto plano conforme al layout del SAT.
        Delimitador: Pipe (|).
        """
        lines = []
        consecutivo_diario = "0000001"
        fecha_actual = datetime.now().strftime("%Y%m%d")

        # 1. Registro 500: Encabezado del Archivo (Obligatorio)
        # Formato: 500 | Patente | Consecutivo diario | Tipo archivo (1=Pedimento) | Fecha generación
        lines.append(f"500|{patente}|{consecutivo_diario}|1|{fecha_actual}|")

        # Totales
        valor_comercial_mxn = sum(round(item.get("value_usd", 0.0) * exchange_rate, 2) for item in items)
        valor_aduana_mxn = sum(item.get("customs_value_mxn", 0.0) for item in items)
        valor_dolares = sum(item.get("value_usd", 0.0) for item in items)

        # 2. Registro 501: Datos Generales del Pedimento
        # Formato: 501 | Patente | Pedimento (7 dígitos) | Aduana-Sección (3) | Tipo Operación (1=Imp, 2=Exp) | Clave Docto | Régimen | Tipo Cambio | Valor Dolares | Valor Aduana | Valor Comercial
        lines.append(f"501|{patente}|{pedimento}|{aduana}|{tipo_op}|A1|{regimen}|{exchange_rate:.4f}|{valor_dolares:.2f}|{valor_aduana_mxn:.2f}|{valor_comercial_mxn:.2f}|")

        # 3. Registro 509: Contribuciones a Nivel Pedimento
        # Formato: 509 | Patente | Pedimento | Clave Contribución | Forma Pago (0=Efectivo) | Importe
        for c in contributions:
            # No incluir CNT en el 509 si se desea estricto Anexo 22 (CNT es derecho no contribución), 
            # pero en los prevalidadores se declara bajo clave 99 o 15 agrupada. Lo declaramos para integridad del pago.
            lines.append(f"509|{patente}|{pedimento}|{c['clave']}|{c['fp']}|{int(c['importe'])}|")

        # 4. Registro 551: Partidas del Pedimento
        # Formato: 551 | Patente | Pedimento | Num Partida | Fracción (8) | Subdivisión/Nico | Val Aduana MXN | Val Comercial USD | Val Dolares | País Origen
        for idx, item in enumerate(items):
            partida_num = idx + 1
            raw_hs = item.get("hs_code", "00000000").replace(".", "").replace(" ", "")
            # Asegurar longitud de 8 dígitos para la fracción
            fraccion = raw_hs[:8].ljust(8, '0')
            nico = "00" # Subpartida / Nico default
            val_aduana_item = item.get("customs_value_mxn", 0.0)
            val_com_usd = item.get("value_usd", 0.0)
            pais_origen = "USA" if fraccion.startswith("84") or fraccion.startswith("85") else "MEX"

            lines.append(f"551|{patente}|{pedimento}|{partida_num}|{fraccion}|{nico}|{val_aduana_item:.2f}|{val_com_usd:.2f}|{val_com_usd:.2f}|{pais_origen}|")

        # 5. Registro 801: Registro de Fin de Archivo (Obligatorio)
        # Formato: 801 | Patente | Consecutivo diario | Total registros en el archivo (incluyendo 500 y 801)
        total_registros = len(lines) + 1
        lines.append(f"801|{patente}|{consecutivo_diario}|{total_registros}|")

        # Unir líneas con salto de carro y avance de línea (CRLF - estándar Windows/SAT)
        return "\r\n".join(lines) + "\r\n"
