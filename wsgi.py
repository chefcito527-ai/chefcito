import sys
import os

# Ajusta esta ruta al directorio de tu proyecto en PythonAnywhere
# Ejemplo: /home/tu_usuario/chefcito
project_path = os.path.dirname(os.path.abspath(__file__))

if project_path not in sys.path:
    sys.path.insert(0, project_path)

from app import application
