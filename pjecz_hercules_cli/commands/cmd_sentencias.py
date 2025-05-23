"""
Command Sentencias
"""

import concurrent.futures
import json
from pathlib import Path
import os
import sys
from urllib.parse import unquote

import click
from dotenv import load_dotenv
from openai import OpenAI
import requests
from tqdm import tqdm

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
SENTENCIAS_BASE_DIR = os.getenv("SENTENCIAS_BASE_DIR")
SENTENCIAS_GCS_BASE_URL = os.getenv("SENTENCIAS_GCS_BASE_URL")
MOSTRAR_CARACTERES = int(os.getenv("MOSTRAR_CARACTERES"))

HILOS_POR_DEFECTO = os.cpu_count() or 4


@click.group()
def cli():
    """Sentencias"""


def analizar_archivo_pdf_hilo(id: int, archivo_ruta: Path, autor: str) -> (int, str, int):
    """Analizar un archivo PDF en un hilo, entrega el ID, el texto extraído, el tamaño del archivo y el autor"""
    if bool(archivo_ruta.exists() and archivo_ruta.is_file()) is False:
        raise MyAnyError(f"El archivo {archivo_ruta} no existe o no es un archivo")
    try:
        texto = extraer_texto_de_archivo_pdf(str(archivo_ruta))
    except MyAnyError as error:
        raise MyAnyError(f"Error al extraer texto del archivo {archivo_ruta.name}: {str(error)}") from error
    if texto.strip() == "":
        raise MyAnyError(f"El archivo {archivo_ruta.name} no tiene texto")
    return id, texto, os.path.getsize(archivo_ruta), autor


def enviar_analisis_rag(id: int, texto: str, archivo_tamanio: int, autor: str, oauth2_token: str) -> bool:
    """Enviar el análisis RAG a la API"""
    data = {
        "id": id,
        "analisis": {
            "archivo_tamanio": archivo_tamanio,
            "autor": autor,
            "longitud": len(texto),
            "texto": texto,
        },
        "sintesis": None,
        "categorias": None,
    }
    try:
        respuesta = requests.put(
            url=f"{API_BASE_URL}/api/v5/sentencias/rag",
            headers={"Authorization": f"Bearer {oauth2_token}"},
            data=json.dumps(data),
            timeout=TIMEOUT,
        )
    except requests.exceptions.RequestException as error:
        raise MyAnyError(error) from error
    if respuesta.status_code != 200:
        raise MyAnyError(f"Status Code {respuesta.status_code}: {respuesta.content}")
    contenido = respuesta.json()
    if "success" not in contenido or "message" not in contenido:
        raise MyAnyError(f"Respuesta inesperada: {contenido}")
    return bool(contenido["success"])


@click.command()
@click.argument("creado_desde", type=str)
@click.argument("creado_hasta", type=str)
@click.option("--hilos", type=int, default=HILOS_POR_DEFECTO, help="Número de hilos a usar")
@click.option("--probar", is_flag=True, help="Modo de prueba, sin cambios")
@click.option("--sobreescribir", is_flag=True, help="Sobreescribe lo ya analizado")
def analizar(creado_desde, creado_hasta, hilos, probar, sobreescribir):
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

        # Consultar sentencias
        try:
            respuesta = requests.get(
                url=f"{API_BASE_URL}/api/v5/sentencias",
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

        # Inicializar la lista de futuros
        futures = []

        # Usar ThreadPoolExecutor para manejar múltiples hilos
        with concurrent.futures.ThreadPoolExecutor(max_workers=hilos) as executor:
            # Bucle por los registros de la consulta
            for item in paginado["data"]:
                # Si ya fue analizada, se omite
                if sobreescribir is False and item["rag_fue_analizado_tiempo"] is not None:
                    continue

                # Definir la ruta al archivo pdf reemplazando el inicio del url con el directorio
                archivo_ruta = Path(SENTENCIAS_BASE_DIR + unquote(item["url"][len(SENTENCIAS_GCS_BASE_URL) :]))

                # Entregar las tareas al multi hilo para extraer los textos de los archivos PDF en paralelo
                future = executor.submit(analizar_archivo_pdf_hilo, item["id"], archivo_ruta, item["autoridad_clave"])
                futures.append(future)

            # Bucle por los resultados de los hilos
            for future in tqdm(concurrent.futures.as_completed(futures), total=len(futures), desc="Analizando archivos PDF"):
                try:
                    id, texto, archivo_tamanio, autor = future.result()
                    if probar is False:
                        enviar_analisis_rag(id, texto, archivo_tamanio, autor, oauth2_token)
                except MyAnyError as error:
                    click.echo(click.style(str(error), fg="yellow"))
                    continue
                contador += 1

        # Incrementar el offset y terminar el bucle si lo rebasamos
        offset += LIMIT
        if offset >= paginado["total"]:
            break

    # Mostrar el mensaje de término
    click.echo(click.style(f"Fueron analizadas {contador} de {paginado['total']} sentencias", fg="green"))


@click.command()
@click.argument("creado_desde", type=str)
@click.argument("creado_hasta", type=str)
@click.option("--probar", is_flag=True, help="Modo de prueba, sin cambios")
@click.option("--sobreescribir", is_flag=True, help="Sobreescribe lo ya sintetizado")
def sintetizar(creado_desde, creado_hasta, probar, sobreescribir):
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

        # Consultar sentencias
        try:
            respuesta = requests.get(
                url=f"{API_BASE_URL}/api/v5/sentencias",
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
            if probar is False:
                click.echo(click.style("ENVIADO", fg="white"))
            else:
                click.echo(click.style("PROBADO", fg="white"))

        # Incrementar el offset y terminar el bucle si lo rebasamos
        offset += LIMIT
        if offset >= paginado["total"]:
            break

    # Mostrar el mensaje de término
    click.echo(click.style(f"Fueron sintetizadas {contador} sentencias", fg="green"))


cli.add_command(analizar)
cli.add_command(sintetizar)
