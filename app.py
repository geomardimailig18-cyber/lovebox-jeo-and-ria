import os
from flask import Flask, render_template, request, send_file, jsonify
from werkzeug.utils import secure_filename

app = Flask(__name__, static_folder='static', template_folder='templates')

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Global variables to manage the image queue for the ESP32
pending_image_path = None
pending_image_filename = None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload_drawing', methods=['POST'])
def upload_drawing():
    global pending_image_path, pending_image_filename
    
    # Accept incoming file payload from the web frontend dashboard
    file = request.files.get('image') or request.files.get('file') or request.files.get('drawing')
    
    if not file or file.filename == '':
        return jsonify({"error": "No file uploaded"}), 400

    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    # Queue the image for the ESP32 longPoll request
    pending_image_path = filepath
    pending_image_filename = filename

    return jsonify({"status": "success", "filename": filename}), 200

@app.route('/longPoll', methods=['GET'])
def long_poll():
    global pending_image_path, pending_image_filename

    # Return 204 No Content if no image is waiting instead of throwing a 404 error
    if not pending_image_path or not os.path.exists(pending_image_path):
        return "", 204

    try:
        response = send_file(pending_image_path)
        response.headers["imgname"] = pending_image_filename
        
        # Clear the queue once successfully fetched by the ESP32 device
        pending_image_path = None
        pending_image_filename = None
        
        return response
    except Exception as e:
        return str(e), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
