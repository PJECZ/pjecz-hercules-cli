"""
PDF Tools
"""

from pathlib import Path

from pypdf import PdfReader

from lib.exceptions import MyAnyError, MyFileNotFoundError, MyFileNotAllowedError


def extraer_texto_de_archivo_pdf(archivo: str) -> str:
    """Extraer el texto de un archivo PDF"""
    ruta = Path(archivo)
    if ruta.exists() is False or ruta.is_file() is False:
        raise MyFileNotFoundError("No existe el archivo PDF")
    if ruta.suffix.lower() != ".pdf":
        raise MyFileNotAllowedError("No es un archivo PDF")
    texto = ""
    try:
        lector = PdfReader(ruta)
        paginas_textos = []
        for pagina in lector.pages:
            texto_sin_avances_de_linea = pagina.extract_text().replace("\n", " ")
            paginas_textos.append(" ".join(texto_sin_avances_de_linea.split()))
        texto = " ".join(paginas_textos)
    except Exception as error:
        raise MyAnyError(error) from error
    return texto
