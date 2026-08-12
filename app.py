# =====================================================================
# app.py
# ---------------------------------------------------------------------
# Acá viven SOLO las rutas: reciben pedidos del navegador, llaman a las
# funciones de funciones.py (que hacen el trabajo real con la base de
# datos) y devuelven una página HTML ya armada con render_template.
#
# Para correr la aplicación:
#     1) python crear_db.py      (una sola vez, crea database.db)
#     2) python app.py           (levanta el servidor)
#     3) abrir http://127.0.0.1:5000 en el navegador
# =====================================================================

from functools import wraps

from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash

import funciones

app = Flask(__name__)

# La secret_key es necesaria para que Flask pueda usar sesiones (para
# saber quién inició sesión en cada navegador). En un proyecto real
# esto no se deja escrito en el código, pero para el trabajo académico
# alcanza con dejarlo así.
app.secret_key = 'agrocompartir-clave-secreta-lavalle'


# =====================================================================
# DECORADOR: exige que haya una sesión iniciada
# ---------------------------------------------------------------------
# Se usa poniendo @login_requerido arriba de cualquier ruta que solo
# deba verse si el usuario ya inició sesión. Si no hay sesión, manda
# directo a la pantalla de login.
# =====================================================================

def login_requerido(vista):
    @wraps(vista)
    def envoltura(*args, **kwargs):
        if not session.get('usuario_id'):
            return redirect(url_for('login'))
        return vista(*args, **kwargs)
    return envoltura


# =====================================================================
# DECORADOR: exige que el usuario tenga un rol determinado
# ---------------------------------------------------------------------
# Se usa arriba de @login_requerido en las rutas que solo pueden ver
# los fleteros (por ejemplo, cargar el espacio disponible del camión).
# Si un cliente intenta entrar igual, se lo manda de vuelta al
# dashboard sin romper nada.
# =====================================================================

def rol_requerido(rol):
    def decorador(vista):
        @wraps(vista)
        def envoltura(*args, **kwargs):
            if session.get('tipo_usuario') != rol:
                return redirect(url_for('dashboard'))
            return vista(*args, **kwargs)
        return envoltura
    return decorador


# =====================================================================
# RUTA RAÍZ
# =====================================================================

@app.route('/')
def index():
    if session.get('usuario_id'):
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


# =====================================================================
# LOGIN / REGISTRO / LOGOUT
# =====================================================================

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')

        usuario = funciones.buscar_usuario_por_email(email)
        # usuario es (id, nombre, email, password_hash, tipo) o None

        if usuario and check_password_hash(usuario[3], password):
            session['usuario_id'] = usuario[0]
            session['usuario_nombre'] = usuario[1]
            session['tipo_usuario'] = usuario[4]
            return redirect(url_for('dashboard'))

        return render_template('login.html', error='Email o contraseña incorrectos.')

    return render_template('login.html')


@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        nombre = request.form.get('nombre', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        tipo = request.form.get('tipo', '')

        if not nombre or not email or not password or tipo not in ('cliente', 'fletero'):
            return render_template('registro.html', error='Completá todos los campos.')

        if funciones.buscar_usuario_por_email(email):
            return render_template('registro.html', error='Ya existe una cuenta con ese email.')

        funciones.crear_usuario(nombre, email, generate_password_hash(password), tipo)
        return redirect(url_for('login'))

    return render_template('registro.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


# =====================================================================
# DASHBOARD (pantalla principal, con accesos a las 4 funcionalidades)
# =====================================================================

@app.route('/dashboard')
@login_requerido
def dashboard():
    return render_template('dashboard.html', resumen=funciones.resumen_disponibilidad())


# =====================================================================
# PRODUCTORES (carga de datos de cosecha, compartida entre todos)
# =====================================================================

@app.route('/productores', methods=['GET', 'POST'])
@login_requerido
def productores():
    if request.method == 'POST':
        funciones.registrar_productor(
            session['usuario_id'],
            request.form.get('nombre_productor', '').strip(),
            request.form.get('localidad'),
            request.form.get('producto'),
            int(request.form.get('cantidad_cajones', 0)),
            float(request.form.get('peso_por_cajon', 0)),
            float(request.form.get('costo_viaje', 0)),
        )
        return redirect(url_for('productores'))

    return render_template(
        'productores.html',
        productores=funciones.obtener_productores(),
        localidades=funciones.LOCALIDADES_PRODUCTORES,
        productos=funciones.PRODUCTOS,
    )


# =====================================================================
# FUNCIONALIDAD 1: PUZZLE DE CARGA (capacidad del camión)
# =====================================================================

@app.route('/camion')
@login_requerido
def camion():
    return render_template('camion.html', datos=funciones.calcular_camion())


# =====================================================================
# FUNCIONALIDAD 2: RUTA INTELIGENTE
# =====================================================================

@app.route('/ruta')
@login_requerido
def ruta():
    return render_template('ruta.html', datos=funciones.calcular_ruta())


# =====================================================================
# FUNCIONALIDAD 3: LUGAR LIBRE
# =====================================================================

@app.route('/lugar_libre', methods=['GET', 'POST'])
@login_requerido
def lugar_libre():
    if request.method == 'POST':
        lugar_libre_cant = int(request.form.get('lugar_libre') or 0)
        necesita_cant = int(request.form.get('necesita') or 0)
        funciones.registrar_espacio(session['usuario_id'], lugar_libre_cant, necesita_cant)
        return redirect(url_for('lugar_libre'))

    return render_template('lugar_libre.html', coincidencias=funciones.buscar_coincidencias())


# =====================================================================
# FUNCIONALIDAD 4: AHORRO
# =====================================================================

@app.route('/ahorro')
@login_requerido
def ahorro():
    return render_template('ahorro.html', datos=funciones.calcular_ahorro())


# =====================================================================
# FUNCIONALIDAD 5: MI ESPACIO DISPONIBLE (solo fleteros)
# ---------------------------------------------------------------------
# Acá el fletero carga su vehículo (o varios) indicando cuánto peso y
# cuántos cajones puede llevar. Eso es justamente "el espacio
# disponible" que después ven los demás usuarios en /disponibilidad.
# =====================================================================

@app.route('/vehiculo', methods=['GET', 'POST'])
@login_requerido
@rol_requerido('fletero')
def vehiculo():
    if request.method == 'POST':
        funciones.registrar_vehiculo(
            session['usuario_id'],
            request.form.get('patente', '').strip().upper(),
            request.form.get('marca_modelo', '').strip(),
            float(request.form.get('peso_maximo', 0)),
            int(request.form.get('cajones_maximo', 0)),
        )
        return redirect(url_for('vehiculo'))

    return render_template(
        'vehiculo.html',
        vehiculos=funciones.obtener_vehiculos_de_usuario(session['usuario_id']),
    )


# =====================================================================
# FUNCIONALIDAD 6: ESPACIO DISPONIBLE (lo ve cualquier usuario)
# ---------------------------------------------------------------------
# Lista de todos los vehículos cargados por los fleteros: es el aviso
# para que un cliente sepa quién tiene lugar en su camión ahora mismo.
# =====================================================================

@app.route('/disponibilidad')
@login_requerido
def disponibilidad():
    return render_template('disponibilidad.html', vehiculos=funciones.obtener_vehiculos())


# =====================================================================
# PUNTO DE ENTRADA
# =====================================================================

if __name__ == '__main__':
    app.run(debug=True)
