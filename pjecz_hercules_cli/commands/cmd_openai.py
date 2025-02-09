"""
Command OpenAI
"""

import os
import sys

import click
from dotenv import load_dotenv
from openai import OpenAI

from pjecz_hercules_cli.dependencies.exceptions import MyAnyError
from pjecz_hercules_cli.dependencies.pdf_tools import extraer_texto_de_archivo_pdf

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_ENDPOINT = os.getenv("OPENAI_ENDPOINT")
OPENAI_MODEL = os.getenv("OPENAI_MODEL")
OPENAI_ORG_ID = os.getenv("OPENAI_ORG_ID")
OPENAI_PROJECT_ID = os.getenv("OPENAI_PROJECT_ID")
OPENAI_PROMPT = os.getenv("OPENAI_PROMPT")


@click.group()
def cli():
    """OpenAI"""


@click.command()
@click.argument("pregunta", type=str)
def preguntar(pregunta):
    """Hacer una pregunta para probar la comunicación"""
    click.echo("Hacer una pregunta para probar la comunicación")

    # Mostrar la pregunta
    click.echo(click.style("Pregunta: ", fg="green"), nl=False)
    click.echo(click.style(pregunta, fg="white"))

    # Inicializar OpenAI
    open_ai = OpenAI(
        api_key=OPENAI_API_KEY,
        base_url=OPENAI_ENDPOINT,
        organization=OPENAI_ORG_ID,
        project=OPENAI_PROJECT_ID,
        timeout=60,
    )

    # Definir los mensajes que se va a enviar
    mensajes = []
    if OPENAI_PROMPT != "":
        mensajes.append({"role": "system", "content": OPENAI_PROMPT})
    mensajes.append({"role": "user", "content": pregunta})

    # Enviar los mensajes
    try:
        response = open_ai.chat.completions.create(
            model=OPENAI_MODEL,
            messages=mensajes,
            stream=False,
        )
    except Exception as error:
        click.echo(click.style(str(error), fg="red"))
        sys.exit(1)

    # Mostrar la respuesta
    click.echo(click.style("Respuesta: ", fg="green"), nl=False)
    click.echo(click.style(response.choices[0].message.content, fg="white"))


@click.command()
@click.argument("archivo", type=str)
def extraer(archivo):
    """Extraer el texto de un archivo PDF"""
    click.echo("Extrayendo el texto de un archivo PDF")

    # Extraer el texto
    try:
        texto = extraer_texto_de_archivo_pdf(archivo)
    except MyAnyError as error:
        click.echo(click.style(str(error), fg="yellow"))
        sys.exit(1)

    # Mostrar el texto en pantalla
    click.echo(click.style("Texto: ", fg="green"), nl=False)
    click.echo(texto)


@click.command()
@click.argument("archivo", type=str)
def sintetizar(archivo):
    """Sintetizar el texto de un archivo PDF"""
    click.echo("Sintetizando el texto de un archivo PDF")

    # Extraer el texto
    try:
        texto = extraer_texto_de_archivo_pdf(archivo)
    except MyAnyError as error:
        click.echo(click.style(str(error), fg="yellow"))
        sys.exit(1)

    # Inicializar OpenAI
    open_ai = OpenAI(
        api_key=OPENAI_API_KEY,
        base_url=OPENAI_ENDPOINT,
        organization=OPENAI_ORG_ID,
        project=OPENAI_PROJECT_ID,
        timeout=60,
    )

    # Definir los mensajes a enviar
    mensajes = [
        {"role": "system", "content": OPENAI_PROMPT},
        {"role": "user", "content": texto},
    ]

    # Sintetizar con OpenAI
    try:
        chat_response = open_ai.chat.completions.create(
            model=OPENAI_MODEL,
            messages=mensajes,
            stream=False,
        )
        sintetizado = chat_response.choices[0].message.content
    except Exception as error:
        click.echo(click.style("Error al sintetizar: " + str(error), fg="yellow"))
        sys.exit(1)

    # Mostrar la síntesis en pantalla
    click.echo(click.style("Texto: ", fg="green"), nl=False)
    click.echo(sintetizado)


cli.add_command(preguntar)
cli.add_command(extraer)
cli.add_command(sintetizar)
