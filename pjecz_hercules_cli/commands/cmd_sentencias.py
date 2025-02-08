"""
Cmd Sentencias

- analizar
- sintetizar
"""

import json
from pathlib import Path
import os
import sys
from urllib.parse import unquote

import click
from dotenv import load_dotenv
from openai import OpenAI
import requests

from pjecz_hercules_cli.dependencies.authentications import get_auth_token
from pjecz_hercules_cli.dependencies.exceptions import MyAnyError
from pjecz_hercules_cli.dependencies.pdf_tools import extraer_texto_de_archivo_pdf

# Cargar variables de entorno
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_ENDPOINT = os.getenv("OPENAI_ENDPOINT")
OPENAI_MODEL = os.getenv("OPENAI_MODEL")
OPENAI_ORG_ID = os.getenv("OPENAI_ORG_ID")
OPENAI_PROJECT_ID = os.getenv("OPENAI_PROJECT_ID")
OPENAI_PROMPT = os.getenv("OPENAI_PROMPT")
API_BASE_URL = os.getenv("API_BASE_URL")
LIMIT = int(os.getenv("LIMIT"))
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
        click.echo(click.style(f"No existe el directorio {SENTENCIAS_BASE_DIR}", fg="red"))
        sys.exit(1)

    # Obtener el token
    try:
        oauth2_token = get_auth_token()
    except Exception as error:
        click.echo(click.style(str(error), fg="red"))
        sys.exit(1)

    # Inicializar el contador y el offset
    contador = 0
    offset = 0

    # Bucle por las consultas
    while True:

        # Consultar las sentencias
        try:
            respuesta = requests.get(
                url=f"{API_BASE_URL}/api/v5/sentencias",
                headers={"Authorization": f"Bearer {oauth2_token}"},
                params={"creado_desde": creado_desde, "creado_hasta": creado_hasta, "limit": LIMIT},
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

            # Si ya fue analizada, se omite
            if sobreescribir is False and item["rag_fue_analizado_tiempo"] is not None:
                click.echo(click.style("Se omite porque ya fue analizada", fg="yellow"))
                continue

            # Definir la ruta al archivo pdf reemplazando el inicio del url con el directorio
            archivo_ruta = Path(SENTENCIAS_BASE_DIR + unquote(item["url"][len(SENTENCIAS_GCS_BASE_URL) :]))

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

            # Definir los datos RAG a enviar
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

            # Enviar los datos RAG
            try:
                respuesta = requests.put(
                    url=f"{API_BASE_URL}/api/v5/sentencias/rag",
                    headers={"Authorization": f"Bearer {oauth2_token}"},
                    data=json.dumps(data),
                    timeout=TIMEOUT,
                )
            except requests.exceptions.RequestException as error:
                click.echo(click.style(str(error), fg="red"))
                sys.exit(1)
            if respuesta.status_code != 200:
                click.echo(click.style(str(respuesta.content), fg="red"))
                sys.exit(1)

            # Si hubo un error
            resultado = respuesta.json()
            if resultado["success"] is False:
                click.echo(click.style(resultado["message"], fg="yellow"))
                continue

            # Incrementar el contador
            contador += 1
            click.echo(click.style("ENVIADO", fg="white"))

        # Incrementar el offset y terminar el bucle si lo rebasamos
        offset += LIMIT
        if offset >= contenido["total"]:
            break

    # Mostrar el mensaje de término
    click.echo(click.style(f"Fueron analizadas {contador} sentencias", fg="green"))


@click.command()
@click.argument("creado_desde", type=str)
@click.argument("creado_hasta", type=str)
@click.option("--sobreescribir", is_flag=True)
def sintetizar(creado_desde, creado_hasta, sobreescribir):
    """Sintetizar sentencias"""
    click.echo("Sintetizando sentencias")

    # Validar que exista el directorio SENTENCIAS_BASE_DIR
    sentencias_dir = Path(SENTENCIAS_BASE_DIR)
    if sentencias_dir.exists() is False or sentencias_dir.is_dir() is False:
        click.echo(click.style(f"No existe el directorio {SENTENCIAS_BASE_DIR}", fg="red"))
        sys.exit(1)

    # Inicializar OpenAI
    open_ai = OpenAI(
        api_key=OPENAI_API_KEY,
        base_url=OPENAI_ENDPOINT,
        organization=OPENAI_ORG_ID,
        project=OPENAI_PROJECT_ID,
        timeout=60,
    )

    # Obtener el token
    try:
        oauth2_token = get_auth_token()
    except Exception as error:
        click.echo(click.style(str(error), fg="red"))
        sys.exit(1)

    # Inicializar el contador y el offset
    contador = 0
    offset = 0

    # Bucle por las consultas
    while True:

        # Consultar las sentencias
        try:
            respuesta = requests.get(
                url=f"{API_BASE_URL}/api/v5/sentencias",
                headers={"Authorization": f"Bearer {oauth2_token}"},
                params={"creado_desde": creado_desde, "creado_hasta": creado_hasta, "limit": LIMIT},
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

        # Bucle por los datos
        for item in contenido["data"]:
            click.echo(click.style(f"[{item['id']}] ", fg="white"), nl=False)

            # Si NO ha sido analizada, se omite
            if sobreescribir is False and item["rag_fue_analizado_tiempo"] is None:
                click.echo(click.style("Se omite porque aun NO se ha analizado", fg="yellow"))
                continue

            # Si ya fue sintetizada, se omite
            if sobreescribir is False and item["rag_fue_sintetizado_tiempo"] is not None:
                click.echo(click.style("Se omite porque ya fue sintetizado", fg="yellow"))
                continue

            # Consultar por su ID para obtener su texto
            try:
                respuesta = requests.get(
                    url=f"{API_BASE_URL}/api/v5/sentencias/{item['id']}",
                    headers={"Authorization": f"Bearer {oauth2_token}"},
                    timeout=TIMEOUT,
                )
            except requests.exceptions.RequestException as error:
                click.echo(click.style(str(error), fg="red"))
                sys.exit(1)
            if respuesta.status_code != 200:
                click.echo(click.style(str(respuesta), fg="red"))
                sys.exit(1)
            detalle = respuesta.json()

            # Validar que tiene el texto
            sentencia = detalle["data"]
            if "texto" not in sentencia["rag_analisis"]:
                click.echo(click.style("No tiene 'texto' el análisis", fg="yellow"))
                continue
            texto = sentencia["rag_analisis"]["texto"]
            if texto.strip() == "":
                click.echo(click.style("No tiene texto, está vacío", fg="yellow"))
                continue

            # Mostrar en pantalla la longitud de caracteres
            click.echo(click.style(f"Longitud {len(texto)} ", fg="green"), nl=False)

            # Definir los mensajes a enviar a OpenAI
            mensajes = [
                {"role": "system", "content": OPENAI_PROMPT},
                {"role": "user", "content": texto},
            ]

            # Enviar a OpenAI el texto
            try:
                chat_response = open_ai.chat.completions.create(
                    model=OPENAI_MODEL,
                    messages=mensajes,
                    stream=False,
                )
            except Exception as error:
                click.echo(click.style(f"Error al sintetizar: {str(error)}", fg="yellow"))
                continue

            # Definir los datos RAG a enviar
            data = {
                "id": item["id"],
                "analisis": None,
                "sintesis": {
                    "modelo": chat_response.model,
                    "sintesis": chat_response.choices[0].message.content,
                    "tokens_total": chat_response.usage.total_tokens,
                },
                "categorias": None,
            }

            # Mostrar en pantalla e total de tokens
            click.echo(click.style(f"Tokens {data['sintesis']['tokens_total']} ", fg="magenta"), nl=False)

            # Enviar los datos RAG
            try:
                respuesta = requests.put(
                    url=f"{API_BASE_URL}/api/v5/sentencias/rag",
                    headers={"Authorization": f"Bearer {oauth2_token}"},
                    data=json.dumps(data),
                    timeout=TIMEOUT,
                )
            except requests.exceptions.RequestException as error:
                click.echo(click.style(str(error), fg="red"))
                sys.exit(1)
            if respuesta.status_code != 200:
                click.echo(click.style(str(respuesta.content), fg="red"))
                sys.exit(1)

            # Si hubo un error
            resultado = respuesta.json()
            if resultado["success"] is False:
                click.echo(click.style(resultado["message"], fg="yellow"))
                continue

            # Incrementar el contador
            contador += 1
            click.echo(click.style("ENVIADO", fg="white"))

        # Incrementar el offset y terminar el bucle si lo rebasamos
        offset += LIMIT
        if offset >= contenido["total"]:
            break

    # Mostrar el mensaje de término
    click.echo(click.style(f"Fueron sintetizadas {contador} sentencias", fg="green"))


cli.add_command(analizar)
cli.add_command(sintetizar)
