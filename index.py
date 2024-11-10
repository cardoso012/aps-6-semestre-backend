import sqlite3
import os
from flask import Flask, request, jsonify, session, g
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from deepface import DeepFace
from flask_cors import CORS, cross_origin

app = Flask(__name__)
app.secret_key = 'sua_chave_secreta_aqui'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 40 * 1024 * 1024  # 40 MB
cors = CORS(
    app, 
    origins=["http://localhost:5173"], 
    supports_credentials=True, 
    allow_headers=['Content-Type', 'Authorization'], 
    methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"]
)

DATABASE = 'database.db'
MODEL_NAME = 'Facenet512'

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    return db

@app.teardown_appcontext
def fechar_conexao(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                senha TEXT NOT NULL,
                foto TEXT NOT NULL
            )
        """)
        db.commit()

init_db()

@app.route('/cadastro', methods=['POST'])
@cross_origin()
def cadastro():
    nome = request.form['nome']
    email = request.form['email']
    senha = request.form['senha']
    foto = request.files['foto']

    if not foto:
        return jsonify({'mensagem': 'Nenhuma foto enviada.'}), 400
    
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])

    filename = secure_filename(foto.filename)
    caminho_foto = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    foto.save(caminho_foto)

    senha_hash = generate_password_hash(senha)

    db = get_db()
    cursor = db.cursor()
    try:
        cursor.execute('''
            INSERT INTO usuarios (nome, email, senha, foto)
            VALUES (?, ?, ?, ?)
        ''', (nome, email, senha_hash, caminho_foto))
        db.commit()
    except sqlite3.IntegrityError:
        return jsonify({'mensagem': 'Email já cadastrado.'}), 400

    return jsonify({'mensagem': 'Usuário cadastrado com sucesso.'}), 201
    
@app.route('/login', methods=['POST'])
@cross_origin(supports_credentials=True, origins=['http://localhost:5173'])
def login():
    if request.method == 'OPTIONS':
        return '', 204
    
    email = request.form['email']
    senha = request.form['senha']

    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT * FROM usuarios WHERE email = ?', (email,))
    usuario = cursor.fetchone()

    if usuario and check_password_hash(usuario[3], senha):
        session['usuario_id'] = usuario[0]
        return jsonify({'login': True, 'mensagem': 'Login realizado com sucesso.'}), 200
    else:
        return jsonify({'login': False, 'mensagem': 'Credenciais inválidas.'}), 401

@app.route('/comparar', methods=['POST', 'OPTIONS'])
@cross_origin(supports_credentials=True, origins=['http://localhost:5173'])
def compare():
    if request.method == 'OPTIONS':
        return '', 204
    
    if 'usuario_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    image = request.files['imagem']
    if not image:
        return jsonify({'error': 'No image provided'}), 400
    
    image_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(image.filename))
    image.save(image_path)

    user_id = session['usuario_id']
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT foto FROM usuarios WHERE id = ?', (user_id,))
    user_photo_path = cursor.fetchone()
    
    if not user_photo_path:
        return jsonify({'error': 'User photo not found'}), 404
    
    img1_representation = DeepFace.represent(user_photo_path[0], model_name=MODEL_NAME)[0]["embedding"]
    img2_representation = DeepFace.represent(image_path, model_name=MODEL_NAME)[0]["embedding"]

    result = DeepFace.verify(
        img1_path=img1_representation, 
        img2_path=img2_representation, 
        model_name=MODEL_NAME,
        distance_metric='cosine',
        enforce_detection=True
    )

    similarity = (1 - result['distance'] / result['threshold']) * 100
    os.remove(image_path)

    return jsonify({
        'similaridade': similarity,
        'verified': result['verified']
    }), 200

if __name__ == '__main__':
    if not os.path.exists('uploads'):
        os.makedirs('uploads')
    app.run(debug=True)
