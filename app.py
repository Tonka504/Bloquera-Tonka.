import os
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
from io import BytesIO
from flask import Flask, render_template, jsonify, request, send_file, send_from_directory
from flask_cors import CORS

# ReportLab para PDFs
try:
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    REPORTLAB_AVAILABLE = True
    print("[INFO] ReportLab OK")
except ImportError:
    REPORTLAB_AVAILABLE = False
    print("[WARN] ReportLab no disponible")

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    print("[ERROR] DATABASE_URL no configurada!")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FACTURAS_DIR = os.path.join(BASE_DIR, "facturas")
os.makedirs(FACTURAS_DIR, exist_ok=True)

app = Flask(__name__, static_folder='static', template_folder='templates')
app.secret_key = 'bloquera-tonka-secret-key-2024'
CORS(app)

def get_db_connection():
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)

# ============================================================
# INIT DB
# ============================================================
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    # Tus tablas (resumido)
    cursor.execute("""CREATE TABLE IF NOT EXISTS historial_facturas (
        num_factura SERIAL PRIMARY KEY, fecha_despacho TEXT, cliente TEXT, producto TEXT,
        cantidad INTEGER, total_venta REAL, estado TEXT DEFAULT 'Pagado',
        anticipo REAL DEFAULT 0.0, saldo_pendiente REAL DEFAULT 0.0,
        identidad TEXT DEFAULT '', rtn TEXT DEFAULT '', telefono TEXT DEFAULT '',
        tipo_factura TEXT DEFAULT 'Normal', isv REAL DEFAULT 0.0,
        direccion TEXT DEFAULT 'SANTA BARBARA, S.B., HONDURAS',
        tipo_impuesto TEXT DEFAULT 'Producto Gravado (15%)'
    )""")
    # Agrega las otras CREATE TABLE aquí (inventario, configuracion, pedidos, gastos, usuarios)
    # ... (copia el resto de tu init_db original)
    conn.commit()
    conn.close()

# ============================================================
# RUTAS BÁSICAS
# ============================================================
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, nombre, rol FROM usuarios WHERE username = %s AND password = %s AND activo = 1", (username, password))
    user = cursor.fetchone()
    conn.close()
    if user:
        return jsonify({"success": True, "user": dict(user)})
    return jsonify({"success": False, "message": "Credenciales incorrectas"}), 401

# Agrega aquí el resto de tus rutas (@app.route('/api/pedidos'), etc.)

if __name__ == '__main__':
    init_db()
    print("🚀 Bloquera Tonka en Render")
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))