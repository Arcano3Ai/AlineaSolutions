# GUÍA Y PLANTILLA PARA CONSOLIDACIÓN DE CURRÍCULUMS VITAE (CV)

La convocatoria del Laboratorio de Supercómputo del CIMAT exige como requisito indispensable:
> *"En el caso de la participación de un grupo de trabajo, se debe adjuntar el curriculum vitae de cada miembro. Todos los CV's deben ser enviados en un solo pdf. Preferiblemente en el formato CVU (Curriculum Vitae Único del CONAHCYT)."*

Dado que el envío debe hacerse en un **único archivo PDF**, esta guía proporciona:
1.  Las instrucciones de compilación.
2.  Una plantilla unificada y profesional para redactar el CV técnico de cada miembro si no cuentan con un CVU descargado de CONAHCYT.

---

## 1. Instrucciones de Compilación de CVs

1.  **Redacción de CVs individuales:** Cada miembro del grupo de trabajo debe completar su CV utilizando la plantilla provista a continuación (se sugiere un límite de 1 a 2 páginas por persona).
2.  **Exportación a PDF:** Exportar cada CV individual a un archivo PDF (ej. `CV_Sergio_Perez.pdf`, `CV_Yolanda_Perez.pdf`, `CV_Lorena_Morales.pdf`).
3.  **Fusión de archivos:** Combinar los PDFs individuales en el orden del grupo de trabajo en un único archivo llamado **`CVs_Consolidados_GrupoTrabajo.pdf`**.
    *   *Herramienta sugerida (Local - PowerShell):* Puedes utilizar Python para fusionar los archivos ejecutando en la terminal:
        ```python
        from pypdf import PdfMerger # o PyPDF2
        merger = PdfMerger()
        merger.append("CV_Sergio_Perez.pdf")
        merger.append("CV_Yolanda_Perez.pdf")
        merger.append("CV_Lorena_Morales.pdf")
        merger.write("CVs_Consolidados_GrupoTrabajo.pdf")
        merger.close()
        ```
    *   *Herramienta en línea:* PDF24, ILovePDF, o Acrobat Online Merger.

---

## 2. Plantilla de Currículum Vitae Técnico (Uso Recomendado)

*Complete la siguiente estructura por cada participante y compile en el documento final:*

---

### [NOMBRE COMPLETO DEL PARTICIPANTE]
**Rol en el Proyecto:** [Solicitante Principal / Investigador de Datos / Ingeniero de MLOps / etc.]  
**Institución de Adscripción:** VUCEM Optimizer S.A. de C.V.  
**Correo Electrónico:** [correo@vucemoptimizer.com]  
**CVU (CONAHCYT):** [Número de CVU de CONAHCYT, si cuenta con él. De lo contrario, indicar "No disponible"]

#### RESUMEN PROFESIONAL
*Breve descripción de su perfil técnico, años de experiencia, áreas de especialización en ingeniería de software, IA o comercio exterior, y contribución principal al proyecto del Clasificador AI.*
*(Ejemplo para Sergio: Ingeniero de Software Senior con más de X años de experiencia en desarrollo de arquitecturas de IA, especializado en Python, Node.js y sistemas distribuidos en la nube).*

#### FORMACIÓN ACADÉMICA
*   **[Título Obtenido (Licenciatura/Ingeniería/Maestría/Doctorado)]**  
    [Nombre de la Institución Académica], [Año de Inicio] - [Año de Egreso].  
    *Especialidad o enfoque de tesis, de ser relevante.*

#### EXPERIENCIA PROFESIONAL Y TECNOLÓGICA (Últimos 3 cargos/proyectos relevantes)
1.  **[Nombre del Cargo / Puesto]** | **VUCEM Optimizer S.A. de C.V.**  
    [Mes, Año Inicio] – [Presente / Mes, Año Fin].  
    *   Descripción de logros o responsabilidades clave.
    *   Tecnologías clave utilizadas (ej. Python, Flask, PyTorch, LangChain, PostgreSQL, Docker).
2.  **[Nombre del Cargo anterior]** | **[Nombre de la Empresa o Institución]**  
    [Mes, Año Inicio] – [Mes, Año Fin].  
    *   Logros clave o proyectos ejecutados.
3.  **[Proyecto Destacado]** | **Desarrollador / Investigador Principal**  
    [Año].  
    *   Breve descripción del proyecto tecnológico (ej. "Diseño y optimización del motor local de clasificación arancelaria con RAG y ChromaDB").

#### HABILIDADES TÉCNICAS Y ÁREAS DE EXPERTISE
*   **Lenguajes de Programación:** Python, JavaScript/Node.js, SQL, C++, Bash.
*   **Frameworks y Herramientas AI:** PyTorch, Hugging Face Transformers, LangChain, ChromaDB, CUDA, Ollama.
*   **Bases de Datos y Backend:** PostgreSQL, SQLAlchemy, Flask, FastAPI, Docker, Git.
*   **Conocimientos de Negocio:** Clasificación Arancelaria LIGIE, Pedimentos SAT, Integración VUCEM, CRM/ERP.

#### PUBLICACIONES, MEMORIAS O CERTIFICACIONES (Opcional)
*   *Certificaciones:* [ej. TensorFlow Developer Certificate, NVIDIA DLI CUDA C/C++]
*   *Idiomas:* Español (Nativo), Inglés ([Nivel]).
