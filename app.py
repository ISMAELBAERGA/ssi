import os
import mysql.connector
import resend  # Librería oficial para enviar los correos electrónicos
from flask import Flask, render_template, request, redirect, url_for, flash

app = Flask(__name__)
# Llave de seguridad requerida por Flask para permitir mostrar alertas de éxito/error en pantalla
app.secret_key = os.environ.get('SECRET_KEY', 'un-token-muy-seguro-de-mantenimiento-12345')

# Configurar la API key de Resend leyendo la variable de entorno de Render
resend.api_key = os.environ.get('RESEND_API_KEY')

def obtener_conexion():
    """Establece la conexión con la base de datos MySQL usando variables de entorno."""
    return mysql.connector.connect(
        host=os.environ.get('DB_HOST'),
        database=os.environ.get('DB_NAME'),
        user=os.environ.get('DB_USER'),
        password=os.environ.get('DB_PASSWORD'),
        port=os.environ.get('DB_PORT', 3306)
    )

def crear_tablas_iniciales():
    """Crea las tablas de clientes, proyectos y hojas de servicio de forma automática si no existen."""
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    
    # 1. Tabla de Clientes (Oficinas, pequeños negocios, etc.)
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
    
    # 2. Tabla de Proyectos (Para infraestructura de redes y despliegues de cámaras)
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
    
    # 3. Tabla de Hojas de Servicio (Registros individuales de mantenimiento o averías)
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

# Ejecutar la verificación/creación automática de tablas al arrancar la app
try:
    crear_tablas_iniciales()
    print("Tablas verificadas/creadas con éxito en MySQL.")
except Exception as e:
    print(f"Error crítico al estructurar la base de datos: {str(e)}")
# --- ENRUTAMIENTO Y LÓGICA DE LA APLICACIÓN WEB ---

@app.route('/')
def inicio():
    """Redirige automáticamente la página de entrada hacia el panel de clientes."""
    return redirect(url_for('clientes_vista'))


# == SECCIÓN 1: GESTIÓN DE CLIENTES ==

@app.route('/clientes', methods=['GET'])
def clientes_vista():
    """Muestra el formulario e historial de todos los clientes registrados."""
    try:
        conexion = obtener_conexion()
        cursor = conexion.cursor()
        cursor.execute("SELECT id, nombre_negocio, nombre_contacto, telefono, email, direccion FROM clientes ORDER BY nombre_negocio ASC;")
        clientes = cursor.fetchall()
        cursor.close()
        conexion.close()
        return render_template('clientes.html', lista_clientes=clientes)
    except Exception as e:
        flash(f"Error al cargar la lista de clientes: {str(e)}", "danger")
        return render_template('clientes.html', lista_clientes=[])

@app.route('/clientes/nuevo', methods=['POST'])
def nuevo_cliente_procesar():
    """Recibe los datos del formulario web e inserta un nuevo cliente en MySQL."""
    nombre_negocio = request.form.get('nombre_negocio')
    nombre_contacto = request.form.get('nombre_contacto')
    telefono = request.form.get('telefono')
    email = request.form.get('email')
    direccion = request.form.get('direccion')

    try:
        conexion = obtener_conexion()
        cursor = conexion.cursor()
        query = """INSERT INTO clientes (nombre_negocio, nombre_contacto, telefono, email, direccion) 
                   VALUES (%s, %s, %s, %s, %s)"""
        cursor.execute(query, (nombre_negocio, nombre_contacto, telefono, email, direccion))
        conexion.commit()
        cursor.close()
        conexion.close()
        flash(f"¡Cliente '{nombre_negocio}' guardado con éxito en el sistema!", "success")
    except Exception as e:
        flash(f"No se pudo registrar el cliente en la base de datos: {str(e)}", "danger")
    
    return redirect(url_for('clientes_vista'))


# == SECCIÓN 2: HOJAS DE SERVICIO TÉCNICO Y ENVÍO DE CORREOS ==

@app.route('/hoja-servicio', methods=['GET'])
def hoja_servicio_vista():
    """Muestra el formulario para crear una nueva hoja de servicio técnico."""
    try:
        # Extrae la lista de clientes para poder rellenar el menú desplegable (Select) del formulario
        conexion = obtener_conexion()
        cursor = conexion.cursor()
        cursor.execute("SELECT id, nombre_negocio, nombre_contacto, telefono, email FROM clientes ORDER BY nombre_negocio ASC;")
        clientes = cursor.fetchall()
        cursor.close()
        conexion.close()
        return render_template('hoja_servicio.html', lista_clientes=clientes)
    except Exception as e:
        flash(f"Error al abrir el formulario técnico: {str(e)}", "danger")
        return redirect(url_for('inicio'))

@app.route('/hoja-servicio/nueva', methods=['POST'])
def nueva_hoja_procesar():
    """Guarda la hoja de servicio en MySQL y la envía de inmediato por correo electrónico al cliente."""
    cliente_id = request.form.get('cliente_id')
    fecha_servicio = request.form.get('fecha_servicio')
    tipo_servicio = request.form.get('tipo_servicio')
    tecnico_asignado = request.form.get('tecnico_asignado')
    descripcion_trabajo = request.form.get('descripcion_trabajo')
    materiales_usados = request.form.get('materiales_usados')
    quiere_correo = request.form.get('enviar_correo') # Devuelve 'on' si la casilla web está marcada

    try:
        conexion = obtener_conexion()
        cursor = conexion.cursor()
        
        # 1. Buscar los datos de contacto del cliente seleccionado para el envío de correo
        cursor.execute("SELECT nombre_negocio, email FROM clientes WHERE id = %s", (cliente_id,))
        cliente_datos = cursor.fetchone()
        if not cliente_datos:
            flash("Error: El cliente seleccionado no fue encontrado en el sistema.", "danger")
            return redirect(url_for('hoja_servicio_vista'))
        
        nombre_negocio_cliente, email_cliente = cliente_datos

        # 2. Insertar los campos técnicos de la hoja de servicio en MySQL
        query = """INSERT INTO hojas_servicio (cliente_id, fecha_servicio, tipo_servicio, descripcion_trabajo, materiales_usados, tecnico_asignado) 
                   VALUES (%s, %s, %s, %s, %s, %s)"""
        cursor.execute(query, (cliente_id, fecha_servicio, tipo_servicio, descripcion_trabajo, materiales_usados, tecnico_asignado))
        hoja_id = cursor.lastrowid  # Obtiene el ID numérico de la orden que se acaba de generar

        # 3. Lógica integrada para el despacho automático del correo electrónico
        enviado_ok = False
        if quiere_correo == 'on' and resend.api_key:
            # Estructuración visual del contenido del correo en formato HTML limpio
            contenido_html = f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: auto; padding: 20px; border: 1px solid #ddd; border-radius: 5px;">
                <h2 style="color: #333; text-align: center; border-bottom: 2px solid #0056b3; padding-bottom: 10px;">Hoja de Servicio Técnico - Orden #{hoja_id}</h2>
                <p><strong>Cliente / Negocio:</strong> {nombre_negocio_cliente}</p>
                <p><strong>Fecha del Servicio:</strong> {fecha_servicio}</p>
                <p><strong>Tipo de Infraestructura:</strong> {tipo_servicio}</p>
                <p><strong>Técnico Encargado:</strong> {tecnico_asignado}</p>
                <hr style="border: 0; border-top: 1px solid #eee;" />
                <h3 style="color: #0056b3;">1. Descripción Detallada del Trabajo:</h3>
                <p style="background-color: #f9f9f9; padding: 15px; border-left: 4px solid #0056b3; line-height: 1.6;">{descripcion_trabajo}</p>
                
                <h3 style="color: #0056b3;">2. Materiales e Infraestructura Utilizada:</h3>
                <p style="background-color: #f9f9f9; padding: 15px; border-left: 4px solid #6c757d; line-height: 1.6;">{materiales_usados if materiales_usados else 'No se reportó uso de materiales adicionales o repuestos.'}</p>
                <hr style="border: 0; border-top: 1px solid #eee;" />
                <p style="color: #888; font-size: 11px; text-align: center;">Este es un comprobante automático digital emitido por el sistema técnico de redes e IT.</p>
            </div>
            """
            
            # Enviar el correo usando la API de Resend
            # Nota: El remitente gratuito por defecto en cuentas nuevas es 'onboarding@resend.dev'
            resend.Emails.send({
                "from": "Soporte Tecnico <onboarding@resend.dev>",
                "to": email_cliente,
                "subject": f"Comprobante Servicio Técnico #{hoja_id} - {nombre_negocio_cliente}",
                "html": contenido_html
            })
            
            # Actualizar en la base de datos que el correo electrónico se envió de manera exitosa
            cursor.execute("UPDATE hojas_servicio SET enviado_por_correo = TRUE WHERE id = %s", (hoja_id,))
            enviado_ok = True

        conexion.commit()
        cursor.close()
        conexion.close()

        if enviado_ok:
            flash(f"¡Hoja de Servicio #{hoja_id} registrada con éxito y enviada por correo a {email_cliente}!", "success")
        else:
            flash(f"¡Hoja de Servicio #{hoja_id} registrada correctamente en la base de datos!", "success")

    except Exception as e:
        flash(f"Error crítico al procesar y enviar el reporte técnico: {str(e)}", "danger")
        
    return redirect(url_for('hoja_servicio_vista'))


if __name__ == '__main__':
    # Configuración para desarrollo local, en Render corre mediante Gunicorn
    app.run(debug=True)
