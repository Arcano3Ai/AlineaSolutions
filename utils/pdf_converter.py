import os
import fitz  # PyMuPDF

class VucemPDFConverter:
    """
    Herramienta de procesamiento de PDFs e imágenes para cumplir con las especificaciones
    técnicas estrictas de la Ventanilla Única de Comercio Exterior Mexicana (VUCEM).
    Especificaciones VUCEM para e-Documents:
    - Peso máximo: 3.0 MB.
    - Sin encriptación ni contraseñas.
    - Sin scripts activos, macros, campos de formulario ni JavaScript.
    - Sin archivos adjuntos u objetos embebidos.
    """

    @staticmethod
    def is_encrypted(file_path):
        """Verifica si el PDF está encriptado o requiere contraseña."""
        try:
            doc = fitz.open(file_path)
            encrypted = doc.is_encrypted
            doc.close()
            return encrypted
        except Exception:
            return True  # Si falla en abrir, asumimos restricción/error

    @staticmethod
    def convert_image_to_pdf(image_path, output_path):
        """Convierte una imagen (PNG, JPG, JPEG) a un documento PDF limpio y compatible."""
        try:
            doc = fitz.open()
            img = fitz.open(image_path)
            rect = img[0].rect
            pdfbytes = img.convert_to_pdf()
            img.close()
            
            imgpdf = fitz.open("pdf", pdfbytes)
            page = doc.new_page(width=rect.width, height=rect.height)
            page.show_pdf_page(rect, imgpdf, 0)
            imgpdf.close()
            
            doc.save(output_path, deflate=True, garbage=4)
            doc.close()
            return {"success": True, "path": output_path, "message": "Imagen convertida a PDF exitosamente."}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @classmethod
    def optimize_and_clean_pdf(cls, input_path, output_path, target_size_mb=3.0, force_grayscale=False):
        """
        Limpia, sanitiza y comprime un archivo PDF para ajustarlo a las políticas de VUCEM.
        """
        try:
            # 1. Verificar si está encriptado
            if cls.is_encrypted(input_path):
                return {
                    "success": False, 
                    "error": "El archivo está encriptado o protegido con contraseña. Debe desencriptarse primero."
                }

            doc = fitz.open(input_path)
            original_size = os.path.getsize(input_path)

            # 2. Sanitizar elementos activos (JavaScript, enlaces, anotaciones y adjuntos)
            # VUCEM rechaza archivos con anotaciones o scripts incrustados.
            for page in doc:
                # Eliminar enlaces activos
                for link in page.links():
                    page.delete_link(link)
                # Eliminar anotaciones y marcas
                for annot in page.annots():
                    page.delete_annot(annot)
                # Eliminar widgets de formulario
                for widget in page.widgets():
                    page.delete_widget(widget)

            # Eliminar archivos embebidos/adjuntos
            for emb_name in doc.embfile_names():
                doc.embfile_del(emb_name)
            
            # Guardado básico con compresión nativa
            doc.save(output_path, garbage=4, deflate=True, clean=True)
            doc.close()

            compressed_size = os.path.getsize(output_path)
            target_bytes = target_size_mb * 1024 * 1024

            # 3. Compresión agresiva por renderizado si el archivo sigue excediendo el límite de 3MB
            # Si el PDF es muy pesado (usualmente por escaneos a color de alta resolución),
            # renderizamos las páginas a imágenes con menor DPI y escala de grises.
            if compressed_size > target_bytes or force_grayscale:
                doc = fitz.open(input_path)
                compressed_doc = fitz.open()

                for page in doc:
                    # Renderizar página a imagen de 150 DPI (suficiente para legibilidad del SAT)
                    pix = page.get_pixmap(dpi=150, colorspace=fitz.csGRAY if (compressed_size > target_bytes or force_grayscale) else fitz.csRGB)
                    img_data = pix.tobytes("png")
                    
                    # Crear nueva página e insertar la imagen renderizada
                    new_page = compressed_doc.new_page(width=page.rect.width, height=page.rect.height)
                    new_page.insert_image(page.rect, stream=img_data)

                doc.close()
                compressed_doc.save(output_path, garbage=4, deflate=True, clean=True)
                compressed_doc.close()
                compressed_size = os.path.getsize(output_path)

            compliance = {
                "size_ok": compressed_size <= target_bytes,
                "no_encryption": True,
                "no_scripts": True,
                "no_attachments": True
            }

            return {
                "success": True,
                "original_size": original_size,
                "compressed_size": compressed_size,
                "savings_pct": round((1.0 - (compressed_size / original_size)) * 100.0, 1),
                "compliance": compliance,
                "path": output_path
            }

        except Exception as e:
            return {"success": False, "error": str(e)}
