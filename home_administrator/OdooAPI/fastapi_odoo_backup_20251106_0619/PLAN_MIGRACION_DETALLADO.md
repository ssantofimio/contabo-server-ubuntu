# 🚀 Plan de Migración Detallado - FastAPI Full-Stack Template

## 📋 **Resumen de la Migración:**
**Objetivo**: Migrar el proyecto FastAPI-Admin actual al Full-Stack Template para obtener interfaz administrativa moderna en español nativo.

## 🎯 **Componentes a Migrar:**

### **1. Router de Odoo (CÓDIGO EXISTENTE) ✅**
**Ubicación actual**: `app/routers/odoo.py` → **Nueva ubicación**: `backend/app/api/routes/odoo.py`

**Endpoints a migrar:**
- `GET /api/odoo/version` → `GET /api/v1/odoo/version`
- `GET /api/odoo/partners?limit=10` → `GET /api/v1/odoo/partners?limit=10`
- `GET /api/odoo/products?limit=10` → `GET /api/v1/odoo/products?limit=10`

### **2. Configuración de Odoo (CÓDIGO EXISTENTE) ✅**
**Fuente**: `.env` actual
```bash
ODDO_HOST=odoo17.sasqcorp.com
ODDO_PORT=443
ODDO_DB=sarupetrol
ODDO_USER=coordinadordatos@sarupetrol.com
ODDO_PASSWORD=Pruebas1234*
```

### **3. Credenciales de Admin (NUEVAS) ✅**
```bash
FIRST_SUPERUSER=admin@sarupetrol.com
FIRST_SUPERUSER_PASSWORD=Admin123*
```

## 🔄 **Proceso de Migración - 6 Pasos:**

### **Paso 1: Backup del Proyecto Actual**
```bash
cp -r fastapi_odoo fastapi_odoo_backup_$(date +%Y%m%d_%H%M)
```

### **Paso 2: Configurar Template Base**
```bash
cd ../fastapi_template
cp -r backend ../fastapi_odoo_migrated
cd ../fastapi_odoo_migrated
```

### **Paso 3: Migrar Configuraciones**
- Copiar credenciales Odoo a `.env`
- Configurar base de datos PostgreSQL
- Configurar CORS para frontend local

### **Paso 4: Migrar Router de Odoo**
- Copiar `app/routers/odoo.py` → `backend/app/api/routes/odoo.py`
- Actualizar imports y dependencias
- Agregar al router principal

### **Paso 5: Configurar Frontend**
- Habilitar español en React i18n
- Configurar proxies para APIs de Odoo
- Personalizar interfaz administrativa

### **Paso 6: Testing y Deploy**
- Testing de APIs migradas
- Testing de autenticación JWT
- Deploy con Docker Compose

## 📊 **Tiempo Estimado por Paso:**
- **Paso 1**: 5 min (backup)
- **Paso 2**: 10 min (configuración base) 
- **Paso 3**: 15 min (migración configuraciones)
- **Paso 4**: 20 min (migrar router)
- **Paso 5**: 30 min (configurar frontend)
- **Paso 6**: 20 min (testing y deploy)
- **Total**: ~100 minutos (1.5 horas)

## 🎁 **Beneficios Post-Migración:**
- ✅ **Interfaz 100% en español nativo**
- ✅ **React moderno con TypeScript**
- ✅ **Autenticación JWT robusta**
- ✅ **Base de datos PostgreSQL**
- ✅ **Docker para producción**
- ✅ **Tests automatizados**
- ✅ **Documentación automática**
- ✅ **UI components modernos**
- ✅ **Escalabilidad profesional**

## 🔧 **Archivos que NO cambian:**
- ✅ `.env` (solo agregar variables nuevas)
- ✅ **Credenciales Odoo** (exactamente iguales)
- ✅ **Lógica de negocio** (router Odoo intacto)

## 🚀 **Comandos de Migración:**
```bash
# 1. Backup
cp -r fastapi_odoo fastapi_odoo_backup

# 2. Configurar template  
cp -r ../fastapi_template/backend fastapi_odoo_migrated
cd fastapi_odoo_migrated

# 3. Migrar configuraciones
cp ../fastapi_odoo/.env .env
echo "FIRST_SUPERUSER=admin@sarupetrol.com" >> .env
echo "FIRST_SUPERUSER_PASSWORD=Admin123*" >> .env

# 4. Migrar router
cp ../fastapi_odoo/app/routers/odoo.py backend/app/api/routes/

# 5. Testing
docker-compose up -d
curl http://localhost:8000/api/v1/odoo/version