import os
import re
import unicodedata
from datetime import datetime
from fpdf import FPDF
from database.models import Section, Chapter, Heading, Subheading, Fraction

PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))

def safe_str(s):
    """Normalize string to be safe for PDF latin-1 output, preserving Spanish characters by replacing accents."""
    if s is None:
        return ""
    if not isinstance(s, str):
        s = str(s)
    
    # Clean HTML tags if present
    s = re.sub(r'<[^>]+>', '\n', s)
    s = re.sub(r'\n+', '\n', s)
    
    # Replace common spanish characters with latin-1 safe equivalents
    replacements = {
        'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u',
        'Á': 'A', 'É': 'E', 'Í': 'I', 'Ó': 'O', 'Ú': 'U',
        'ñ': 'n', 'Ñ': 'N', 'ü': 'u', 'Ü': 'U',
        '¿': '', '¡': '', '—': '-', '–': '-',
        '“': '"', '”': '"', '‘': "'", '’': "'",
        '\u201c': '"', '\u201d': '"', '\u2018': "'", '\u2019': "'"
    }
    for k, v in replacements.items():
        s = s.replace(k, v)
        
    # Standard normalization to ASCII safe
    nfkd = unicodedata.normalize('NFKD', s)
    s_clean = nfkd.encode('ASCII', 'ignore').decode('ASCII')
    return s_clean.strip()

class SingleReportPDF(FPDF):
    def __init__(self, logo_path=None):
        super().__init__()
        self.logo_path = logo_path
        
    def header(self):
        # Header banner
        self.set_fill_color(26, 54, 93) # Navy blue
        self.rect(0, 0, 210, 30, "F")
        
        # Logo placeholder on the right
        if self.logo_path and os.path.exists(self.logo_path):
            try:
                self.image(self.logo_path, 165, 5, w=35)
            except Exception:
                pass
                
        self.set_y(8)
        self.set_x(15)
        self.set_font("Helvetica", "B", 14)
        self.set_text_color(255, 255, 255)
        self.cell(0, 6, "ALINEA SOLUTIONS", new_x="LMARGIN", new_y="NEXT")
        
        self.set_font("Helvetica", "", 10)
        self.set_text_color(56, 189, 248) # Cyan accent
        self.cell(0, 5, "DICTAMEN TECNICO DE CLASIFICACION ARANCELARIA", new_x="LMARGIN", new_y="NEXT")
        
        self.set_y(35)
        self.ln(2)

    def footer(self):
        # Footer accent line
        self.set_y(-20)
        self.set_draw_color(56, 189, 248)
        self.line(15, self.get_y(), 195, self.get_y())
        
        self.set_y(-15)
        self.set_font("Helvetica", "I", 7)
        self.set_text_color(100, 116, 139)
        self.cell(100, 8, "ALINEA SOLUTIONS - Sistema Inteligente LIGIE", align="L")
        self.cell(0, 8, f"Pagina {self.page_no()}/{{nb}}", align="R")

    def section_header(self, title):
        self.set_font("Helvetica", "B", 11)
        self.set_fill_color(241, 245, 249) # Light blue-grey background
        self.set_text_color(26, 54, 93) # Dark navy
        self.cell(0, 8, f"  {title.upper()}", fill=True, new_x="LMARGIN", new_y="NEXT")
        
        # cyan left border style
        y_prev = self.get_y() - 8
        self.set_draw_color(56, 189, 248)
        self.set_line_width(1.5)
        self.line(15, y_prev, 15, y_prev + 8)
        self.set_line_width(0.2)
        self.ln(2)

    def value_block(self, label, val):
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(71, 85, 105)
        self.cell(50, 6, f"{label}:")
        self.set_font("Helvetica", "", 9)
        self.set_text_color(15, 23, 42)
        self.multi_cell(0, 6, val)

def generate_single_classification_report(session, data, output_path=None):
    """
    Generates a single classification PDF report for a product.
    
    :param session: SQLAlchemy DB Session
    :param data: Dictionary with keys:
                 - product_description: Commercial description of classified goods
                 - hs_code: Recommended tariff code (6 or 8 digits)
                 - nico: Optional NICO suffix
                 - confidence: Confidence score (0.0 to 1.0)
                 - reasoning: Mercological reasoning (text or HTML)
                 - method: Method name (ai, local, rule_based)
                 - rrnas: List of non-tariff regulations (optional)
                 - taxes: Dictionary with estimated taxes (optional)
    :param output_path: Where to save the output PDF file.
    """
    product_desc = data.get('product_description', 'Mercancia en General')
    hs_code = data.get('hs_code', '').replace('.', '').replace(' ', '').strip()
    nico_str = data.get('nico', '')
    confidence = data.get('confidence', 0.8)
    reasoning = data.get('reasoning', '')
    method = data.get('method', 'local')
    rrnas = data.get('rrnas', [])
    taxes = data.get('taxes', {})
    
    # Locate Logo
    logo_path = os.path.join(PROJECT_ROOT, 'static', 'img', 'logo.png')
    if not os.path.exists(logo_path):
        logo_path = os.path.join(PROJECT_ROOT, 'static', 'img', 'logo_light.png')
    if not os.path.exists(logo_path):
        logo_path = os.path.join(PROJECT_ROOT, 'logo.png')
        
    # Query database LIGIE hierarchy
    fraction = None
    subheading = None
    heading = None
    chapter = None
    section = None
    
    if len(hs_code) >= 8:
        fraction = session.query(Fraction).filter(Fraction.code.like(f"%{hs_code[:8]}%")).first()
        if fraction:
            subheading = fraction.subheading
        else:
            subheading = session.query(Subheading).filter(Subheading.code.like(f"%{hs_code[:6]}%")).first()
    elif len(hs_code) == 6:
        subheading = session.query(Subheading).filter(Subheading.code.like(f"%{hs_code[:6]}%")).first()
        
    if subheading:
        heading = subheading.heading
    else:
        heading = session.query(Heading).filter(Heading.code.like(f"%{hs_code[:4]}%")).first()
        
    if heading:
        chapter = heading.chapter
    else:
        chapter = session.query(Chapter).filter(Chapter.code.like(f"%{hs_code[:2]}%")).first()
        
    if chapter:
        section = chapter.section
        
    # PDF Setup
    pdf = SingleReportPDF(logo_path=logo_path)
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()
    
    # SECTION 1: DETALLES DE CLASIFICACION
    pdf.section_header("1. Resumen de la Clasificacion")
    pdf.ln(1)
    
    # Summary Table
    pdf.set_fill_color(248, 250, 252)
    pdf.set_draw_color(226, 232, 240)
    pdf.rect(15, pdf.get_y(), 180, 50, "DF")
    
    pdf.set_y(pdf.get_y() + 3)
    pdf.set_x(20)
    
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(71, 85, 105)
    pdf.cell(50, 6, "Mercancia Declarada:")
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(15, 23, 42)
    pdf.multi_cell(120, 6, safe_str(product_desc))
    
    pdf.set_x(20)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(71, 85, 105)
    pdf.cell(50, 6, "Codigo Sugerido LIGIE:")
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(26, 54, 93)
    
    formatted_code = hs_code
    if len(hs_code) >= 8:
        formatted_code = f"{hs_code[:4]}.{hs_code[4:6]}.{hs_code[6:8]}"
    elif len(hs_code) == 6:
        formatted_code = f"{hs_code[:4]}.{hs_code[4:6]}"
        
    pdf.cell(120, 6, safe_str(formatted_code), new_x="LMARGIN", new_y="NEXT")
    
    pdf.set_x(20)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(71, 85, 105)
    pdf.cell(50, 6, "NICO Identificado:")
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(120, 6, safe_str(nico_str or "00"), new_x="LMARGIN", new_y="NEXT")
    
    pdf.set_x(20)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(71, 85, 105)
    pdf.cell(50, 6, "Grado de Confianza:")
    pdf.set_font("Helvetica", "B", 10)
    conf_val = float(confidence)
    if conf_val >= 0.8:
        pdf.set_text_color(22, 101, 52) # Dark green
        conf_label = f"ALTA ({(conf_val*100):.0f}%)"
    elif conf_val >= 0.5:
        pdf.set_text_color(180, 83, 9) # Dark orange
        conf_label = f"MEDIA ({(conf_val*100):.0f}%)"
    else:
        pdf.set_text_color(153, 27, 27) # Dark red
        conf_label = f"BAJA ({(conf_val*100):.0f}%)"
    pdf.cell(120, 6, safe_str(conf_label), new_x="LMARGIN", new_y="NEXT")
    
    pdf.set_x(20)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(71, 85, 105)
    pdf.cell(50, 6, "Metodo de Clasificacion:")
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(15, 23, 42)
    method_label = "Alinea AI Engine (RAG Legal + Vision)" if method == 'gemini' else "Similitud Lexico-Semantica Local (RGI 1)"
    pdf.cell(120, 6, safe_str(method_label), new_x="LMARGIN", new_y="NEXT")
    
    pdf.set_x(20)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(71, 85, 105)
    pdf.cell(50, 6, "Fecha y Hora:")
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(120, 6, safe_str(datetime.now().strftime('%d/%m/%Y %H:%M:%S')), new_x="LMARGIN", new_y="NEXT")
    
    pdf.set_y(pdf.get_y() + 8)
    pdf.ln(2)
    
    # SECTION 2: FUNDAMENTACION LEGAL LIGIE
    pdf.section_header("2. Fundamentacion Legal (Estructura LIGIE)")
    pdf.ln(1)
    
    if section:
        pdf.value_block("SECCION " + section.code, safe_str(section.title))
        pdf.ln(1)
    if chapter:
        pdf.value_block("CAPITULO " + chapter.code, safe_str(chapter.title))
        pdf.ln(1)
    if heading:
        pdf.value_block("PARTIDA " + heading.code, safe_str(heading.title))
        pdf.ln(1)
    if subheading:
        pdf.value_block("SUBPARTIDA " + subheading.code, safe_str(subheading.title))
        pdf.ln(1)
    if fraction:
        pdf.value_block("FRACCION NICO " + fraction.code, safe_str(fraction.description))
        pdf.ln(1)
    else:
        # Fallback to subheading description or default
        desc = subheading.description if subheading else ""
        if desc:
            pdf.value_block("FRACCION NICO", safe_str(desc))
            pdf.ln(1)
            
    pdf.ln(2)
    
    # SECTION 3: RAZONAMIENTO MERCIOLOGICO
    pdf.section_header("3. Mapa de Razonamiento Merciologico")
    pdf.ln(1)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(33, 41, 54)
    cleaned_reasoning = safe_str(reasoning)
    pdf.multi_cell(0, 5, cleaned_reasoning)
    pdf.ln(4)
    
    # SECTION 4: GRAVAMENES Y RESTRICCIONES
    pdf.section_header("4. Aranceles y Regulaciones No Arancelarias (RRNA)")
    pdf.ln(1)
    
    # Taxes Table
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_fill_color(226, 232, 240)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(100, 7, "Tasa / Gravamen Estimado", border=1, fill=True)
    pdf.cell(80, 7, "Valor", border=1, fill=True, align="C", new_x="LMARGIN", new_y="NEXT")
    
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(100, 6, "Impuesto General de Importacion (IGI)", border=1)
    pdf.cell(80, 6, safe_str(taxes.get('igi', '10.0%')), border=1, align="C", new_x="LMARGIN", new_y="NEXT")
    
    pdf.cell(100, 6, "Impuesto al Valor Agregado (IVA)", border=1)
    pdf.cell(80, 6, safe_str(taxes.get('iva', '16.0%')), border=1, align="C", new_x="LMARGIN", new_y="NEXT")
    
    pdf.cell(100, 6, "Derecho de Tramite Aduanero (DTA)", border=1)
    pdf.cell(80, 6, "8 al millar (0.8%)", border=1, align="C", new_x="LMARGIN", new_y="NEXT")
    
    pdf.cell(100, 6, "Prevalidacion (SAT)", border=1)
    pdf.cell(80, 6, "$310.00 MXN", border=1, align="C", new_x="LMARGIN", new_y="NEXT")
    
    pdf.ln(4)
    
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(180, 83, 9)
    pdf.cell(0, 5, "Restricciones No Arancelarias Obligatorias:")
    pdf.ln(6)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(15, 23, 42)
    
    if rrnas:
        for r in rrnas:
            pdf.set_x(15)
            pdf.multi_cell(0, 5, f"- {safe_str(r)}")
    else:
        pdf.set_x(15)
        pdf.multi_cell(0, 5, "Sin restricciones arancelarias obligatorias detectadas para esta fraccion.")
        
    pdf.set_x(15)
    pdf.ln(5)
    
    # SECTION 5: AVISO LEGAL
    pdf.section_header("5. Limitacion de Responsabilidad y Sustento Legal")
    pdf.ln(1)
    pdf.set_font("Helvetica", "I", 7.5)
    pdf.set_text_color(100, 116, 139)
    
    legal_text = (
        "AVISO LEGAL / DECLARACION DE LIMITACION DE RESPONSABILIDAD\n"
        "Este dictamen tecnico de clasificacion arancelaria se emite con caracter meramente indicativo "
        "e informativo, fundamentado en las Reglas Generales de Interpretacion (RGI) de la Ley de los Impuestos "
        "Generales de Importacion y de Exportacion (LIGIE) de Mexico y las herramientas de inteligencia artificial "
        "y recuperacion semantica de ALINEA SOLUTIONS.\n\n"
        "Este reporte no constituye una resolucion oficial o vinculante por parte del Servicio de Administracion "
        "Tributaria (SAT) ni de ninguna otra autoridad aduanera o fiscal en los terminos de los Articulos 47 y 48 de la "
        "Ley Aduanera mexicana vigente. La clasificacion arancelaria definitiva, la correcta determinacion del "
        "Impuesto General de Importacion (IGI), Impuesto al Valor Agregado (IVA), el cumplimiento de regulaciones y "
        "restricciones no arancelarias (RRNA) y demas contribuciones aduaneras aplicables al despacho de las mercancias "
        "son responsabilidad exclusiva del contribuyente (importador o exportador) y de su agente aduanal en terminos "
        "del Articulo 54 de la Ley Aduanera. ALINEA SOLUTIONS no asume responsabilidad alguna por multas, recargos, "
        "diferencias arancelarias, retenciones de mercancia o cualquier sancion aduanera derivada del uso de este reporte."
    )
    
    pdf.multi_cell(0, 4, legal_text)
    
    # Save PDF
    if output_path is None:
        report_dir = os.path.join(PROJECT_ROOT, "reportes")
        os.makedirs(report_dir, exist_ok=True)
        filename = f"reporte_clasificacion_{hs_code}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        output_path = os.path.join(report_dir, filename)
        
    pdf.output(output_path)
    return output_path
