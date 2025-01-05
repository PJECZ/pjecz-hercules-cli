"""
Sentencias
"""

from pathlib import Path
import os
import sys
from urllib.parse import unquote

import click
from dotenv import load_dotenv
import requests

from lib.authentications import get_auth_token
from lib.exceptions import MyAnyError
from lib.pdf_tools import extraer_texto_de_archivo_pdf

# Cargar variables de entorno
load_dotenv()
API_BASE_URL = os.getenv("API_BASE_URL")
TIMEOUT = int(os.getenv("TIMEOUT"))
SENTENCIAS_BASE_DIR = os.getenv("SENTENCIAS_BASE_DIR")
SENTENCIAS_GCS_BASE_URL = os.getenv("SENTENCIAS_GCS_BASE_URL")


@click.group()
def cli():
    """Sentencias"""


@click.command()
@click.argument("creado_desde", type=str)
@click.argument("creado_hasta", type=str)
@click.option("--sobreescribir", is_flag=True)
def analizar(creado_desde, creado_hasta, sobreescribir):
    """Analizar sentencias"""
    click.echo("Analizando sentencias")

    # Validar que exista el directorio SENTENCIAS_BASE_DIR
    sentencias_dir = Path(SENTENCIAS_BASE_DIR)
    if sentencias_dir.exists() is False or sentencias_dir.is_dir() is False:
        click.echo(
            click.style(f"No existe el directorio {SENTENCIAS_BASE_DIR}", fg="red")
        )
        sys.exit(1)

    # Obtener el token
    try:
        oauth2_token = get_auth_token()
    except Exception as error:
        click.echo(click.style(str(error), fg="red"))
        sys.exit(1)

    # Consultar las sentencias
    try:
        respuesta = requests.get(
            url=f"{API_BASE_URL}/api/v1/sentencias",
            headers={"Authorization": f"Bearer {oauth2_token}"},
            params={"creado_desde": creado_desde, "creado_hasta": creado_hasta},
            timeout=TIMEOUT,
        )
    except requests.exceptions.RequestException as error:
        click.echo(click.style(str(error), fg="red"))
        sys.exit(1)
    if respuesta.status_code != 200:
        click.echo(click.style(str(respuesta), fg="red"))
        sys.exit(1)

    # Si hubo un error
    contenido = respuesta.json()
    if contenido["success"] is False:
        click.echo(click.style(contenido["message"], fg="red"))
        sys.exit(1)

    # Bucle por las sentencias
    contador = 0
    for item in contenido["data"]:
        click.echo(click.style(f"[{item['id']}] ", fg="white"), nl=False)

        # Definir la ruta al archivo pdf reemplazando el inicio del url con el directorio
        archivo_ruta = Path(
            SENTENCIAS_BASE_DIR + unquote(item["url"][len(SENTENCIAS_GCS_BASE_URL) :])
        )

        # Verificar que exista el archivo pdf
        archivo_ruta_existe = bool(archivo_ruta.exists() and archivo_ruta.is_file())

        # Si NO existe se muestra en color amarillo y se omite, de lo contario se muestra en color verde
        if archivo_ruta_existe is False:
            click.echo(click.style(f"{item['archivo']} NO existe", fg="yellow"))
            continue
        click.echo(click.style(f"{item['archivo']} ", fg="green"), nl=False)

        # Extraer el texto del archivo PDF
        try:
            texto = extraer_texto_de_archivo_pdf(str(archivo_ruta))
        except MyAnyError as error:
            click.echo(click.style(str(error), fg="yellow"))
            continue

        # Si no hay texto, se omite
        if texto.strip() == "":
            click.echo(click.style("No tiene texto", fg="yellow"))
            continue
        click.echo(click.style(f"Longitud {len(texto)} ", fg="green"), nl=False)

        # Definir el análisis
        data = {
            "id": item["id"],
            "analisis": {
                "archivo_tamanio": archivo_ruta.stat().st_size,
                "autor": item["autoridad_clave"],
                "longitud": len(texto),
                "texto": texto,
            },
            "sintesis": None,
            "categorias": None,
        }

        # Enviar el análisis
        try:
            respuesta = requests.put(
                url=f"{API_BASE_URL}/api/v1/sentencias/rag",
                headers={"Authorization": f"Bearer {oauth2_token}"},
                data=data,
                timeout=TIMEOUT,
            )
        except requests.exceptions.RequestException as error:
            click.echo(click.style(str(error), fg="red"))
            sys.exit(1)

        # Incrementar el contador
        contador += 1
        click.echo(click.style("ENVIADO", fg="green"))

    # Mostrar el mensaje de término
    click.echo(click.style(f"Fueron analizadas {contador} sentencias", fg="green"))


@click.command()
@click.argument("creado_desde", type=str)
@click.argument("creado_hasta", type=str)
@click.option("--sobreescribir", is_flag=True)
def sintetizar(creado_desde, creado_hasta, sobreescribir):
    """Sintetizar sentencias"""
    click.echo("Sintetizando sentencias")

    # Consultar las sentencias

    # Si no hay sentencias, terminar

    # Bucle por las sentencias

    # Extraer el texto del archivo PDF

    # Sintetizar con OpenAI

    # Enviar el análisis y la síntesis

    # Mostrar el mensaje de término

    # Mostrar el mensaje de término
    contador = 0
    click.echo(click.style(f"Fueron sintetizadas {contador} sentencias", fg="green"))


cli.add_command(analizar)
cli.add_command(sintetizar)
