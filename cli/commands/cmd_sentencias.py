"""
Sentencias
"""

import os
import sys

import click


@click.group()
def cli():
    """Sentencias"""


@cli.command()
def analizar():
    """Analizar una sentencia"""
    click.echo("Analizando una sentencia")


@cli.command()
def sintetizar():
    """Sintetizar una sentencia"""
    click.echo("Sintetizando una sentencia")


@cli.command()
def categorizar():
    """Categorizar una sentencia"""
    click.echo("Categorizando una sentencia")
