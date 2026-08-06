import os

class PedimentoTaxCalculator:
    """
    Calculador de contribuciones y gravámenes de comercio exterior conforme a la 
    legislación aduanera mexicana vigente (Ley de los Impuestos Generales de Importación 
    y de Exportación - LIGIE, Ley del IVA, Ley del IEPS y Ley Federal de Derechos).
    """

    @staticmethod
    def resolve_item_rates(hs_code, has_fta=False):
        """
        Determina las tasas de IGI, IVA e IEPS aplicables según la fracción arancelaria (Capítulo)
        y la existencia de un Tratado de Libre Comercio (TLC / T-MEC).
        """
        # Limpiar fracción arancelaria
        clean_code = hs_code.replace('.', '').replace(' ', '')
        if not clean_code:
            return {"igi_rate": 0.10, "iva_rate": 0.16, "ieps_rate": 0.0, "notes": "Código inválido, aplicando tasa general."}
        
        try:
            chapter = int(clean_code[:2])
        except ValueError:
            return {"igi_rate": 0.10, "iva_rate": 0.16, "ieps_rate": 0.0, "notes": "Capítulo no reconocible, aplicando tasa general."}

        # 1. Tasa IGI (Ad-Valorem)
        if has_fta:
            igi_rate = 0.0
            notes_igi = "Preferencia arancelaria aplicada por Tratado de Libre Comercio (IGI 0%)."
        else:
            if chapter in [84, 85, 90]:
                igi_rate = 0.0  # Tecnología y maquinaria usualmente exenta o con PROSEC
                notes_igi = "Capítulo de bienes de capital/tecnología (IGI 0% bajo regla general/PROSEC)."
            elif chapter in [61, 62, 64]:
                igi_rate = 0.20  # Textil, confección y calzado (tasas altas de protección)
                notes_igi = "Capítulo de calzado y vestido sujeto a arancel de protección (IGI 20%)."
            elif chapter in [1, 2, 3, 4, 5, 7, 8, 9, 10, 11, 12]:
                igi_rate = 0.15  # Agropecuarios
                notes_igi = "Capítulo de alimentos o materias primas agrícolas (IGI 15%)."
            elif chapter == 30:
                igi_rate = 0.0  # Medicamentos
                notes_igi = "Sector salud / Medicamentos (IGI 0%)."
            else:
                igi_rate = 0.10  # Tasa general residual
                notes_igi = "Tasa general residual para importaciones (IGI 10%)."

        # 2. Tasa IVA (Impuesto al Valor Agregado)
        # Productos exentos / tasa 0% según Art. 2-A de la Ley del IVA (alimentos básicos y medicinas)
        if chapter in [1, 2, 3, 4, 5, 7, 8, 9, 10, 11, 12]:
            iva_rate = 0.0
            notes_iva = "Alimentos básicos exentos de IVA conforme a Ley del IVA Art. 2-A (IVA 0%)."
        elif chapter == 30:
            iva_rate = 0.0
            notes_iva = "Medicamentos de patente exentos de IVA conforme a Ley del IVA Art. 2-A (IVA 0%)."
        else:
            iva_rate = 0.16
            notes_iva = "Tasa general de IVA (16%)."

        # 3. Tasa IEPS (Bebidas alcohólicas, tabacos, etc.)
        if chapter == 22:
            ieps_rate = 0.265  # Ejemplo: Bebidas con graduación alcohólica menor a 14°
            notes_ieps = "Sujeto a IEPS por graduación alcohólica (IEPS 26.5%)."
        else:
            ieps_rate = 0.0
            notes_ieps = "Exento de IEPS."

        return {
            "igi_rate": igi_rate,
            "iva_rate": iva_rate,
            "ieps_rate": ieps_rate,
            "notes": f"{notes_igi} | {notes_iva} | {notes_ieps}"
        }

    @classmethod
    def calculate_import_taxes(cls, customs_value_usd, exchange_rate, has_fta=False, items=None, prv_fee=310.0, cnt_fee=70.0):
        """
        Realiza el cálculo de impuestos de importación para un conjunto de partidas.
        - prv_fee: Cuota de Prevalidación fija (SAT).
        - cnt_fee: Cuota de Contraprestación para prevalidación fija.
        """
        valor_aduana_mxn = round(customs_value_usd * exchange_rate, 2)
        
        # Si no hay partidas específicas, tratamos el pedimento como un solo bloque general
        if not items:
            items = [{
                "hs_code": "8471.30.01",
                "customs_value_item_usd": customs_value_usd,
                "description": "Mercancías Declaradas"
            }]

        # Calcular prorrateo de valor
        total_items_val_usd = sum(item.get("customs_value_item_usd", 0.0) for item in items)
        if total_items_val_usd <= 0.0:
            total_items_val_usd = customs_value_usd

        # 1. DTA (Derecho de Trámite Aduanero)
        # Ley Federal de Derechos: 8 al millar sobre valor aduana para operaciones comerciales generales.
        # Operaciones bajo TLC (T-MEC Art. 2.16.3): Cuota fija de DTA (ej. $436 pesos mexicanos para 2026).
        if has_fta:
            total_dta_mxn = 436.00
            dta_notes = "DTA Fijo aplicado conforme a beneficios del Tratado de Libre Comercio."
        else:
            calculated_dta = valor_aduana_mxn * 0.008
            total_dta_mxn = round(max(436.00, calculated_dta), 2)
            dta_notes = f"DTA calculado al 8 al millar sobre valor aduana (${valor_aduana_mxn:.2f} MXN)."

        calculated_items = []
        total_igi_mxn = 0.0
        total_ieps_mxn = 0.0
        total_iva_items_mxn = 0.0

        for idx, item in enumerate(items):
            item_val_usd = item.get("customs_value_item_usd", 0.0)
            # Prorrateo si los valores unitarios no suman exactamente el total declarado
            ratio = item_val_usd / total_items_val_usd if total_items_val_usd > 0 else (1.0 / len(items))
            item_val_aduana_mxn = round(valor_aduana_mxn * ratio, 2)
            
            hs = item.get("hs_code", "0000.00.00")
            rates = cls.resolve_item_rates(hs, has_fta=has_fta)
            
            # IGI
            item_igi_mxn = round(item_val_aduana_mxn * rates["igi_rate"], 2)
            total_igi_mxn += item_igi_mxn
            
            # IEPS
            item_ieps_mxn = round(item_val_aduana_mxn * rates["ieps_rate"], 2)
            total_ieps_mxn += item_ieps_mxn
            
            # DTA correspondiente a este item para base gravable de IVA
            item_dta_share_mxn = round(total_dta_mxn * ratio, 2)
            
            # Base del IVA = Valor en aduana + IGI + DTA + IEPS + otros impuestos
            item_iva_base = item_val_aduana_mxn + item_igi_mxn + item_dta_share_mxn + item_ieps_mxn
            item_iva_mxn = round(item_iva_base * rates["iva_rate"], 2)
            total_iva_items_mxn += item_iva_mxn

            calculated_items.append({
                "partida": idx + 1,
                "hs_code": hs,
                "description": item.get("description", "Sin descripción"),
                "value_usd": item_val_usd,
                "value_mxn": round(item_val_usd * exchange_rate, 2),
                "customs_value_mxn": item_val_aduana_mxn,
                "igi_rate": rates["igi_rate"],
                "igi_mxn": item_igi_mxn,
                "iva_rate": rates["iva_rate"],
                "iva_mxn": item_iva_mxn,
                "ieps_rate": rates["ieps_rate"],
                "ieps_mxn": item_ieps_mxn,
                "notes": rates["notes"]
            })

        # Prevalidación (PRV) es sujeta a IVA (16%)
        prv_iva_mxn = round(prv_fee * 0.16, 2)
        total_iva_mxn = round(total_iva_items_mxn + prv_iva_mxn, 2)

        # Totales del Pedimento
        # Forma de Pago usual: 0 (Efectivo/Transferencia electrónica de fondos)
        cuadro_contribuciones = [
            {"clave": 1, "concepto": "IGI (Impuesto General Importación)", "fp": 0, "importe": round(total_igi_mxn, 0)},
            {"clave": 3, "concepto": "DTA (Derecho Trámite Aduanero)", "fp": 0, "importe": round(total_dta_mxn, 0)},
            {"clave": 15, "concepto": "PRV (Prevalidación)", "fp": 0, "importe": round(prv_fee, 0)},
            {"clave": 50, "concepto": "IVA (Impuesto al Valor Agregado)", "fp": 0, "importe": round(total_iva_mxn, 0)}
        ]

        if total_ieps_mxn > 0.0:
            cuadro_contribuciones.append(
                {"clave": 9, "concepto": "IEPS (Impuesto Especial Producción/Servicios)", "fp": 0, "importe": round(total_ieps_mxn, 0)}
            )

        # CNT (Contraprestación) - En México no se cataloga siempre como contribución en el cuadro 
        # pero es un costo obligatorio pagado en la misma cuenta aduanera. Lo sumamos al total de pago.
        cuadro_contribuciones.append(
            {"clave": 99, "concepto": "CNT (Contraprestación Prevalidación)", "fp": 0, "importe": round(cnt_fee, 0)}
        )

        total_contribuciones_mxn = sum(c["importe"] for c in cuadro_contribuciones)

        return {
            "valor_comercial_usd": total_items_val_usd,
            "valor_comercial_mxn": round(total_items_val_usd * exchange_rate, 2),
            "valor_aduana_mxn": valor_aduana_mxn,
            "exchange_rate": exchange_rate,
            "has_fta": has_fta,
            "dta_notes": dta_notes,
            "items": calculated_items,
            "prv_fee": prv_fee,
            "prv_iva": prv_iva_mxn,
            "cnt_fee": cnt_fee,
            "total_igi_mxn": round(total_igi_mxn, 2),
            "total_dta_mxn": round(total_dta_mxn, 2),
            "total_iva_mxn": round(total_iva_mxn, 2),
            "total_ieps_mxn": round(total_ieps_mxn, 2),
            "cuadro_contribuciones": cuadro_contribuciones,
            "total_contribuciones_mxn": total_contribuciones_mxn
        }
