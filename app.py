import os
import logging
import sys
import uuid
import base64
from io import BytesIO
from datetime import datetime

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from werkzeug.middleware.proxy_fix import ProxyFix

from extensions import db  # ✅ your db object
from ocr_processor import process_image
from text_processor import extract_medical_entities
from document_manager import DocumentManager  # ✅ uses models correctly

# --------------------- Logging Setup ---------------------
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# --------------------- Tesseract Path ---------------------
tessdata_path = os.path.join(os.getcwd(), 'tessdata')
if os.path.exists(tessdata_path):
    os.environ['TESSDATA_PREFIX'] = tessdata_path
    logger.info(f"TESSDATA_PREFIX set to {tessdata_path}")

# --------------------- Flask App Setup ---------------------
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev_secret_key")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Database config
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///your_database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# Import models only after db is ready
with app.app_context():
    from models import Document
    db.create_all()
    logger.info("Database tables created")

logger.info(f"Database URL: {os.environ.get('DATABASE_URL')}")

# --------------------- Document Manager ---------------------
document_manager = DocumentManager()

# Upload settings
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'tiff', 'pdf'}
MAX_CONTENT_LENGTH = 16 * 1024 * 1024

# --------------------- Routes ---------------------

@app.route('/')
def index():
    return render_template('index.html')

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/process', methods=['POST'])
def process_document():
    try:
        if 'file' not in request.files and 'image_data' not in request.form:
            flash('No file part or image data', 'error')
            return redirect(request.url)

        document_type = request.form.get('document_type', 'prescription')
        document_id = str(uuid.uuid4())

        # File Upload
        if 'file' in request.files:
            file = request.files['file']
            if file.filename == '':
                flash('No selected file', 'error')
                return redirect(request.url)
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file_data = file.read()
                ocr_text = process_image(file_data)
                processed_data = extract_medical_entities(ocr_text, document_type)
                document = {
                    'id': document_id,
                    'name': filename,
                    'type': document_type,
                    'created_at': datetime.now().isoformat(),
                    'raw_text': ocr_text,
                    'processed_data': processed_data,
                    'image_data': base64.b64encode(file_data).decode('utf-8')
                }
                document_manager.add_document(document)
                return redirect(url_for('view_document', document_id=document_id))

        # Camera Capture
        elif 'image_data' in request.form:
            image_data = request.form['image_data'].split(',')[1] if ',' in request.form['image_data'] else request.form['image_data']
            image_bytes = base64.b64decode(image_data)
            ocr_text = process_image(image_bytes)
            processed_data = extract_medical_entities(ocr_text, document_type)
            document = {
                'id': document_id,
                'name': f"{document_type}{datetime.now().strftime('%Y%m%d%H%M%S')}.jpg",
                'type': document_type,
                'created_at': datetime.now().isoformat(),
                'raw_text': ocr_text,
                'processed_data': processed_data,
                'image_data': image_data
            }
            document_manager.add_document(document)
            return redirect(url_for('view_document', document_id=document_id))

        flash('Invalid file type.', 'error')
        return redirect(request.url)

    except Exception as e:
        logger.error(f"Error processing document: {str(e)}")
        flash(f"Error: {str(e)}", 'error')
        return redirect(url_for('index'))

@app.route('/documents')
def documents():
    return render_template('documents.html', documents=document_manager.get_all_documents())

@app.route('/document/<document_id>')
def view_document(document_id):
    doc = document_manager.get_document(document_id)
    if not doc:
        flash("Document not found", "error")
        return redirect(url_for('documents'))
    return render_template('document_view.html', document=doc)

@app.route('/document/<document_id>/export', methods=['GET'])
def export_document(document_id):
    doc = document_manager.get_document(document_id)
    if not doc:
        flash("Document not found", "error")
        return redirect(url_for('documents'))

    format_type = request.args.get('format', 'json')
    if format_type == 'json':
        export_data = doc.copy()
        export_data.pop('image_data', None)
        return jsonify(export_data)
    elif format_type == 'txt':
        result = f"Document: {doc['name']}\nType: {doc['type']}\nCreated: {doc['created_at']}\n\n"
        result += "EXTRACTED INFORMATION\n----------------------\n\n"
        for k, v in doc['processed_data'].items():
            result += f"{k.upper()}:\n"
            if isinstance(v, list):
                result += '\n'.join(f"- {item}" for item in v)
            else:
                result += str(v)
            result += "\n\n"
        result += f"\nRAW TEXT\n--------\n{doc['raw_text']}"
        buffer = BytesIO()
        buffer.write(result.encode('utf-8'))
        buffer.seek(0)
        filename = f"{doc['name'].split('.')[0]}_export.txt"
        return send_file(buffer, as_attachment=True, download_name=filename, mimetype='text/plain')
    else:
        flash("Unsupported format", "error")
        return redirect(url_for('view_document', document_id=document_id))

@app.route('/document/<document_id>/delete', methods=['POST'])
def delete_document(document_id):
    document_manager.delete_document(document_id)
    flash('Document deleted successfully', 'success')
    return redirect(url_for('documents'))

@app.route('/profile')
def profile():
    stats = {
        'total': len(document_manager.get_all_documents()),
        'by_type': document_manager.get_document_type_counts()
    }
    return render_template('profile.html', stats=stats)

@app.errorhandler(413)
def too_large(e):
    flash(f'File too large. Max size is {MAX_CONTENT_LENGTH // (1024 * 1024)}MB', 'error')
    return redirect(url_for('index'))

@app.errorhandler(404)
def not_found(e):
    return render_template('index.html', error="Page not found"), 404

@app.errorhandler(500)
def internal_error(e):
    return render_template('index.html', error="Internal server error"), 500

# ✅ Correct this line (was wrong in your code)
if __name__ == '__main__':
    app.run(debug=True)
