# pjecz-hercules-cli

CLI (Command Line Interface) para trabajar con RAG (Retrieval-Augmented Generation) y enviar los resultados a la API OAuth2 de Hercules

## Instalación

Crear el entorno virtual con **Python 3.11**

```bash
python3.11 -m venv .venv
```

Ingresar al entorno virtual

```bash
. .venv/bin/activate
```

Actualizar e instalar **poetry 2**

```bash
pip install --upgrade pip setuptools wheel poetry
```

Crear un archivo para las variables de entorno

```bash
nano .env
```

Escriba las siguientes variables cambiándolas a sus requerimientos

```ini
# Ollama
OPENAI_API_KEY="NONE"
OPENAI_ENDPOINT="http://127.0.0.1:11434/v1"
OPENAI_MODEL="llama3.2"
OPENAI_ORG_ID="NONE"
OPENAI_PROJECT_ID="NONE"
OPENAI_PROMPT=""

# API OAuth2
API_BASE_URL="http://localhost:8000"
USERNAME="nombre@servidor.com"
PASSWORD="XXXXXXXXXXXXXXXX"
LIMIT=100
TIMEOUT=20

# Edictos
EDICTOS_BASE_DIR="/mnt/unidad/archivista/Edictos"
EDICTOS_GCS_BASE_URL="https://storage.googleapis.com/XXXX/XXXX"

# Sentencias
SENTENCIAS_BASE_DIR="/mnt/unidad/archivista/Sentencias"
SENTENCIAS_GCS_BASE_URL="https://storage.googleapis.com/XXXX/XXXX"
```

Instalar en este entorno el comando `hercules`

```bash
pip install --editable .
```

Probar que funcione el CLI

```bash
hercules --help
```
