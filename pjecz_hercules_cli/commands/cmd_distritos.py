"""
Command Distritos
"""

import os
import sys

import click
from dotenv import load_dotenv
import requests
from tabulate import tabulate

from pjecz_hercules_cli.dependencies.authentications import get_auth_token

load_dotenv()
API_BASE_URL = os.getenv("API_BASE_URL")
LIMIT = int(os.getenv("LIMIT"))
TIMEOUT = int(os.getenv("TIMEOUT"))


@click.group()
def cli():
    """Distritos"""


@click.command()
def mostrar():
    """Mostrar los distritos"""

    # Obtener el token
    try:
        oauth2_token = get_auth_token()
    except Exception as error:
        click.echo(click.style(str(error), fg="red"))
        sys.exit(1)

    # Consultar
    try:
        respuesta = requests.get(
            url=f"{API_BASE_URL}/api/v5/distritos",
            headers={"Authorization": f"Bearer {oauth2_token}"},
            params={"limit": LIMIT},
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

    # Mostrar la tabla con los datos de los distritos
    tabla = []
    encabezados = ["clave", "nombre_corto", "nombre", "es_jurisdiccional"]
    for item in contenido["data"]:
        tabla.append([item[encabezado] for encabezado in encabezados])
    click.echo(tabulate(tabla, headers=encabezados))


cli.add_command(mostrar)
