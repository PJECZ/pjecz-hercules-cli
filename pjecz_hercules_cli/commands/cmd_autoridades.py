"""
Command Autoridades
"""

import csv
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
    """Autoridades"""


@click.command()
@click.argument("archivo_csv", type=click.Path(exists=False))
@click.option("--jurisdiccionales", is_flag=True, help="Solo Jurisdiccionales")
@click.option("--notarias", is_flag=True, help="Solo Notarías")
def exportar(archivo_csv, jurisdiccionales, notarias):
    """Exportar Autoridades a un archivo CSV"""

    # Obtener el token
    try:
        oauth2_token = get_auth_token()
    except Exception as error:
        click.echo(click.style(str(error), fg="red"))
        sys.exit(1)

    # Crear el archivo CSV
    contador = 0
    click.echo(click.style(f"Agregando líneas a {archivo_csv}: ", fg="white"), nl=False)
    with open(archivo_csv, mode="w", encoding="utf8") as puntero:
        escritor = csv.DictWriter(puntero, fieldnames=["clave", "directorio_edictos"])
        escritor.writeheader()

        # Banderas
        es_jurisdiccional = 1 if jurisdiccionales else 0
        es_notaria = 1 if notarias else 0

        # Consultar las autoridades
        offset = 0
        while True:
            try:
                respuesta = requests.get(
                    url=f"{API_BASE_URL}/api/v5/autoridades",
                    headers={"Authorization": f"Bearer {oauth2_token}"},
                    params={"es_jurisdiccional": es_jurisdiccional, "es_notaria": es_notaria, "limit": LIMIT, "offset": offset},
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

            # Bucle por cada autoridad
            for item in contenido["data"]:
                escritor.writerow(
                    {
                        "clave": item["clave"],
                        "directorio_edictos": item["directorio_edictos"],
                    }
                )
                contador += 1
                click.echo(click.style(f"[{item['clave']}] ", fg="green"), nl=False)

            # Incrementar el offset con el LIMIT para la siguiente consulta
            offset += LIMIT

            # Si ya llegamos al final de las consultas
            if offset > contenido["total"]:
                break  # Salir del bucle

    # Mostrar el mensaje de término
    click.echo(click.style(f"Fueron agregadas {contador} autoridades a {archivo_csv}", fg="green"))


@click.command()
@click.option("--notarias", is_flag=True, help="Solo Notarías")
def mostrar(notarias):
    """Mostrar tabla de autoridades"""

    # Obtener el token
    try:
        oauth2_token = get_auth_token()
    except Exception as error:
        click.echo(click.style(str(error), fg="red"))
        sys.exit(1)

    # Definir parámetros
    params = {"limit": LIMIT}
    if notarias:
        params["es_notaria"] = 1

    # Consultar
    try:
        respuesta = requests.get(
            url=f"{API_BASE_URL}/api/v5/autoridades",
            headers={"Authorization": f"Bearer {oauth2_token}"},
            params=params,
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
    encabezados = ["clave", "descripcion_corta", "es_notaria"]
    for item in contenido["data"]:
        tabla.append([item[encabezado] for encabezado in encabezados])
    click.echo(tabulate(tabla, headers=encabezados))


cli.add_command(exportar)
cli.add_command(mostrar)
