# =====================================================================
# funciones.py
# ---------------------------------------------------------------------
# Acá vive TODA la lógica de la aplicación: acceso a la base de datos,
# cálculos y algoritmos. app.py solo se encarga de las rutas (recibir
# pedidos web y devolver una página), y llama a estas funciones.
#
# Separar el código así tiene una ventaja para el estudiante: si algún
# día hay que revisar "cómo se calcula el ahorro" o "cómo se arma la
# ruta", se sabe que hay que mirar acá, y no revolver todo app.py.
# =====================================================================

import sqlite3

# =====================================================================
# CONSTANTES DEL SISTEMA
# ---------------------------------------------------------------------
# Se dejan como variables "sueltas" arriba del archivo para que sea muy
# fácil encontrarlas y modificarlas (por ejemplo, para la exposición).
# =====================================================================

# --- Datos del camión (Funcionalidad 1: Puzzle de carga) ---
PESO_MAXIMO_CAMION = 10000       # kilogramos
CAJONES_MAXIMO_CAMION = 500      # cajones

# --- Productos permitidos ---
PRODUCTOS = ['Tomate', 'Melón', 'Uva']

# --- Localidades donde puede estar un productor ---
LOCALIDADES_PRODUCTORES = [
    'Costa de Araujo',
    'Jocolí',
    'Tres de Mayo',
    'San Francisco',
    'Gustavo André',
]

# El mercado es el destino final del camión, no la localidad de ningún
# productor, por eso se maneja aparte.
MERCADO = 'Mercado Central'

# Todas las localidades (para la matriz de distancias) = productores + mercado
LOCALIDADES = LOCALIDADES_PRODUCTORES + [MERCADO]

# --- Matriz de distancias fija (Funcionalidad 2: Ruta inteligente) ---
# Se guarda una sola vez cada par (A, B); para buscar la distancia entre
# dos localidades sin importar el orden se usa la función obtener_distancia().
# Los valores son ficticios pero razonables para un trabajo académico:
# no se usan mapas ni APIs externas, como pide la consigna.
DISTANCIAS = {
    ('Costa de Araujo', 'Jocolí'): 12,
    ('Costa de Araujo', 'Tres de Mayo'): 20,
    ('Costa de Araujo', 'San Francisco'): 25,
    ('Costa de Araujo', 'Gustavo André'): 30,
    ('Costa de Araujo', 'Mercado Central'): 35,
    ('Jocolí', 'Tres de Mayo'): 9,
    ('Jocolí', 'San Francisco'): 15,
    ('Jocolí', 'Gustavo André'): 22,
    ('Jocolí', 'Mercado Central'): 28,
    ('Tres de Mayo', 'San Francisco'): 10,
    ('Tres de Mayo', 'Gustavo André'): 14,
    ('Tres de Mayo', 'Mercado Central'): 20,
    ('San Francisco', 'Gustavo André'): 8,
    ('San Francisco', 'Mercado Central'): 15,
    ('Gustavo André', 'Mercado Central'): 10,
}

# --- Costo de referencia del camión compartido (Funcionalidad 4: Ahorro) ---
# En una cooperativa real este número podría salir de una cotización de
# transporte. Para mantener el proyecto simple (sin formularios extra
# ni tablas nuevas) se deja como una constante fácil de ajustar acá.
COSTO_CAMION_COMPARTIDO = 180000


# =====================================================================
# CONEXIÓN A LA BASE DE DATOS
# =====================================================================

def obtener_conexion():
    """
    Abre una conexión nueva a la base de datos SQLite.

    Recibe: nada.
    Devuelve: un objeto de conexión de sqlite3, ya listo para usar.
    """
    conexion = sqlite3.connect('database.db')
    return conexion


# =====================================================================
# USUARIOS (login / registro)
# =====================================================================

def buscar_usuario_por_email(email):
    """
    Busca un usuario según su email, para el login o para validar que
    no esté repetido en el registro.

    Recibe: email (texto).
    Devuelve: una tupla (id, nombre, email, password, tipo) si lo
    encuentra, o None si no existe ningún usuario con ese email. El
    tipo es 'cliente' o 'fletero'.
    """
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute(
        'SELECT id, nombre, email, password, tipo FROM usuarios WHERE email = ?',
        (email,)
    )
    usuario = cursor.fetchone()
    conexion.close()
    return usuario


def crear_usuario(nombre, email, password_hash, tipo='cliente'):
    """
    Guarda un usuario nuevo en la base de datos.

    Recibe: nombre (texto), email (texto), password_hash (texto: la
    contraseña ya encriptada, nunca la contraseña original), tipo
    (texto: 'cliente' o 'fletero', según se haya elegido en el
    registro).
    Devuelve: nada.
    """
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute(
        'INSERT INTO usuarios (nombre, email, password, tipo) VALUES (?, ?, ?, ?)',
        (nombre, email, password_hash, tipo)
    )
    conexion.commit()
    conexion.close()


# =====================================================================
# FUNCIONALIDAD: PRODUCTORES (carga de datos de cada cosecha)
# =====================================================================

def registrar_productor(usuario_id, nombre_productor, localidad, producto,
                         cantidad_cajones, peso_por_cajon, costo_viaje):
    """
    Guarda un nuevo registro de producción (lo que un usuario quiere
    llevar en el camión compartido).

    Recibe: usuario_id (id numérico del usuario dueño del dato),
    nombre_productor (texto), localidad (texto), producto (texto),
    cantidad_cajones (número entero), peso_por_cajon (número, en kg),
    costo_viaje (número, en pesos).
    Devuelve: nada.
    """
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute('''
        INSERT INTO productores
            (usuario_id, nombre_productor, localidad, producto,
             cantidad_cajones, peso_por_cajon, costo_viaje)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (usuario_id, nombre_productor, localidad, producto,
          cantidad_cajones, peso_por_cajon, costo_viaje))
    conexion.commit()
    conexion.close()


def obtener_productores():
    """
    Trae la lista completa de productores cargados por TODOS los
    usuarios (la cooperativa comparte los datos entre todos).

    Recibe: nada.
    Devuelve: una lista de tuplas, cada una con
    (id, nombre_usuario, nombre_productor, localidad, producto,
     cantidad_cajones, peso_por_cajon, costo_viaje).
    """
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute('''
        SELECT p.id, u.nombre, p.nombre_productor, p.localidad, p.producto,
               p.cantidad_cajones, p.peso_por_cajon, p.costo_viaje
        FROM productores p
        JOIN usuarios u ON u.id = p.usuario_id
        ORDER BY p.id
    ''')
    filas = cursor.fetchall()
    conexion.close()
    return filas


# =====================================================================
# FUNCIONALIDAD 1: PUZZLE DE CARGA
# =====================================================================

def calcular_camion(vehiculo_id=None):
    """
    Suma los cajones y el peso de TODOS los productores cargados hasta
    ahora, y los compara contra la capacidad máxima del camión.

    Si se pasa un vehiculo_id, la comparación se hace contra el peso y
    los cajones máximos de ESE vehículo en particular (cargado por un
    fletero en la Funcionalidad 5). Si no se pasa ninguno, o el
    vehículo no existe, se usan las constantes fijas del sistema como
    antes (para no romper nada si todavía no hay vehículos cargados).

    No hace falta ningún algoritmo complicado: solo sumar y comparar,
    tal como pide la consigna.

    Recibe: vehiculo_id (número entero, opcional).
    Devuelve: un diccionario con el peso total, los cajones totales,
    los porcentajes ocupados y si se superó algún límite.
    """
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute('SELECT cantidad_cajones, peso_por_cajon FROM productores')
    filas = cursor.fetchall()

    peso_maximo = PESO_MAXIMO_CAMION
    cajones_maximo = CAJONES_MAXIMO_CAMION

    if vehiculo_id:
        cursor.execute(
            'SELECT peso_maximo, cajones_maximo FROM vehiculos WHERE id = ?',
            (vehiculo_id,)
        )
        vehiculo = cursor.fetchone()
        if vehiculo:
            peso_maximo, cajones_maximo = vehiculo

    conexion.close()

    cajones_totales = 0
    peso_total = 0
    for cantidad_cajones, peso_por_cajon in filas:
        cajones_totales += cantidad_cajones
        peso_total += cantidad_cajones * peso_por_cajon

    porcentaje_cajones = (cajones_totales / cajones_maximo) * 100
    porcentaje_peso = (peso_total / peso_maximo) * 100

    return {
        'cajones_totales': cajones_totales,
        'peso_total': peso_total,
        'cajones_maximo': cajones_maximo,
        'peso_maximo': peso_maximo,
        'porcentaje_cajones': round(porcentaje_cajones, 1),
        'porcentaje_peso': round(porcentaje_peso, 1),
        'supera_cajones': cajones_totales > cajones_maximo,
        'supera_peso': peso_total > peso_maximo,
        'camion_lleno': porcentaje_cajones >= 100 or porcentaje_peso >= 100,
    }


# =====================================================================
# FUNCIONALIDAD 2: RUTA INTELIGENTE (vecino más cercano)
# =====================================================================

def obtener_distancia(origen, destino):
    """
    Busca en la matriz fija la distancia entre dos localidades, sin
    importar en qué orden se guardó el par en el diccionario DISTANCIAS.

    Recibe: origen (texto), destino (texto).
    Devuelve: la distancia en kilómetros (número).
    """
    if origen == destino:
        return 0
    if (origen, destino) in DISTANCIAS:
        return DISTANCIAS[(origen, destino)]
    return DISTANCIAS[(destino, origen)]


def calcular_ruta_personalizada(localidades_incluidas, origen=None):
    """
    Arma una ruta simple usando el algoritmo del "vecino más cercano":
    parte de un origen (por defecto, la primera localidad de la lista),
    en cada paso va a la localidad no visitada más cercana, y termina
    siempre en el Mercado Central (destino final de toda la
    producción).

    Es la versión general del algoritmo: se le puede pasar CUALQUIER
    lista de localidades (por ejemplo, solo las de los chacareros que
    un fletero eligió coordinar en la Funcionalidad 6), no solamente
    todas las localidades del sistema.

    Recibe: localidades_incluidas (lista de nombres de localidad, sin
    el Mercado Central), origen (texto, opcional: si no se indica, se
    usa la primera localidad de la lista).
    Devuelve: un diccionario con el orden de visita (lista de
    localidades, terminando en el Mercado Central) y la distancia
    total recorrida en km.
    """
    # Por las dudas, nos aseguramos de no repetir localidades ni de
    # incluir el mercado entre los "puntos a visitar" (el mercado
    # siempre se agrega al final, aparte).
    localidades_incluidas = list(dict.fromkeys(
        loc for loc in localidades_incluidas if loc != MERCADO
    ))

    if not localidades_incluidas:
        return {'ruta': [MERCADO], 'distancia_total': 0}

    if origen is None or origen not in localidades_incluidas:
        origen = localidades_incluidas[0]

    # Localidades que hay que visitar antes de llegar al mercado
    pendientes = [loc for loc in localidades_incluidas if loc != origen]

    ruta = [origen]
    actual = origen
    distancia_total = 0

    # Vecino más cercano: en cada paso, buscamos entre las localidades
    # que faltan visitar cuál es la más cercana a donde estamos parados.
    while pendientes:
        localidad_mas_cercana = None
        menor_distancia = None
        for localidad in pendientes:
            distancia = obtener_distancia(actual, localidad)
            if menor_distancia is None or distancia < menor_distancia:
                menor_distancia = distancia
                localidad_mas_cercana = localidad

        ruta.append(localidad_mas_cercana)
        distancia_total += menor_distancia
        actual = localidad_mas_cercana
        pendientes.remove(localidad_mas_cercana)

    # Por último, del último punto visitado se va siempre al mercado
    distancia_total += obtener_distancia(actual, MERCADO)
    ruta.append(MERCADO)

    return {
        'ruta': ruta,
        'distancia_total': distancia_total,
    }


def calcular_ruta():
    """
    Arma la ruta general del sistema: todas las localidades de
    productores, partiendo siempre de Costa de Araujo. Es la ruta que
    se muestra en la Funcionalidad 2 (Ruta inteligente).

    Recibe: nada.
    Devuelve: lo mismo que calcular_ruta_personalizada().
    """
    return calcular_ruta_personalizada(LOCALIDADES_PRODUCTORES, origen='Costa de Araujo')


# =====================================================================
# FUNCIONALIDAD 3: LUGAR LIBRE
# =====================================================================

def registrar_espacio(usuario_id, lugar_libre, necesita):
    """
    Guarda una publicación de "tengo libres X cajones" o
    "necesito X cajones".

    Recibe: usuario_id (id del usuario que publica), lugar_libre
    (cajones libres que ofrece, 0 si no aplica), necesita (cajones que
    necesita, 0 si no aplica).
    Devuelve: nada.
    """
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute(
        'INSERT INTO espacios (usuario_id, lugar_libre, necesita) VALUES (?, ?, ?)',
        (usuario_id, lugar_libre, necesita)
    )
    conexion.commit()
    conexion.close()


def buscar_coincidencias():
    """
    Busca automáticamente en la base de datos coincidencias entre un
    productor que tiene espacio libre y otro que necesita exactamente
    esa cantidad (y no son el mismo usuario).

    Recibe: nada.
    Devuelve: una lista de diccionarios, cada uno con los datos de la
    coincidencia encontrada (quién ofrece, quién necesita, cantidad y
    distancia aproximada entre sus localidades).
    """
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute('''
        SELECT DISTINCT
            u_ofrece.nombre, p_ofrece.localidad, p_ofrece.producto,
            e_ofrece.lugar_libre,
            u_necesita.nombre, p_necesita.localidad
        FROM espacios e_ofrece
        JOIN espacios e_necesita ON e_ofrece.lugar_libre = e_necesita.necesita
        JOIN usuarios u_ofrece ON u_ofrece.id = e_ofrece.usuario_id
        JOIN usuarios u_necesita ON u_necesita.id = e_necesita.usuario_id
        LEFT JOIN productores p_ofrece ON p_ofrece.usuario_id = e_ofrece.usuario_id
        LEFT JOIN productores p_necesita ON p_necesita.usuario_id = e_necesita.usuario_id
        WHERE e_ofrece.usuario_id != e_necesita.usuario_id
          AND e_ofrece.lugar_libre > 0
          AND e_necesita.necesita > 0
    ''')
    filas = cursor.fetchall()
    conexion.close()

    coincidencias = []
    for fila in filas:
        nombre_ofrece, localidad_ofrece, producto_ofrece, cantidad, nombre_necesita, localidad_necesita = fila

        # Si ambas localidades están registradas y son parte del mapa,
        # calculamos la distancia; si no, mostramos "No disponible".
        distancia = 'No disponible'
        if localidad_ofrece in LOCALIDADES and localidad_necesita in LOCALIDADES:
            distancia = obtener_distancia(localidad_ofrece, localidad_necesita)

        coincidencias.append({
            'nombre_ofrece': nombre_ofrece,
            'localidad_ofrece': localidad_ofrece or 'Sin registrar',
            'producto_ofrece': producto_ofrece or '—',
            'cantidad': cantidad,
            'nombre_necesita': nombre_necesita,
            'localidad_necesita': localidad_necesita or 'Sin registrar',
            'distancia': distancia,
        })

    return coincidencias


# =====================================================================
# FUNCIONALIDAD 4: CÁLCULO DEL AHORRO
# =====================================================================

def calcular_ahorro():
    """
    Calcula cuánto ahorra cada productor compartiendo el camión, en vez
    de pagar un flete individual.

    El costo compartido se reparte en partes iguales entre todos los
    productores (una mejora posible sería repartirlo según la cantidad
    de cajones de cada uno, pero se deja simple a propósito).

    Recibe: nada.
    Devuelve: un diccionario con el detalle por productor y los
    totales generales (costo individual total, costo compartido y
    ahorro total).
    """
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute('SELECT nombre_productor, costo_viaje FROM productores')
    filas = cursor.fetchall()
    conexion.close()

    cantidad_productores = len(filas)

    if cantidad_productores == 0:
        return {
            'detalle': [],
            'costo_individual_total': 0,
            'costo_compartido': COSTO_CAMION_COMPARTIDO,
            'ahorro_total': 0,
        }

    costo_individual_total = sum(costo for _, costo in filas)
    parte_por_productor = COSTO_CAMION_COMPARTIDO / cantidad_productores

    detalle = []
    for nombre, costo in filas:
        ahorro = costo - parte_por_productor
        detalle.append({
            'nombre': nombre,
            'costo_individual': costo,
            'parte_compartida': round(parte_por_productor, 2),
            'ahorro': round(ahorro, 2),
        })

    ahorro_total = costo_individual_total - COSTO_CAMION_COMPARTIDO

    return {
        'detalle': detalle,
        'costo_individual_total': costo_individual_total,
        'costo_compartido': COSTO_CAMION_COMPARTIDO,
        'ahorro_total': ahorro_total,
    }


# =====================================================================
# FUNCIONALIDAD 5: VEHÍCULOS (los fleteros cargan su camión)
# ---------------------------------------------------------------------
# Cualquier usuario puede cargar acá los datos de su camión: patente,
# marca/modelo y, lo más importante, cuánto peso y cuántos cajones
# soporta llevar. Esos vehículos después se usan en la Funcionalidad 1
# (Puzzle de carga, para comparar contra un camión real en vez de
# valores fijos) y en la Funcionalidad 6 (Coordinar ruta).
# =====================================================================

def registrar_vehiculo(usuario_id, patente, marca_modelo, peso_maximo, cajones_maximo):
    """
    Guarda un vehículo nuevo cargado por un fletero.

    Recibe: usuario_id (id del usuario dueño/conductor del vehículo),
    patente (texto), marca_modelo (texto), peso_maximo (número, en kg
    que soporta cargar), cajones_maximo (número entero de cajones que
    entran).
    Devuelve: nada.
    """
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute('''
        INSERT INTO vehiculos (usuario_id, patente, marca_modelo, peso_maximo, cajones_maximo)
        VALUES (?, ?, ?, ?, ?)
    ''', (usuario_id, patente, marca_modelo, peso_maximo, cajones_maximo))
    conexion.commit()
    conexion.close()


def obtener_vehiculos():
    """
    Trae la lista completa de vehículos cargados por TODOS los
    usuarios (para que cualquiera vea qué fleteros hay disponibles).

    Recibe: nada.
    Devuelve: una lista de tuplas, cada una con
    (id, nombre_fletero, patente, marca_modelo, peso_maximo, cajones_maximo).
    """
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute('''
        SELECT v.id, u.nombre, v.patente, v.marca_modelo, v.peso_maximo, v.cajones_maximo
        FROM vehiculos v
        JOIN usuarios u ON u.id = v.usuario_id
        ORDER BY v.id
    ''')
    filas = cursor.fetchall()
    conexion.close()
    return filas


def obtener_vehiculos_de_usuario(usuario_id):
    """
    Trae solo los vehículos cargados por un fletero en particular (para
    que, al entrar a "Mi espacio disponible", cada uno vea únicamente
    lo suyo).

    Recibe: usuario_id (id del fletero).
    Devuelve: una lista de tuplas (id, patente, marca_modelo,
    peso_maximo, cajones_maximo).
    """
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute('''
        SELECT id, patente, marca_modelo, peso_maximo, cajones_maximo
        FROM vehiculos
        WHERE usuario_id = ?
        ORDER BY id
    ''', (usuario_id,))
    filas = cursor.fetchall()
    conexion.close()
    return filas


def resumen_disponibilidad():
    """
    Calcula un resumen del espacio disponible que publicaron los
    fleteros hasta ahora: cuántos vehículos hay cargados y cuántos
    cajones libres suman entre todos. Se usa para el aviso que ven los
    demás usuarios en el Dashboard (se recalcula cada vez que alguien
    entra, así siempre está al día).

    Recibe: nada.
    Devuelve: un diccionario con 'cantidad_vehiculos' y
    'cajones_disponibles' (la suma de cajones_maximo de todos los
    vehículos cargados).
    """
    vehiculos = obtener_vehiculos()
    return {
        'cantidad_vehiculos': len(vehiculos),
        'cajones_disponibles': sum(v[4] for v in vehiculos),
    }


# =====================================================================
# FUNCIONALIDAD 6: COORDINAR RUTA (fletero + chacareros)
# ---------------------------------------------------------------------
# Un fletero elige con qué vehículo va a salir y qué chacareros
# (productores ya cargados en la Funcionalidad "Productores") va a
# levantar en ese viaje. El sistema arma automáticamente la mejor ruta
# entre esas localidades (reutilizando el mismo algoritmo del vecino
# más cercano de la Funcionalidad 2) y cada chacarero puede confirmar
# después que su carga va a estar lista.
# =====================================================================

def crear_coordinacion(usuario_id, vehiculo_id, productor_ids):
    """
    Crea un nuevo viaje coordinado: calcula la mejor ruta entre las
    localidades de los productores elegidos y guarda tanto la
    coordinación como el detalle de cada chacarero incluido.

    Recibe: usuario_id (id del fletero que arma la coordinación),
    vehiculo_id (id del vehículo elegido), productor_ids (lista de ids
    de productores/chacareros a incluir en el viaje).
    Devuelve: nada.
    """
    conexion = obtener_conexion()
    cursor = conexion.cursor()

    # Localidades de los productores elegidos, sin repetir (puede haber
    # más de un chacarero en la misma localidad).
    placeholders = ','.join('?' * len(productor_ids))
    cursor.execute(
        f'SELECT DISTINCT localidad FROM productores WHERE id IN ({placeholders})',
        productor_ids
    )
    localidades_incluidas = [fila[0] for fila in cursor.fetchall()]

    resultado_ruta = calcular_ruta_personalizada(localidades_incluidas)

    cursor.execute('''
        INSERT INTO coordinaciones (usuario_id, vehiculo_id, ruta, distancia_total)
        VALUES (?, ?, ?, ?)
    ''', (
        usuario_id,
        vehiculo_id,
        ','.join(resultado_ruta['ruta']),
        resultado_ruta['distancia_total'],
    ))
    coordinacion_id = cursor.lastrowid

    for productor_id in productor_ids:
        cursor.execute('''
            INSERT INTO coordinacion_detalle (coordinacion_id, productor_id, confirmado)
            VALUES (?, ?, 0)
        ''', (coordinacion_id, productor_id))

    conexion.commit()
    conexion.close()


def obtener_coordinaciones():
    """
    Trae todos los viajes coordinados, con la ruta ya armada y el
    detalle de qué chacareros están incluidos (y si ya confirmaron su
    carga o siguen pendientes).

    Recibe: nada.
    Devuelve: una lista de diccionarios, cada uno con los datos del
    viaje (vehículo, fletero, ruta, distancia total) y su detalle de
    chacareros.
    """
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute('''
        SELECT c.id, c.ruta, c.distancia_total,
               u.nombre, v.patente, v.marca_modelo
        FROM coordinaciones c
        JOIN usuarios u ON u.id = c.usuario_id
        JOIN vehiculos v ON v.id = c.vehiculo_id
        ORDER BY c.id DESC
    ''')
    filas_coordinaciones = cursor.fetchall()

    coordinaciones = []
    for c_id, ruta_texto, distancia_total, fletero, patente, marca_modelo in filas_coordinaciones:
        cursor.execute('''
            SELECT cd.id, cd.confirmado, p.usuario_id, p.nombre_productor,
                   p.localidad, p.producto, p.cantidad_cajones
            FROM coordinacion_detalle cd
            JOIN productores p ON p.id = cd.productor_id
            WHERE cd.coordinacion_id = ?
        ''', (c_id,))

        detalle = []
        for det_id, confirmado, usuario_id_chacarero, nombre_productor, localidad, producto, cajones in cursor.fetchall():
            detalle.append({
                'detalle_id': det_id,
                'confirmado': bool(confirmado),
                'usuario_id': usuario_id_chacarero,
                'nombre_productor': nombre_productor,
                'localidad': localidad,
                'producto': producto,
                'cajones': cajones,
            })

        coordinaciones.append({
            'id': c_id,
            'ruta': ruta_texto.split(','),
            'distancia_total': distancia_total,
            'fletero': fletero,
            'patente': patente,
            'marca_modelo': marca_modelo,
            'detalle': detalle,
        })

    conexion.close()
    return coordinaciones


def confirmar_participacion(detalle_id, usuario_id):
    """
    Marca como confirmada la carga de un chacarero dentro de un viaje
    coordinado. Solo puede confirmar el usuario dueño de esa
    producción (por eso el UPDATE chequea que el productor pertenezca
    a usuario_id): así un usuario no puede confirmar la carga de otro.

    Recibe: detalle_id (id de la fila en coordinacion_detalle),
    usuario_id (id del usuario que está confirmando).
    Devuelve: nada.
    """
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute('''
        UPDATE coordinacion_detalle
        SET confirmado = 1
        WHERE id = ?
          AND productor_id IN (
              SELECT id FROM productores WHERE usuario_id = ?
          )
    ''', (detalle_id, usuario_id))
    conexion.commit()
    conexion.close()
