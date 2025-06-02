from flask import Flask, render_template, request, send_file
import os
import io
from docx2pdf import convert
import uuid
import pythoncom
from werkzeug.utils import secure_filename 
from pdf2docx import Converter
from PIL import Image
import fitz  # PyMuPDF
import zipfile

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/pdfimg')
def pdfimg():
    return render_template('pdfimg.html')

@app.route('/sobre')
def sobre():
    return render_template('sobre.html')

@app.route('/pdfword')
def pdfword():
    return render_template('pdfword.html')

@app.route('/wordpdf')
def wordpdf():
    return render_template('wordpdf.html')

@app.route('/imgpdf')
def imgpdf():
    return render_template('imgpdf.html')

# DOCX → PDF
@app.route('/convert', methods=['POST'])
def convert_to_pdf():
    if 'file' not in request.files:
        return 'Nenhum arquivo enviado.', 400
    files = request.files.getlist('file')
    if len(files) == 0:
        return 'Nenhum arquivo selecionado.', 400

    pythoncom.CoInitialize()
    converted_files = []

    for file in files:
        if file and file.filename.endswith('.docx'):
            original_filename = secure_filename(file.filename)
            basename, _ = os.path.splitext(original_filename)
            unique_suffix = str(uuid.uuid4())[:8]
            docx_filename = f"{basename}_{unique_suffix}.docx"
            pdf_filename = f"{basename}.pdf"
            docx_path = os.path.join(app.config['UPLOAD_FOLDER'], docx_filename)
            pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], pdf_filename)
            file.save(docx_path)
            try:
                convert(docx_path, pdf_path)
                converted_files.append(pdf_path)  
            except Exception as e:
                pythoncom.CoUninitialize()
                return f"Erro ao converter {file.filename}: {e}", 500
    pythoncom.CoUninitialize()

    if len(converted_files) > 1:
        zip_filename = str(uuid.uuid4()) + '.zip'
        zip_path = os.path.join(app.config['UPLOAD_FOLDER'], zip_filename)
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for pdf_file in converted_files:
                zipf.write(pdf_file, os.path.basename(pdf_file))
        return send_file(zip_path, as_attachment=True)

    return send_file(converted_files[0], as_attachment=True)

# PDF → DOCX
@app.route('/convert-pdf', methods=['POST'])
def convert_pdf_to_word():
    if 'file' not in request.files:
        return 'Nenhum arquivo enviado.', 400
    files = request.files.getlist('file')
    if len(files) == 0:
        return 'Nenhum arquivo selecionado.', 400

    converted_files = []
    for file in files:
        if file and file.filename.endswith('.pdf'):
            original_filename = secure_filename(file.filename)
            basename, _ = os.path.splitext(original_filename)
            unique_suffix = str(uuid.uuid4())[:8]
            pdf_filename = f"{basename}_{unique_suffix}.pdf"
            docx_filename = f"{basename}.docx"
            pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], pdf_filename)
            docx_path = os.path.join(app.config['UPLOAD_FOLDER'], docx_filename)
            file.save(pdf_path)

            try:
                cv = Converter(pdf_path)
                cv.convert(docx_path)
                cv.close()
                converted_files.append(docx_path)
            except Exception as e:
                return f"Erro ao converter {file.filename}: {e}", 500

    if len(converted_files) > 1:
        zip_filename = str(uuid.uuid4()) + '.zip'
        zip_path = os.path.join(app.config['UPLOAD_FOLDER'], zip_filename)
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for word_file in converted_files:
                zipf.write(word_file, os.path.basename(word_file))
        return send_file(zip_path, as_attachment=True)

    return send_file(converted_files[0], as_attachment=True)

# PDF → Imagem (com PyMuPDF)
@app.route('/convert-pdf-img', methods=['POST'])
def convert_pdf_to_img():
    if 'file' not in request.files:
        return 'Nenhum arquivo enviado.', 400
    files = request.files.getlist('file')
    if len(files) == 0:
        return 'Nenhum arquivo selecionado.', 400

    converted_files = []

    for file in files:
        if file and file.filename.endswith('.pdf'):
            pdf_bytes = file.read()
            try:
                doc = fitz.open(stream=pdf_bytes, filetype="pdf")
                basename = os.path.splitext(secure_filename(file.filename))[0]
                for i in range(len(doc)):
                    page = doc.load_page(i)
                    pix = page.get_pixmap()
                    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                    img_filename = f"{basename}_page_{i+1}_{uuid.uuid4().hex[:6]}.png"
                    img_path = os.path.join(app.config['UPLOAD_FOLDER'], img_filename)
                    img.save(img_path, 'PNG')
                    converted_files.append(img_path)
            except Exception as e:
                return f"Erro ao converter {file.filename}: {e}", 500

    if len(converted_files) > 1:
        zip_filename = str(uuid.uuid4()) + '.zip'
        zip_path = os.path.join(app.config['UPLOAD_FOLDER'], zip_filename)
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for img_file in converted_files:
                zipf.write(img_file, os.path.basename(img_file))
        return send_file(zip_path, as_attachment=True)

    return send_file(converted_files[0], as_attachment=True)

# Imagem → PDF
@app.route('/convert-img-pdf', methods=['POST'])
def convert_img_to_pdf():
    if 'file' not in request.files:
        return 'Nenhuma imagem enviada.', 400
    files = request.files.getlist('file')
    if len(files) == 0:
        return 'Nenhuma imagem selecionada.', 400

    images = []
    for file in files:
        if file and file.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp')):
            try:
                img = Image.open(file)
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                images.append(img)
            except Exception as e:
                return f"Erro ao processar {file.filename}: {e}", 500

    if not images:
        return 'Nenhuma imagem válida.', 400

    pdf_io = io.BytesIO()
    images[0].save(pdf_io, format='PDF', save_all=True, append_images=images[1:])
    pdf_io.seek(0)

    return send_file(pdf_io, as_attachment=True, download_name='imagens_convertidas.pdf', mimetype='application/pdf')

if __name__ == '__main__':
    app.run(debug=True)
