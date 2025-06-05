#!/bin/bash
# Ruta absoluta a tu proyecto
PROJECT_PATH="/home/administrador/BackApp/backend-app-test"

# Da permisos de lectura y ejecución a todos
chmod -R o+rX "$PROJECT_PATH/staticfiles"
chmod -R o+rX "$PROJECT_PATH/media"


# Da permisos de ejecución a los directorios necesarios
chmod o+x /home
chmod o+x /home/administrador
chmod o+x /home/administrador/BackApp
chmod o+x /home/administrador/BackApp/backend-app-test
