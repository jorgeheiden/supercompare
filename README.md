# SuperCompare — DIA vs COTO 🛒⚖

Compará precios de productos entre supermercados DIA y COTO en tiempo real.

---

## Requisitos previos

Instalá estos programas **antes** de correr la app:

| Programa | Link de descarga | Versión mínima |
|----------|-----------------|----------------|
| **Python** | https://python.org/downloads | 3.10+ |
| **Node.js** | https://nodejs.org | 18+ |
| **Angular CLI** | (se instala con un comando) | 17+ |

### Instalar Angular CLI (solo una vez)
Abrí una terminal y ejecutá:
```bash
npm install -g @angular/cli
```

---

## ▶ Cómo correr la app

### Opción A: Script automático

- **Windows**: doble click en `start.bat`
- **Mac/Linux**: ejecutá `./start.sh` (puede que necesites `chmod +x start.sh` primero)

### Opción B: Manual en VS Code

1. Abrí la carpeta `supercompare` en VS Code
2. Abrí **dos terminales** (Ctrl+`)

**Terminal 1 — Backend:**
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

**Terminal 2 — Frontend:**
```bash
cd frontend-angular
npm install
ng serve
```

3. Abrí el navegador en **http://localhost:4200**

---

## 🔗 URLs

| Servicio | URL |
|----------|-----|
| App frontend | http://localhost:4200 |
| API backend | http://localhost:8000 |
| Docs API (Swagger) | http://localhost:8000/docs |

---

## ✨ Características

- 🔍 Búsqueda en tiempo real con debounce
- 💚 Precios de **DIA** en tiempo real
- 🔴 Precios de **COTO** en tiempo real
- 💰 Comparación automática de precios
- 🏆 Indica cuál supermercado es más barato
- 🏷 Muestra productos **en oferta** con % de descuento
- 📊 Diferencia de precio en pesos y porcentaje
- 🕐 Búsquedas recientes guardadas
- 📱 Diseño responsive (funciona en celular)
- ⚖ Ordenar por precio, nombre o descuento

---

## ⚠ Nota importante

Este scraper depende de la estructura HTML actual de los sitios web de DIA y COTO.
Si los supermercados cambian su sitio, puede ser necesario actualizar los selectores CSS en `backend/scraper.py`.

Para uso personal únicamente.

---

## 🛠 Stack técnico

- **Backend**: Python + FastAPI + BeautifulSoup + httpx
- **Frontend**: Angular 17 + TypeScript
- **Comunicación**: REST API (HTTP)
