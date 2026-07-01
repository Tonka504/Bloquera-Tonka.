import os
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
from io import BytesIO
from flask import Flask, render_template, jsonify, request, send_file
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
except ImportError:
    REPORTLAB_AVAILABLE = False
    print("[WARN] ReportLab no disponible")

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    print("[ERROR] DATABASE_URL no configurada!")

app = Flask(__name__, static_folder='static', template_folder='templates')
app.secret_key = 'bloquera-tonka-secret-key-2024'
CORS(app)

def get_db_connection():
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)

# ============================================================
# INICIALIZAR BASE DE DATOS (todas las tablas)
# ============================================================
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Usuarios
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id SERIAL PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            nombre TEXT NOT NULL,
            rol TEXT DEFAULT 'operario',
            activo INTEGER DEFAULT 1
        )
    """)

    # Pedidos
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pedidos (
            id SERIAL PRIMARY KEY,
            fecha TEXT NOT NULL,
            cliente TEXT NOT NULL,
            producto TEXT NOT NULL,
            cantidad INTEGER NOT NULL,
            precio_unitario REAL NOT NULL,
            estado TEXT DEFAULT 'Pendiente',
            anticipo REAL DEFAULT 0
        )
    """)

    # Historial Facturas
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS historial_facturas (
            num_factura SERIAL PRIMARY KEY,
            fecha_despacho TEXT,
            cliente TEXT,
            producto TEXT,
            cantidad INTEGER,
            total_venta REAL,
            estado TEXT DEFAULT 'Pagado',
            anticipo REAL DEFAULT 0.0,
            saldo_pendiente REAL DEFAULT 0.0,
            identidad TEXT DEFAULT '',
            rtn TEXT DEFAULT '',
            telefono TEXT DEFAULT '',
            tipo_factura TEXT DEFAULT 'Normal',
            isv REAL DEFAULT 0.0,
            direccion TEXT DEFAULT 'SANTA BARBARA, S.B., HONDURAS',
            tipo_impuesto TEXT DEFAULT 'Producto Gravado (15%)'
        )
    """)

    # Inventario
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS inventario (
            id SERIAL PRIMARY KEY,
            tipo TEXT UNIQUE NOT NULL,
            cantidad REAL DEFAULT 0
        )
    """)

    # Gastos
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS gastos (
            id SERIAL PRIMARY KEY,
            fecha TEXT NOT NULL,
            descripcion TEXT NOT NULL,
            categoria TEXT,
            monto REAL NOT NULL
        )
    """)

    # Configuración
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS configuracion (
            id SERIAL PRIMARY KEY,
            bloques_por_bolsa REAL DEFAULT 42,
            arena_por_100_bloques REAL DEFAULT 0.40
        )
    """)

    # Insertar datos iniciales si no existen
    cursor.execute("SELECT COUNT(*) FROM usuarios")
    if cursor.fetchone()['count'] == 0:
        cursor.execute("""
            INSERT INTO usuarios (username, password, nombre, rol) VALUES
            ('admin', 'admin123', 'Administrador', 'admin'),
            ('operario', 'operario123', 'Operario', 'operario')
        """)

    cursor.execute("SELECT COUNT(*) FROM inventario")
    if cursor.fetchone()['count'] == 0:
        cursor.execute("""
            INSERT INTO inventario (tipo, cantidad) VALUES
            ('cemento_bolsas', 0),
            ('arena_m3', 0),
            ('bloque_de_4"_estandar', 0),
            ('bloque_de_5"_estandar', 0),
            ('bloque_de_6"_estandar', 0)
        """)

    cursor.execute("SELECT COUNT(*) FROM configuracion")
    if cursor.fetchone()['count'] == 0:
        cursor.execute("INSERT INTO configuracion (bloques_por_bolsa, arena_por_100_bloques) VALUES (42, 0.40)")

    conn.commit()
    conn.close()
    print("[INFO] Base de datos inicializada correctamente")

# ============================================================
# RUTAS
# ============================================================

@app.route('/')
def index():
    return render_template('index.html')

# ---------- LOGIN ----------
@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, nombre, rol FROM usuarios 
        WHERE username = %s AND password = %s AND activo = 1
    """, (username, password))
    user = cursor.fetchone()
    conn.close()

    if user:
        return jsonify({"success": True, "user": dict(user)})
    return jsonify({"success": False, "message": "Credenciales incorrectas"}), 401

# ---------- DASHBOARD ----------
@app.route('/api/reportes/resumen')
def resumen():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COALESCE(SUM(total_venta), 0) as total FROM historial_facturas")
    ventas = cursor.fetchone()['total'] or 0

    cursor.execute("SELECT COALESCE(SUM(monto), 0) as total FROM gastos")
    gastos = cursor.fetchone()['total'] or 0

    cursor.execute("SELECT COALESCE(SUM(saldo_pendiente), 0) as total FROM historial_facturas")
    por_cobrar = cursor.fetchone()['total'] or 0

    cursor.execute("SELECT COALESCE(SUM(cantidad), 0) as total FROM historial_facturas")
    bloques = cursor.fetchone()['total'] or 0

    conn.close()

    return jsonify({
        "ventas_total": round(ventas, 2),
        "gastos_total": round(gastos, 2),
        "balance": round(ventas - gastos, 2),
        "por_cobrar": round(por_cobrar, 2),
        "bloques_vendidos": int(bloques)
    })

# ---------- PEDIDOS ----------
@app.route('/api/pedidos', methods=['GET'])
def get_pedidos():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM pedidos ORDER BY id DESC")
    pedidos = cursor.fetchall()
    conn.close()
    return jsonify([dict(p) for p in pedidos])

@app.route('/api/pedidos', methods=['POST'])
def crear_pedido():
    data = request.get_json()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO pedidos (fecha, cliente, producto, cantidad, precio_unitario, estado, anticipo)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (
        datetime.now().strftime("%Y-%m-%d"),
        data['cliente'],
        data['producto'],
        data['cantidad'],
        data['precio'],
        data.get('estado', 'Pendiente'),
        data.get('anticipo', 0)
    ))
    conn.commit()
    conn.close()
    return jsonify({"success": True, "message": "Pedido creado"})

@app.route('/api/pedidos/<int:id>', methods=['DELETE'])
def eliminar_pedido(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM pedidos WHERE id = %s", (id,))
    conn.commit()
    conn.close()
    return jsonify({"success": True})

@app.route('/api/pedidos/<int:id>/despachar', methods=['POST'])
def despachar_pedido(id):
    data = request.get_json()
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM pedidos WHERE id = %s", (id,))
    pedido = cursor.fetchone()
    if not pedido:
        conn.close()
        return jsonify({"exito": False, "mensaje": "Pedido no encontrado"}), 404

    total = pedido['cantidad'] * pedido['precio_unitario']
    anticipo = pedido.get('anticipo', 0)
    saldo = total - anticipo

    cursor.execute("""
        INSERT INTO historial_facturas 
        (fecha_despacho, cliente, producto, cantidad, total_venta, estado, anticipo, saldo_pendiente,
         identidad, rtn, telefono, direccion, tipo_impuesto)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING num_factura
    """, (
        datetime.now().strftime("%Y-%m-%d"),
        pedido['cliente'],
        pedido['producto'],
        pedido['cantidad'],
        total,
        'Pagado' if saldo <= 0 else 'Pendiente',
        anticipo,
        max(saldo, 0),
        data.get('identidad', ''),
        data.get('rtn', ''),
        data.get('telefono', ''),
        data.get('direccion', 'SANTA BARBARA, S.B., HONDURAS'),
        data.get('tipo_impuesto', 'Producto Gravado (15%)')
    ))

    num_factura = cursor.fetchone()['num_factura']
    cursor.execute("DELETE FROM pedidos WHERE id = %s", (id,))
    conn.commit()
    conn.close()

    return jsonify({"exito": True, "num_factura": num_factura})

# ---------- FACTURAS ----------
@app.route('/api/facturas', methods=['GET'])
def get_facturas():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM historial_facturas ORDER BY num_factura DESC")
    facturas = cursor.fetchall()
    conn.close()
    return jsonify([dict(f) for f in facturas])

@app.route('/api/facturas/<int:num>/liquidar', methods=['POST'])
def liquidar_factura(num):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE historial_facturas 
        SET saldo_pendiente = 0, estado = 'Pagado' 
        WHERE num_factura = %s
    """, (num,))
    conn.commit()
    conn.close()
    return jsonify({"success": True})

@app.route('/api/facturas/<int:num>/pdf')
def descargar_pdf(num):
    # Versión simplificada de PDF
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM historial_facturas WHERE num_factura = %s", (num,))
    factura = cursor.fetchone()
    conn.close()

    if not factura:
        return "Factura no encontrada", 404

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, 750, "BLOQUERA TONKA - FACTURA")
    c.setFont("Helvetica", 12)
    c.drawString(50, 720, f"Factura #: {factura['num_factura']}")
    c.drawString(50, 700, f"Fecha: {factura['fecha_despacho']}")
    c.drawString(50, 680, f"Cliente: {factura['cliente']}")
    c.drawString(50, 660, f"Producto: {factura['producto']}")
    c.drawString(50, 640, f"Cantidad: {factura['cantidad']}")
    c.drawString(50, 620, f"Total: L. {factura['total_venta']:.2f}")
    c.save()
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name=f"factura_{num}.pdf", mimetype='application/pdf')

# ---------- INVENTARIO ----------
@app.route('/api/inventario', methods=['GET'])
def get_inventario():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT tipo, cantidad FROM inventario")
    rows = cursor.fetchall()
    conn.close()
    return jsonify({r['tipo']: r['cantidad'] for r in rows})

@app.route('/api/inventario/abastecer', methods=['POST'])
def abastecer_inventario():
    data = request.get_json()
    conn = get_db_connection()
    cursor = conn.cursor()

    if data.get('cemento', 0) > 0:
        cursor.execute("""
            UPDATE inventario SET cantidad = cantidad + %s 
            WHERE tipo = 'cemento_bolsas'
        """, (data['cemento'],))

    if data.get('arena', 0) > 0:
        cursor.execute("""
            UPDATE inventario SET cantidad = cantidad + %s 
            WHERE tipo = 'arena_m3'
        """, (data['arena'],))

    conn.commit()
    conn.close()
    return jsonify({"success": True})

@app.route('/api/inventario/producir', methods=['POST'])
def producir_bloques():
    data = request.get_json()
    producto = data['producto']
    cantidad = data['cantidad']

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM configuracion LIMIT 1")
    config = cursor.fetchone()

    bloques_por_bolsa = config['bloques_por_bolsa']
    arena_por_100 = config['arena_por_100_bloques']

    cemento_necesario = round(cantidad / bloques_por_bolsa, 2)
    arena_necesaria = round((cantidad / 100) * arena_por_100, 2)

    cursor.execute("SELECT cantidad FROM inventario WHERE tipo = 'cemento_bolsas'")
    cemento_actual = cursor.fetchone()['cantidad']

    cursor.execute("SELECT cantidad FROM inventario WHERE tipo = 'arena_m3'")
    arena_actual = cursor.fetchone()['cantidad']

    if cemento_actual < cemento_necesario or arena_actual < arena_necesaria:
        conn.close()
        return jsonify({
            "success": False,
            "cemento_necesario": cemento_necesario,
            "arena_necesaria": arena_necesaria
        })

    # Descontar materiales
    cursor.execute("""
        UPDATE inventario SET cantidad = cantidad - %s 
        WHERE tipo = 'cemento_bolsas'
    """, (cemento_necesario,))

    cursor.execute("""
        UPDATE inventario SET cantidad = cantidad - %s 
        WHERE tipo = 'arena_m3'
    """, (arena_necesaria,))

    # Sumar bloques producidos
    cursor.execute("""
        UPDATE inventario SET cantidad = cantidad + %s 
        WHERE tipo = %s
    """, (cantidad, producto))

    conn.commit()
    conn.close()

    return jsonify({
        "success": True,
        "cemento_necesario": cemento_necesario,
        "arena_necesaria": arena_necesaria
    })

# ---------- GASTOS ----------
@app.route('/api/gastos', methods=['GET'])
def get_gastos():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM gastos ORDER BY id DESC")
    gastos = cursor.fetchall()
    conn.close()
    return jsonify([dict(g) for g in gastos])

@app.route('/api/gastos', methods=['POST'])
def crear_gasto():
    data = request.get_json()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO gastos (fecha, descripcion, categoria, monto)
        VALUES (%s, %s, %s, %s)
    """, (
        datetime.now().strftime("%Y-%m-%d"),
        data['descripcion'],
        data['categoria'],
        data['monto']
    ))
    conn.commit()
    conn.close()
    return jsonify({"success": True})

@app.route('/api/gastos/<int:id>', methods=['DELETE'])
def eliminar_gasto(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM gastos WHERE id = %s", (id,))
    conn.commit()
    conn.close()
    return jsonify({"success": True})

# ---------- DEUDORES ----------
@app.route('/api/deudores', methods=['GET'])
def get_deudores():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT cliente, SUM(saldo_pendiente) as deuda 
        FROM historial_facturas 
        WHERE saldo_pendiente > 0 
        GROUP BY cliente
    """)
    deudores = cursor.fetchall()
    conn.close()
    return jsonify([dict(d) for d in deudores])

# ---------- CONFIG ----------
@app.route('/api/config', methods=['GET'])
def get_config():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM configuracion LIMIT 1")
    config = cursor.fetchone()
    conn.close()
    return jsonify(dict(config) if config else {})

@app.route('/api/config', methods=['POST'])
def guardar_config():
    data = request.get_json()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE configuracion 
        SET bloques_por_bolsa = %s, arena_por_100_bloques = %s
        WHERE id = 1
    """, (data['bloques_por_bolsa'], data['arena_por_100_bloques']))
    conn.commit()
    conn.close()
    return jsonify({"success": True})

# ============================================================
# INICIO
# ============================================================
if __name__ == '__main__':
    init_db()
    print("🚀 Bloquera Tonka iniciada")
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))