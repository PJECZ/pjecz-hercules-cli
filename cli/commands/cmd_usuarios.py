"""
Cmd Usuarios

- exportar: Exportar Usuarios a un archivo CSV con
    - distrito_nombre_corto
    - autoridad_descripcion_corta
    - usuario_email
    - directorio_edictos
"""

import csv
import os
import sys

import click
from dotenv import load_dotenv
import requests

from lib.authentications import get_auth_token

load_dotenv()
API_BASE_URL = os.getenv("API_BASE_URL")
LIMIT = int(os.getenv("LIMIT"))
TIMEOUT = int(os.getenv("TIMEOUT"))


@click.group()
def cli():
    """Usuarios"""


@click.command()
@click.argument("archivo_csv", type=click.Path(exists=False))
@click.option("--jurisdiccionales", is_flag=True, help="Solo Jurisdiccionales")
@click.option("--notarias", is_flag=True, help="Solo Notarías")
def exportar(archivo_csv, jurisdiccionales, notarias):
    """Exportar Usuarios a un archivo CSV"""

    # Banderas
    es_jurisdiccional = 1 if jurisdiccionales else 0
    es_notaria = 1 if notarias else 0

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
        encabezados = ["distrito_nombre_corto", "autoridad_descripcion_corta", "usuario_email", "directorio_edictos"]
        escritor = csv.DictWriter(puntero, fieldnames=encabezados)
        escritor.writeheader()

        # Consultar las autoridades
        autoridades_offset = 0
        while True:
            autoridades_params = {
                "es_jurisdiccional": es_jurisdiccional,
                "es_notaria": es_notaria,
                "limit": LIMIT,
                "offset": autoridades_offset,
            }
            try:
                respuesta = requests.get(
                    url=f"{API_BASE_URL}/api/v5/autoridades",
                    headers={"Authorization": f"Bearer {oauth2_token}"},
                    params=autoridades_params,
                    timeout=TIMEOUT,
                )
            except requests.exceptions.RequestException as error:
                click.echo(click.style(str(error), fg="red"))
                sys.exit(1)
            if respuesta.status_code != 200:
                click.echo(click.style(str(respuesta), fg="red"))
                sys.exit(1)
            autoridades_contenido = respuesta.json()
            if autoridades_contenido["success"] is False:
                click.echo(click.style(autoridades_contenido["message"], fg="red"))
                sys.exit(1)

            # Bucle por cada autoridad
            for autoridad_item in autoridades_contenido["data"]:

                # Consultar los usuarios de la autoridad
                usuarios_offset = 0
                while True:
                    usuarios_params = {"autoridad_clave": autoridad_item["clave"], "limit": LIMIT, "offset": usuarios_offset}
                    try:
                        respuesta = requests.get(
                            url=f"{API_BASE_URL}/api/v5/usuarios",
                            headers={"Authorization": f"Bearer {oauth2_token}"},
                            params=usuarios_params,
                            timeout=TIMEOUT,
                        )
                    except requests.exceptions.RequestException as error:
                        click.echo(click.style(str(error), fg="red"))
                        sys.exit(1)
                    if respuesta.status_code != 200:
                        click.echo(click.style(str(respuesta), fg="red"))
                        sys.exit(1)
                    usuarios_contenido = respuesta.json()
                    if usuarios_contenido["success"] is False:
                        click.echo(
                            click.style(f"[{autoridad_item['clave']} {usuarios_contenido['message']}]", fg="yellow"), nl=False
                        )
                        break  # No se encontraron

                    # Bucle por cada usuario
                    for item in usuarios_contenido["data"]:
                        escritor.writerow(
                            {
                                "distrito_nombre_corto": autoridad_item["distrito_nombre_corto"],
                                "autoridad_descripcion_corta": autoridad_item["descripcion_corta"],
                                "usuario_email": item["email"],
                                "directorio_edictos": autoridad_item["directorio_edictos"],
                            }
                        )
                        contador += 1
                        click.echo(click.style("+", fg="green"), nl=False)

                    # Incrementar el offset para obtener los siguientes resultados
                    usuarios_offset += LIMIT
                    if usuarios_offset > usuarios_contenido["total"]:
                        break  # Salir del bucle

            # Incrementar el offset para obtener los siguientes resultados
            autoridades_offset += LIMIT
            if autoridades_offset > autoridades_contenido["total"]:
                break  # Salir del bucle

    # Mostrar el mensaje de término
    click.echo(click.style(f"Fueron agregadas {contador} usuarios a {archivo_csv}", fg="green"))


cli.add_command(exportar)
