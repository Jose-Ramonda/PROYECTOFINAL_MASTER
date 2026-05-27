from flask import Flask, request
import os

app = Flask(__name__)

# Ruta donde se guardarán las fotos
UPLOAD_FOLDER = 'fotos_esp32'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

@app.route('/upload', methods=['POST'])
def upload():
    # En el ESP-IDF enviamos el buffer crudo, Flask lo recibe en 'request.data'
    img_data = request.data
    
    if img_data:
        filename = f"captura_{len(os.listdir(UPLOAD_FOLDER)) + 1}.jpg"
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        
        with open(filepath, "wb") as f:
            f.write(img_data)
        
        print(f"✅ Foto recibida y guardada como: {filename} ({len(img_data)} bytes)")
        return "Foto Recibida", 200
    else:
        print("❌ Se recibió un POST pero sin datos")
        return "Sin datos", 400

if __name__ == '__main__':
    # '0.0.0.0' permite conexiones de otros dispositivos en la misma red WiFi
    app.run(host='0.0.0.0', port=5000, debug=True)
