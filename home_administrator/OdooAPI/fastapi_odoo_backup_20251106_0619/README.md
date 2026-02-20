# Odoo API Integration with FastAPI-Admin

Este proyecto integra FastAPI con FastAPI-Admin para consumir y gestionar datos del API de Odoo.

## Estructura del Proyecto

```
fastapi_odoo/
├── app/
│   ├── __init__.py
│   ├── main.py          # Punto de entrada principal
│   ├── config.py        # Configuraciones de la aplicación
│   ├── routers/
│   │   └── odoo.py      # Endpoints para consumir Odoo API
│   └── admin/
│       ├── __init__.py
│       ├── config.py    # Configuración de FastAPI-Admin
│       ├── models.py    # Modelos para el admin
│       └── resources.py # Recursos del admin
├── templates/           # Templates para FastAPI-Admin
├── static/              # Archivos estáticos
├── requirements.txt     # Dependencias
├── .env                 # Variables de entorno
└── run.py               # Script para ejecutar la aplicación
```

## Instalación y Ejecución

1. Activar entorno virtual:
   ```bash
   source venv/bin/activate
   ```

2. Instalar dependencias:
   ```bash
   pip install -r requirements.txt
   ```

3. Ejecutar la aplicación:
   ```bash
   python run.py
   ```

## Acceso

- API: http://localhost:8020
- Documentación API: http://localhost:8020/docs
- Panel Admin: http://localhost:8020/admin

## Endpoints Disponibles

- `GET /api/version` - Obtener versión de Odoo
- `GET /api/partners` - Listar partners
- `GET /api/products` - Listar productos