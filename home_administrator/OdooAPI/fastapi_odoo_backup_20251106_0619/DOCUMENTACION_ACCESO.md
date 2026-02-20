# 🔐 Documentación de Acceso - FastAPI-Admin con Autenticación Odoo

## 🚀 **Estado del Sistema**
- ✅ **Servidor funcionando**: http://45.85.249.203:8020
- ✅ **FastAPI-Admin activo**: http://45.85.249.203:8020/admin
- ✅ **Login automático**: http://45.85.249.203:8020/admin/login
- ✅ **Autenticación Odoo**: Configurada y activa

## 🔑 **Credenciales de Acceso**

### **Configuración Odoo (Archivo `.env`)**
```
ODDO_HOST=odoo17.sasqcorp.com
ODDO_PORT=443
ODDO_DB=sarupetrol
ODDO_USER=coordinadordatos@sarupetrol.com
ODDO_PASSWORD=Pruebas1234*
```

## 🔒 **Cómo Iniciar Sesión**

### **1. Acceder al Panel de Admin**
- **URL**: http://45.85.249.203:8020/admin
- **Redirect**: Automáticamente te lleva al login

### **2. Usar Credenciales de Odoo**
- **Usuario**: Email del usuario en Odoo (ej: `coordinadordatos@sarupetrol.com`)
- **Contraseña**: La contraseña del usuario en Odoo

### **3. Ejemplo de Login**
```
Usuario: coordinadordatos@sarupetrol.com
Contraseña: [Tu contraseña de Odoo]
```

## 🏗️ **Funcionalidades Implementadas**

### **🔗 Conexión con Odoo**
- ✅ **Autenticación directa** contra base de datos de Odoo
- ✅ **Validación de usuarios** activos
- ✅ **Roles y permisos** de Odoo
- ✅ **Gestión de sesiones** con Redis

### **🛡️ Seguridad**
- ✅ **Credenciales seguras**: No expuestas en código
- ✅ **Validación robusta**: Solo usuarios activos de Odoo
- ✅ **Tokens seguros**: Acceso controlado
- ✅ **Fallback Redis**: En caso de no tener Redis real

### **📊 Panel de Administración**
- ✅ **Interfaz completa** con FastAPI-Admin
- ✅ **Gestión de usuarios** desde Odoo
- ✅ **Logs de actividad** automáticos
- ✅ **API disponible** en `/api/`

## 🛠️ **APIs Disponibles**

### **Documentación API**
- **Swagger UI**: http://45.85.249.203:8020/docs
- **ReDoc**: http://45.85.249.203:8020/redoc

### **Endpoints Principales**
- `GET /` - Estado del sistema
- `GET /api/version` - Versión de la API
- `POST /api/odoo/[endpoint]` - Métodos de Odoo

## 🔧 **Comandos Útiles**

### **Verificar Estado del Servidor**
```bash
curl http://45.85.249.203:8020/
```

### **Ver Logs en Tiempo Real**
```bash
# Desde terminal del servidor
tail -f /var/log/fastapi.log
```

### **Reiniciar Servidor**
```bash
# Desde el directorio del proyecto
pkill -f "python3 run.py"
python3 run.py
```

## 🎯 **Próximos Pasos**

### **Para Desarrollar APIs de Odoo:**
1. **Usa el panel de admin** para entender la estructura
2. **Consulta la documentación** en `/docs`
3. **Usa las credenciales de Odoo** para autenticación
4. **Desarrolla endpoints** en `app/routers/`

### **Estructura del Proyecto:**
```
app/
├── auth/
│   └── odoo_provider.py    # 🔐 Autenticación Odoo
├── main.py                 # 🚀 App principal
├── config.py              # ⚙️ Configuración
├── routers/
│   └── odoo.py            # 📡 Endpoints Odoo
└── admin/                 # 👥 Panel admin
```

## 📞 **Soporte**
- **Servidor**: http://45.85.249.203:8020
- **Panel Admin**: http://45.85.249.203:8020/admin
- **API Docs**: http://45.85.249.203:8020/docs

---
*Sistema configurado y funcionando - FastAPI-Admin con Autenticación Odoo* 🎉