# 🏗️ Bloquera Tonka - Despliegue en Render

## ✅ Ventajas de Render sobre Vercel para esta app

| Característica | Render | Vercel |
|---------------|--------|--------|
| SQLite (base de datos) | ✅ Funciona perfecto | ❌ Se reinicia |
| Archivos PDF guardados | ✅ Persisten en disco | ❌ Se borran |
| Flask nativo | ✅ Soporte completo | ⚠️ Serverless |
| Disco persistente | ✅ 1GB gratis | ❌ No tiene |

## 🚀 Pasos para subir a Render

### 1. Crear cuenta en Render
- Ve a https://render.com
- Regístrate con tu email o GitHub

### 2. Subir el proyecto

#### Opción A: Con GitHub (recomendado)
```bash
# Inicializar repositorio
git init

# Agregar todos los archivos
git add .

# Commit
git commit -m "Bloquera Tonka para Render"

# Crear repo en GitHub y subir
git remote add origin https://github.com/TU_USUARIO/bloquera-tonka.git
git push -u origin main
```

Luego en Render:
1. Click en **"New +"** → **"Web Service"**
2. Conecta tu repositorio de GitHub
3. Render detectará automáticamente Python/Flask

#### Opción B: Subir ZIP directamente
1. Ve a https://render.com
2. Click en **"New +"** → **"Web Service"**
3. Selecciona **"Upload ZIP"** o arrastra el archivo
4. Selecciona **Python** como runtime

### 3. Configurar el servicio

| Campo | Valor |
|-------|-------|
| **Name** | bloquera-tonka |
| **Runtime** | Python 3 |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `gunicorn app:app --bind 0.0.0.0:$PORT --workers 1 --timeout 120` |
| **Plan** | Free |

### 4. Agregar disco persistente (IMPORTANTE)

Para que SQLite guarde los datos permanentemente:

1. En tu servicio, ve a **"Disks"**
2. Click en **"Add Disk"**
3. Configura:
   - **Name**: `bloquera-data`
   - **Mount Path**: `/opt/render/project/src`
   - **Size**: 1 GB (gratis)

### 5. Deploy

Click en **"Create Web Service"** y espera unos minutos.

Tu app estará en: `https://bloquera-tonka.onrender.com`

---

## 📁 Estructura del proyecto

```
bloquera-tonka/
├── app.py              # Backend Flask
├── requirements.txt    # Dependencias Python
├── Procfile           # Comando de inicio
├── render.yaml        # Configuración Blueprint (opcional)
├── templates/
│   └── index.html      # Frontend principal
└── static/
    ├── css/style.css   # Estilos
    ├── js/app.js       # Lógica JavaScript
    ├── manifest.json   # Config PWA
    ├── service-worker.js
    └── icons/          # Iconos
```

## 🔑 Usuarios de prueba

| Usuario | Contraseña | Rol |
|---------|-----------|-----|
| admin | admin123 | Administrador (acceso total) |
| operario | operario123 | Operario (producción e inventario) |

## ⚠️ Notas importantes

- **Plan Free**: La app se "duerme" después de 15 min de inactividad. Se despierta automáticamente al entrar (tarda ~30 segundos).
- **Datos persistentes**: Con el disco configurado, tu base de datos SQLite y facturas PDF se guardan permanentemente.
- **Backups**: Exporta tu `database.db` periódicamente como respaldo.

## 🔄 Actualizar la app

Si usas GitHub, solo haz `git push` y Render se actualiza automáticamente.
