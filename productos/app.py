from flask import Flask, request, jsonify
from database import conectar_db
from jwt_auth import token_required
import pika
from resilience import retry_config, cb
from logger import setup_logger

app = Flask(__name__)
logger = setup_logger('productos')

@retry_config
@cb
def publicar_mensaje(mensaje):
    logger.info(f"Intentando publicar mensaje: {mensaje}") 
    try:
        connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
        channel = connection.channel()
        channel.queue_declare(queue='productos_queue')
        channel.basic_publish(exchange='', routing_key='productos_queue', body=mensaje)
        connection.close()
        logger.info("Mensaje publicado exitosamente") 
    except Exception as e:
        logger.error(f"Error al publicar mensaje: {str(e)}")
        raise

@app.route('/productos', methods=['GET'])
@token_required
def obtener_productos():
    conn = conectar_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM productos")
    productos = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify([{"id": p[0], "nombre": p[1], "descripcion": p[2]} for p in productos])

@app.route('/productos/<int:id>', methods=['GET'])
@token_required
def obtener_producto(id):
    conn = conectar_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM productos WHERE id = %s", (id,))
    producto = cur.fetchone()
    cur.close()
    conn.close()
    if producto:
        return jsonify({"id": producto[0], "nombre": producto[1], "descripcion": producto[2]})
    return jsonify({"error": "Producto no encontrado"}), 404

@app.route('/productos', methods=['POST'])
@token_required
def crear_producto():
    nuevo_producto = request.json
    if not nuevo_producto or 'nombre' not in nuevo_producto or 'descripcion' not in nuevo_producto:
        return jsonify({"error": "Datos de producto invalidos"}), 400
    
    if not nuevo_producto['nombre'].strip() or not nuevo_producto['descripcion'].strip():
        return jsonify({"error": "El nombre y la descripción del producto no pueden estar vacíos"}), 400

    conn = conectar_db()
    cur = conn.cursor()
    conn.autocommit = False
    cur.execute("INSERT INTO productos (nombre, descripcion) VALUES (%s, %s) RETURNING id",
                (nuevo_producto['nombre'], nuevo_producto['descripcion']))
    id_producto = cur.fetchone()[0]
    
    try:
        publicar_mensaje(f"crear:{id_producto}")
    except Exception as e:
        conn.rollback()
        logger.error(f"No se pudo publicar el mensaje {id_producto}")
        return jsonify({"error": "No se pudo crear el producto debido a un error de comunicación"}), 500
    
    conn.commit()
    return jsonify({"id": id_producto, "mensaje": "Producto creado exitosamente"}), 201
    cur.close()
    conn.close()

@app.route('/productos/<int:id>', methods=['PUT'])
@token_required
def actualizar_producto(id):
    datos = request.json
    conn = conectar_db()
    cur = conn.cursor()
    cur.execute("UPDATE productos SET nombre = %s, descripcion = %s WHERE id = %s RETURNING id",
                (datos['nombre'], datos['descripcion'], id))
    producto_actualizado = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    if producto_actualizado:
        return jsonify({"mensaje": "Producto actualizado exitosamente"})
    return jsonify({"error": "Producto no encontrado"}), 404

if __name__ == '__main__':
    logger.info("Iniciando servicio de productos")
    app.run(port=5000, debug=True)