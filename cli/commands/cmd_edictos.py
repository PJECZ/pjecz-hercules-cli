"""
Cmd Edictos

- analizar
- sintetizar
"""

import os
import sys

import click


@click.group()
def cli():
    """Edictos"""


@click.command()
def analizar():
    """Analizar un edicto"""
    click.echo("Analizando un edicto")


@click.command()
def sintetizar():
    """Sintetizar un edicto"""
    click.echo("Sintetizando un edicto")


cli.add_command(analizar)
cli.add_command(sintetizar)
