import os
import queue
import base64
import re
from flask import Flask, render_template, request, send_from_directory, jsonify

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Thread-safe queue for long polling
update_queue = queue.Queue()
current_filename = "default.png"

def sanitize_filename(filename):
    # Convert to lowercase, replace spaces with underscores, remove unsafe characters
    filename = filename.lower().strip()
    filename = re.sub(r'\s+', '_', filename)
    filename = re.sub(r'[^a-z0-9_.-]', '', filename)
    return filename if filename else "image.png"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    global current_filename
    if 'file' in request.files:
        file = request.files['file']
        if file.filename != '':
            filename = sanitize_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            current_filename = filename
            
            # Clear queue and notify waiting ESP32
            while not update_queue.empty():
                try:
                    update_queue.get_nowait()
                except queue.Empty:
                    pass
            update_queue.put(filename)
            return jsonify({"status": "success", "filename": filename})
    return jsonify({"status": "error", "message": "No file uploaded"}), 400

@app.route('/upload_drawing', methods=['POST'])
def upload_drawing():
    global current_filename
    data = request.get_json()
    if data and 'image' in data:
        try:
            header, encoded = data['image'].split(',', 1)
            img_bytes = base64.b64decode(encoded)
            filename = 'drawing.png'
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            with open(filepath, 'wb') as f:
                f.write(img_bytes)
            
            current_filename = filename
            while not update_queue.empty():
                try:
                    update_queue.get_nowait()
                except queue.Empty:
                    pass
            update_queue.put(filename)
            return jsonify({"status": "success", "filename": filename})
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 400
    return jsonify({"status": "error", "message": "No image data provided"}), 400

@app.route('/longPoll')
def long_poll():
    try:
        update_queue.get(timeout=15)
    except queue.Empty:
        pass
    
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], current_filename)
    if os.path.exists(filepath):
        response = send_from_directory(app.config['UPLOAD_FOLDER'], current_filename)
        response.headers['imgname'] = current_filename
        return response
    return "No image found", 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
