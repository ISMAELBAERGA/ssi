import os
import mysql.connector
from flask import Flask

app = Flask(__name__)

def obtener_conexion():
    return mysql.connector.connect(
        host=os.environ.get('DB_HOST'),
        database=os.environ.get('DB_NAME'),
        user=os.environ.get('DB_USER'),
        password=os.environ.get('DB_PASSWORD'),
        port=os.environ.get('DB_PORT', 3306)
    )

@app.route('/')
def inicio():
    try:
        conexion = obtener_conexion()
        cursor = conexion.cursor()
        cursor.execute("SELECT VERSION();")
        version = cursor.fetchone()
        cursor.close()
        conexion.close()
        return f"¡Conexión exitosa a Clever Cloud! Versión de MySQL: {version[0]}"
    except Exception as e:
        return f"Error de conexión: {str(e)}"

if __name__ == '__main__':
    app.run(debug=True)
