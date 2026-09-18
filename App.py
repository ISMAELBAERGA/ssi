import os
import mysql.connector
from flask import Flask, render_template, request, redirect, url_for, flash

app = Flask(__name__)
app.secret_key = 'clave_secreta_para_alertas_flash'

def obtener_conexion():
    return mysql.connector.connect(
        host=os.environ.get('DB_HOST'),
        database=os.environ.get('DB_NAME'),
        user=os.environ.get('DB_USER'),
        password=os.environ.get('DB_PASSWORD'),
        port=os.environ.get('DB_PORT', 3306)
    )

def crear_tablas_iniciales():
    """Crea las tablas de clientes, proyectos y hojas de servicio si no existen."""
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    
    # 1. Tabla de Clientes
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS clientes (
        id INT AUTO_INCREMENT PRIMARY KEY,
        nombre_negocio VARCHAR(150) NOT NULL,
        nombre_contacto VARCHAR(100),
        telefono VARCHAR(20),
        email VARCHAR(100) NOT NULL,
        direccion TEXT,
        fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    
    # 2. Tabla de Proyectos (Para infraestructura de redes y proyectos de cámaras)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS proyectos (
        id INT AUTO_INCREMENT PRIMARY KEY,
        cliente_id INT,
        nombre_proyecto VARCHAR(150) NOT NULL,
        tipo_proyecto ENUM('Cámaras', 'Redes de Data', 'Mixto', 'Otros') NOT NULL,
        descripcion TEXT,
        estado ENUM('Pendiente', 'En Desarrollo', 'Completado', 'Cancelado') DEFAULT 'Pendiente',
        fecha_inicio DATE,
        FOREIGN KEY (cliente_id) REFERENCES clientes(id) ON DELETE CASCADE
    );
    """)
    
    # 3. Tabla de Hojas de Servicio (Mantenimientos, Soporte IT, etc.)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS hojas_servicio (
        id INT AUTO_INCREMENT PRIMARY KEY,
        cliente_id INT NOT NULL,
        proyecto_id INT DEFAULT NULL,
        fecha_servicio DATE NOT NULL,
        tipo_servicio ENUM('Mantenimiento Cámaras', 'Infraestructura Redes', 'Soporte IT Oficina', 'Otro') NOT NULL,
        descripcion_trabajo TEXT NOT NULL,
        materiales_usados TEXT,
        tecnico_asignado VARCHAR(100),
        enviado_por_correo BOOLEAN DEFAULT FALSE,
        fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (cliente_id) REFERENCES clientes(id) ON DELETE CASCADE,
        FOREIGN KEY (proyecto_id) REFERENCES proyectos(id) ON DELETE SET NULL
    );
    """)
    
    conexion.commit()
    cursor.close()
    conexion.close()

# Ejecutar la creación de tablas al arrancar la app
try:
    crear_tablas_iniciales()
    print("Tablas verificadas/creadas con éxito en MySQL.")
except Exception as e:
    print(f"Error al estructurar la base de datos: {str(e)}")


@app.route('/')
def inicio():
    return "¡Estructura de Base de Datos Lista! El sistema de Mantenimiento IT está preparado."

if __name__ == '__main__':
    app.run(debug=True)
