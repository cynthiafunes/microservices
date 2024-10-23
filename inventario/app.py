from flask import Flask, request, jsonify
from database import conectar_db
from jwt_auth import token_required
import pika
import threading
from resilience import retry_config, cb

app = Flask(__name__)

@retry_config
@cb
def consumir_mensajes():
    def callback(ch, method, properties, body):
        mensaje = body.decode()
        accion, datos = mensaje.split(':', 1)
        if accion == 'crear':
            producto_id = datos
            conn = conectar_db()
            cur = conn.cursor()
            cur.execute("INSERT INTO inventario (producto_id, cantidad) VALUES (%s, 0) ON CONFLICT DO NOTHING",
                        (producto_id,))
            conn.commit()
            cur.close()
            conn.close()
            
    connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
    channel = connection.channel()
    channel.queue_declare(queue='productos_queue')
    channel.basic_consume(queue='productos_queue', on_message_callback=callback, auto_ack=True)
    channel.start_consuming()

threading.Thread(target=consumir_mensajes, daemon=True).start()

@app.route('/inventario', methods=['GET'])
@token_required
def obtener_todos_inventarios():
    conn = conectar_db()
    cur = conn.cursor()
    cur.execute("SELECT producto_id, cantidad FROM inventario")
    inventarios = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify([{"producto_id": i[0], "cantidad": i[1]} for i in inventarios])

@app.route('/inventario/<int:producto_id>', methods=['GET'])
@token_required
def obtener_inventario_producto(producto_id):
    conn = conectar_db()
    cur = conn.cursor()
    cur.execute("SELECT cantidad FROM inventario WHERE producto_id = %s", (producto_id,))
    item = cur.fetchone()
    cur.close()
    conn.close()
    if item:
        return jsonify({"producto_id": producto_id, "cantidad": item[0]})
    return jsonify({"error": "Producto no encontrado en inventario"}), 404

@app.route('/inventario/<int:producto_id>', methods=['PUT'])
@token_required
def actualizar_inventario(producto_id):
    datos = request.json
    if 'cantidad' not in datos:
        return jsonify({"error": "Se requiere el campo 'cantidad'"}), 400
    
    conn = conectar_db()
    cur = conn.cursor()
    cur.execute("UPDATE inventario SET cantidad = %s WHERE producto_id = %s RETURNING producto_id",
                (datos['cantidad'], producto_id))
    producto_actualizado = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    
    if producto_actualizado:
        return jsonify({"mensaje": "Inventario actualizado exitosamente"}), 200
    else:
        return jsonify({"error": "Producto no encontrado en inventario"}), 404

if __name__ == '__main__':
    app.run(port=5001, debug=True)