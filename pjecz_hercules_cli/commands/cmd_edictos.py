"""
Command Edictos
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
EDICTOS_BASE_DIR = os.getenv("EDICTOS_BASE_DIR")
EDICTOS_GCS_BASE_URL = os.getenv("EDICTOS_GCS_BASE_URL")
MOSTRAR_CARACTERES = int(os.getenv("MOSTRAR_CARACTERES"))


@click.group()
def cli():
    """Edictos"""


@click.command()
@click.argument("creado_desde", type=str)
@click.argument("creado_hasta", type=str)
@click.option("--probar", is_flag=True, help="Modo de prueba, sin cambios")
@click.option("--sobreescribir", is_flag=True, help="Sobreescribe lo ya analizado")
def analizar(creado_desde, creado_hasta, probar, sobreescribir):
    """Analizar edictos"""
    click.echo("Analizando edictos")

    # Validar que exista el directorio EDICTOS_BASE_DIR
    sentencias_dir = Path(EDICTOS_BASE_DIR)
    if sentencias_dir.exists() is False or sentencias_dir.is_dir() is False:
        click.echo(click.style(f"No existe el directorio {EDICTOS_BASE_DIR}", fg="red"))
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

        # Consultar edictos
        try:
            respuesta = requests.get(
                url=f"{API_BASE_URL}/api/v5/edictos",
                headers={"Authorization": f"Bearer {oauth2_token}"},
                params={"creado_desde": creado_desde, "creado_hasta": creado_hasta, "limit": LIMIT, "offset": offset},
                timeout=TIMEOUT,
            )
        except requests.exceptions.RequestException as error:
            click.echo(click.style(str(error), fg="red"))
            sys.exit(1)
        if respuesta.status_code != 200:
            click.echo(click.style(str(respuesta), fg="red"))
            sys.exit(1)
        paginado = respuesta.json()

        # Si hubo un error
        if paginado["success"] is False:
            click.echo(click.style(paginado["message"], fg="red"))
            sys.exit(1)

        # Bucle por los datos
        for item in paginado["data"]:
            click.echo(click.style(f"[{item['id']}] ", fg="white"), nl=False)

            # Si ya fue analizada, se omite
            if sobreescribir is False and item["rag_fue_analizado_tiempo"] is not None:
                click.echo(click.style("Se omite porque ya fue analizado", fg="yellow"))
                continue

            # Definir la ruta al archivo pdf reemplazando el inicio del url con el directorio
            archivo_ruta = Path(EDICTOS_BASE_DIR + unquote(item["url"][len(EDICTOS_GCS_BASE_URL) :]))

            # Verificar que exista el archivo pdf
            archivo_ruta_existe = bool(archivo_ruta.exists() and archivo_ruta.is_file())

            # Si NO existe se muestra en color amarillo y se omite, de lo contario se muestra en color verde
            if archivo_ruta_existe is False:
                click.echo(click.style(f"{item['archivo']} NO existe", fg="yellow"))
                continue
            click.echo(click.style(f"{item['archivo'][:20]}... ", fg="green"), nl=False)

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
            click.echo(click.style(f"{texto[:MOSTRAR_CARACTERES]}... = {len(texto)} ", fg="blue"), nl=False)

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

            # Si NO está en modo de pruebas
            if probar is False:
                # Enviar los datos RAG
                try:
                    respuesta = requests.put(
                        url=f"{API_BASE_URL}/api/v5/edictos/rag",
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
            if probar is False:
                click.echo(click.style("ENVIADO", fg="white"))
            else:
                click.echo(click.style("PROBADO", fg="white"))

        # Incrementar el offset y terminar el bucle si lo rebasamos
        offset += LIMIT
        if offset >= paginado["total"]:
            break

    # Mostrar el mensaje de término
    click.echo(click.style(f"Fueron analizadas {contador} edictos", fg="green"))


@click.command()
@click.argument("creado_desde", type=str)
@click.argument("creado_hasta", type=str)
@click.option("--probar", is_flag=True, help="Modo de prueba, sin cambios")
@click.option("--sobreescribir", is_flag=True, help="Sobreescribe lo ya sintetizado")
def sintetizar(creado_desde, creado_hasta, probar, sobreescribir):
    """Sintetizar edictos"""
    click.echo("Sintetizando edictos")

    # Validar que exista el directorio EDICTOS_BASE_DIR
    sentencias_dir = Path(EDICTOS_BASE_DIR)
    if sentencias_dir.exists() is False or sentencias_dir.is_dir() is False:
        click.echo(click.style(f"No existe el directorio {EDICTOS_BASE_DIR}", fg="red"))
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

        # Consultar edictos
        try:
            respuesta = requests.get(
                url=f"{API_BASE_URL}/api/v5/edictos",
                headers={"Authorization": f"Bearer {oauth2_token}"},
                params={"creado_desde": creado_desde, "creado_hasta": creado_hasta, "limit": LIMIT, "offset": offset},
                timeout=TIMEOUT,
            )
        except requests.exceptions.RequestException as error:
            click.echo(click.style(str(error), fg="red"))
            sys.exit(1)
        if respuesta.status_code != 200:
            click.echo(click.style(str(respuesta), fg="red"))
            sys.exit(1)
        paginado = respuesta.json()

        # Si hubo un error
        if paginado["success"] is False:
            click.echo(click.style(paginado["message"], fg="red"))
            sys.exit(1)

        # Bucle por los datos
        for item in paginado["data"]:
            click.echo(click.style(f"[{item['id']}] ", fg="white"), nl=False)

            # Si ya fue analizado, se omite
            if sobreescribir is False and item["rag_fue_analizado_tiempo"] is not None:
                click.echo(click.style("Se omite porque ya fue analizado", fg="yellow"))
                continue

            # Si ya fue sintetizado, se omite
            if sobreescribir is False and item["rag_fue_sintetizado_tiempo"] is not None:
                click.echo(click.style("Se omite porque ya fue sintetizado", fg="yellow"))
                continue

            # Consultar por su ID para obtener su texto
            try:
                respuesta = requests.get(
                    url=f"{API_BASE_URL}/api/v5/edictos/{item['id']}",
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

            # Si hubo un error
            contenido = respuesta.json()
            if contenido["success"] is False:
                click.echo(click.style(contenido["message"], fg="red"))
                sys.exit(1)

            # Validar que tiene el texto
            datos = detalle["data"]
            if datos is None:
                click.echo(click.style("No tiene 'data'", fg="yellow"))
                continue
            if "rag_analisis" not in datos or datos["rag_analisis"] is None:
                click.echo(click.style("No tiene 'rag_analisis' o es nulo", fg="yellow"))
                continue
            if "texto" not in datos["rag_analisis"] or datos["rag_analisis"]["texto"] is None:
                click.echo(click.style("No tiene 'texto' el análisis o es nulo", fg="yellow"))
                continue
            texto = datos["rag_analisis"]["texto"]
            if texto.strip() == "":
                click.echo(click.style("No hay texto para sintetizar, está vacío", fg="yellow"))
                continue

            # Mostrar en pantalla la longitud de caracteres
            click.echo(click.style(f"{texto[:MOSTRAR_CARACTERES]}… = {len(texto)} ", fg="blue"), nl=False)

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

            # Mostrar en pantalla un fragmento de la sintesis
            sintesis = chat_response.choices[0].message.content
            tokens_total = chat_response.usage.total_tokens
            click.echo(click.style(f"{sintesis[:MOSTRAR_CARACTERES]}… = {tokens_total} ", fg="magenta"), nl=False)

            # Definir los datos RAG a enviar
            data = {
                "id": item["id"],
                "analisis": None,
                "sintesis": {
                    "modelo": chat_response.model,
                    "sintesis": sintesis,
                    "tokens_total": tokens_total,
                },
                "categorias": None,
            }

            # Si NO está en modo de pruebas
            if probar is False:
                # Enviar los datos RAG
                try:
                    respuesta = requests.put(
                        url=f"{API_BASE_URL}/api/v5/edictos/rag",
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
            if probar is False:
                click.echo(click.style("ENVIADO", fg="white"))
            else:
                click.echo(click.style("PROBADO", fg="white"))

        # Incrementar el offset y terminar el bucle si lo rebasamos
        offset += LIMIT
        if offset >= paginado["total"]:
            break

    # Mostrar el mensaje de término
    click.echo(click.style(f"Fueron sintetizados {contador} edictos", fg="green"))


cli.add_command(analizar)
cli.add_command(sintetizar)
