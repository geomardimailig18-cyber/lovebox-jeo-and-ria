import os
import queue
import base64
import re
from flask import Flask, render_template, request, send_from_directory, jsonify
from PIL import Image, ImageOps

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

MUSIC_FOLDER = 'music'
app.config['MUSIC_FOLDER'] = MUSIC_FOLDER

# Thread-safe queue for long polling
update_queue = queue.Queue()
current_filename = "default.png"

def sanitize_filename(filename):
    filename = filename.lower().strip()
    filename = re.sub(r'\s+', '_', filename)
    filename = re.sub(r'[^a-z0-9_.-]', '', filename)
    return filename if filename else "image.png"

def resize_if_needed(filepath, output_filepath=None):
    if output_filepath is None:
        output_filepath = filepath
    try:
        with Image.open(filepath) as img:
            try:
                img = ImageOps.exif_transpose(img)
            except Exception:
                pass

            if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
                background = Image.new("RGB", img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                if img.mode == 'RGBA':
                    background.paste(img, mask=img.split()[3])
                else:
                    background.paste(img)
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')

            if img.width > 320:
                w_percent = (320 / float(img.width))
                h_size = int(float(img.height) * float(w_percent))
                resample_method = getattr(Image, 'Resampling', Image).LANCZOS
                img = img.resize((320, h_size), resample_method)

            if 'icc_profile' in img.info:
                del img.info['icc_profile']

            img.save(output_filepath, "PNG", optimize=False)
    except Exception as e:
        print(f"Skipping resize/conversion due to error: {e}")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    global current_filename
    if 'file' in request.files:
        file = request.files['file']
        if file.filename != '':
            raw_filename = sanitize_filename(file.filename)
            temp_filepath = os.path.join(app.config['UPLOAD_FOLDER'], raw_filename)
            file.save(temp_filepath)
            
            # GIFs are kept as .gif for animated playback
            if raw_filename.endswith('.gif'):
                filename = raw_filename
            else:
                # Automatically convert .jfif, .jpg, .jpeg, .webp, etc. to .png
                base_name = os.path.splitext(raw_filename)[0]
                filename = f"{base_name}.png"
                png_filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                
                resize_if_needed(temp_filepath, png_filepath)
                
                # Remove temporary original if it had a different extension
                if temp_filepath != png_filepath and os.path.exists(temp_filepath):
                    os.remove(temp_filepath)

            current_filename = filename
            
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
            
            resize_if_needed(filepath)

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
        # Wait up to 15 seconds to prevent Render's proxy from killing idle sockets (avoids error -11)
        update_queue.get(timeout=15)
        
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], current_filename)
        if os.path.exists(filepath):
            response = send_from_directory(app.config['UPLOAD_FOLDER'], current_filename)
            response.headers['imgname'] = current_filename
            return response
    except queue.Empty:
        pass
    
    # Returns 404 on timeout; the ESP32 gracefully catches this and immediately re-polls
    return "No new image", 404

@app.route('/music/songs.json')
def music_manifest():
    return send_from_directory(app.config['MUSIC_FOLDER'], 'songs.json')

@app.route('/music/<path:filename>')
def music_file(filename):
    # send_from_directory safely rejects path traversal attempts (../ etc.)
    return send_from_directory(app.config['MUSIC_FOLDER'], filename)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
