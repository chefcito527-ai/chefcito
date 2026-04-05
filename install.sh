#!/bin/bash

# Script de instalación para PythonAnywhere
# Ejecuta: bash install.sh

echo "Instalando dependencias..."

# Crear entorno virtual si no existe
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

# Activar entorno virtual
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt

echo "Instalación completada."
echo "Recuerda configurar las variables de entorno en el panel Web de PythonAnywhere:"
echo "- DATABASE_URL"
echo "- SECRET_KEY"