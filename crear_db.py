# =====================================================================
# crear_db.py
# ---------------------------------------------------------------------
# Este script arma la base de datos SQLite desde cero: crea las tablas
# y carga datos de ejemplo (usuarios, productores y publicaciones de
# espacio libre) para poder probar la aplicación sin cargar todo a mano.
#
# SE EJECUTA UNA SOLA VEZ ANTES DE app.py (o cada vez que se quiera
# reiniciar la base de datos):
#
#     python crear_db.py
#
# Es seguro ejecutarlo varias veces: primero borra las tablas viejas
# (si existían) y las vuelve a crear limpias.
# =====================================================================

import sqlite3
from werkzeug.security import generate_password_hash

# Nos conectamos a database.db. Si el archivo no existe todavía,
# sqlite3 lo crea automáticamente en este mismo momento.
conexion = sqlite3.connect('database.db')
cursor = conexion.cursor()

# ---------------------------------------------------------------------
# Borramos las tablas si ya existían, para poder correr este script
# las veces que haga falta durante el desarrollo sin que tire error.
# ---------------------------------------------------------------------
cursor.execute('DROP TABLE IF EXISTS usuarios')
cursor.execute('DROP TABLE IF EXISTS productores')
cursor.execute('DROP TABLE IF EXISTS espacios')
cursor.execute('DROP TABLE IF EXISTS vehiculos')
cursor.execute('DROP TABLE IF EXISTS coordinaciones')
cursor.execute('DROP TABLE IF EXISTS coordinacion_detalle')

# ---------------------------------------------------------------------
# Tabla usuarios: una fila por cada persona que puede iniciar sesión.
# La contraseña NUNCA se guarda tal cual la escribe el usuario: se
# guarda "hasheada" (encriptada) con una función de Flask/Werkzeug.
# ---------------------------------------------------------------------
cursor.execute('''
    CREATE TABLE usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL,
        tipo TEXT NOT NULL DEFAULT 'cliente' CHECK (tipo IN ('cliente', 'fletero'))
    )
''')

# ---------------------------------------------------------------------
# Tabla productores: cada fila es una "carga" que un usuario quiere
# llevar en el camión compartido. usuario_id conecta cada carga con
# quién la registró (así sabemos qué usuario cargó qué datos).
# ---------------------------------------------------------------------
cursor.execute('''
    CREATE TABLE productores (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario_id INTEGER NOT NULL,
        nombre_productor TEXT NOT NULL,
        localidad TEXT NOT NULL,
        producto TEXT NOT NULL,
        cantidad_cajones INTEGER NOT NULL,
        peso_por_cajon REAL NOT NULL,
        costo_viaje REAL NOT NULL,
        FOREIGN KEY (usuario_id) REFERENCES usuarios (id)
    )
''')

# ---------------------------------------------------------------------
# Tabla espacios: publicaciones de "tengo libres" / "necesito" cajones,
# usada por la Funcionalidad 3 (Lugar Libre) para buscar coincidencias
# entre distintos usuarios.
# ---------------------------------------------------------------------
cursor.execute('''
    CREATE TABLE espacios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario_id INTEGER NOT NULL,
        lugar_libre INTEGER NOT NULL DEFAULT 0,
        necesita INTEGER NOT NULL DEFAULT 0,
        FOREIGN KEY (usuario_id) REFERENCES usuarios (id)
    )
''')

# ---------------------------------------------------------------------
# Tabla vehiculos: cada fila es un camión que un usuario (el "fletero")
# carga con el peso y la cantidad de cajones que soporta transportar.
# Se usa en la Funcionalidad 5 (Vehículos) y también como base para la
# Funcionalidad 6 (Coordinar ruta).
# ---------------------------------------------------------------------
cursor.execute('''
    CREATE TABLE vehiculos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario_id INTEGER NOT NULL,
        patente TEXT NOT NULL,
        marca_modelo TEXT NOT NULL,
        peso_maximo REAL NOT NULL,
        cajones_maximo INTEGER NOT NULL,
        FOREIGN KEY (usuario_id) REFERENCES usuarios (id)
    )
''')

# ---------------------------------------------------------------------
# Tabla coordinaciones: cada fila es un viaje coordinado por un fletero
# con un vehículo puntual. Guarda la ruta ya calculada (localidades
# separadas por coma, en el orden a recorrer) y la distancia total, así
# no hay que recalcularla cada vez que se entra a la pantalla.
# ---------------------------------------------------------------------
cursor.execute('''
    CREATE TABLE coordinaciones (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario_id INTEGER NOT NULL,
        vehiculo_id INTEGER NOT NULL,
        ruta TEXT NOT NULL,
        distancia_total REAL NOT NULL,
        FOREIGN KEY (usuario_id) REFERENCES usuarios (id),
        FOREIGN KEY (vehiculo_id) REFERENCES vehiculos (id)
    )
''')

# ---------------------------------------------------------------------
# Tabla coordinacion_detalle: une cada coordinación con los productores
# (chacareros) que van a viajar en ese camión, y guarda si ese
# chacarero ya confirmó su carga o todavía está pendiente.
# ---------------------------------------------------------------------
cursor.execute('''
    CREATE TABLE coordinacion_detalle (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        coordinacion_id INTEGER NOT NULL,
        productor_id INTEGER NOT NULL,
        confirmado INTEGER NOT NULL DEFAULT 0,
        FOREIGN KEY (coordinacion_id) REFERENCES coordinaciones (id),
        FOREIGN KEY (productor_id) REFERENCES productores (id)
    )
''')

# =====================================================================
# DATOS DE EJEMPLO
# =====================================================================
# Se cargan 3 usuarios (los 2 obligatorios de la consigna + 1 extra de
# regalo para que las pruebas de "coincidencias" y "ahorro" tengan más
# de dos productores, como en el ejemplo del enunciado).
# =====================================================================

usuarios_prueba = [
    ('Juan Pérez', 'juan@gmail.com', generate_password_hash('1234'), 'cliente'),
    ('Pedro Gómez', 'pedro@gmail.com', generate_password_hash('1234'), 'fletero'),
    ('María López', 'maria@gmail.com', generate_password_hash('1234'), 'cliente'),
]
cursor.executemany(
    'INSERT INTO usuarios (nombre, email, password, tipo) VALUES (?, ?, ?, ?)',
    usuarios_prueba
)

# Un registro de producción por cada usuario de prueba.
# (usuario_id 1 = Juan, 2 = Pedro, 3 = María, según el orden de arriba)
productores_prueba = [
    (1, 'Juan Pérez', 'Costa de Araujo', 'Tomate', 150, 20, 120000),
    (2, 'Pedro Gómez', 'Jocolí', 'Uva', 100, 18, 90000),
    (3, 'María López', 'Tres de Mayo', 'Melón', 120, 25, 110000),
]
cursor.executemany('''
    INSERT INTO productores
        (usuario_id, nombre_productor, localidad, producto,
         cantidad_cajones, peso_por_cajon, costo_viaje)
    VALUES (?, ?, ?, ?, ?, ?, ?)
''', productores_prueba)

# Juan publica que tiene 10 cajones libres, y Pedro publica que necesita
# 10 cajones: al entrar a "Lugar libre" ya va a aparecer una coincidencia
# armada, lista para mostrar en la exposición.
espacios_prueba = [
    (1, 10, 0),   # Juan: tengo libres 10 cajones
    (2, 0, 10),   # Pedro: necesito 10 cajones
]
cursor.executemany(
    'INSERT INTO espacios (usuario_id, lugar_libre, necesita) VALUES (?, ?, ?)',
    espacios_prueba
)

# Pedro (usuario_id 2) es, además de productor, el fletero de prueba:
# carga su camión con el peso y los cajones que soporta.
vehiculos_prueba = [
    (2, 'AB123CD', 'Ford Cargo 1722', 8000, 400),
]
cursor.executemany('''
    INSERT INTO vehiculos (usuario_id, patente, marca_modelo, peso_maximo, cajones_maximo)
    VALUES (?, ?, ?, ?, ?)
''', vehiculos_prueba)

# Guardamos todo y cerramos la conexión.
conexion.commit()
conexion.close()

print('Base de datos creada correctamente: database.db')
print('')
print('Usuarios de prueba disponibles:')
print('  - juan@gmail.com  / 1234  (cliente)')
print('  - pedro@gmail.com / 1234  (fletero)')
print('  - maria@gmail.com / 1234  (cliente)')
print('')
print('Pedro ya tiene un vehículo cargado de prueba (patente AB123CD).')
