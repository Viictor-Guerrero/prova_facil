import sqlite3
import csv
import io
import re
import os
import json
from functools import wraps
from flask import Flask, render_template, request, jsonify, session, abort, redirect, url_for

app = Flask(__name__)
app.secret_key = "chave_secreta_amparo_legal_2026"

# Acessos
USUARIOS = {
    "admin": {"senha": "coordprovafacil@2026", "role": "admin", "nome": "Admin"},
    "victor.gsilva": {"senha": "prova@2026", "role": "victor.gsilva", "nome": "Victor Silva"},
    "amanda.pbeniamino": {"senha": "prova@2026", "role": "amanda.pbeniamino", "nome": "Amanda Pardal"},
    "marilia.ameireles": {"senha": "prova@2026", "role": "marilia.ameireles", "nome": "Marilia Meireles"},
    "ana.rgsriva": {"senha": "prova@2026", "role": "ana.rgsriva", "nome": "Ana Rita"},
    "luana.lsnascimento": {"senha": "prova@2026", "role": "luana.lsnascimento", "nome": "Luana Nascimento"},
    "thais.fsaraujo": {"senha": "prova@2026", "role": "thais.fsaraujo", "nome": "Thais Araujo"},
    "danilo.bsantos": {"senha": "prova@2026", "role": "danilo.bsantos", "nome": "Danilo Santos"},
    "gabriel.anicolau": {"senha": "prova@2026", "role": "gabriel.anicolau", "nome": "Gabriel"},
    "lilian.bsantos": {"senha": "prova@2026", "role": "lilian.bsantos", "nome": "Lilian Santos"},
    "amanda.ssantos": {"senha": "prova@2026", "role": "amanda.ssantos", "nome": "Amanda Santos"},
    "andreia.fdsantos": {"senha": "prova@2026", "role": "andreia.fdsantos", "nome": "Andreia Francisca"},
    "cintia.asantos": {"senha": "prova@2026", "role": "cintia.asantos", "nome": "Cintia Aparecida"},
    "jose.mmonteiro": {"senha": "prova@2026", "role": "jose.mmonteiro", "nome": "Jose Mario"},
    "junior.crafael": {"senha": "prova@2026", "role": "junior.crafael", "nome": "Junior Cesar Rafael"},
}

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_NAME = os.path.join(BASE_DIR, "database.db")

MODULOS = {
    'amparo': {
        'nome': 'Amparo Legal',
        'subtitulo': '⚡ Prova Fácil - Amparo Legal',
        'export_prefix': 'agendamento_amparo_legal'
    },
    'provas_2tri': {
        'nome': 'Provas 2° Trimestre',
        'subtitulo': '⚡ Prova Fácil - 2° Trimestre',
        'export_prefix': 'agendamento_provas_2tri'
    },
    'provas_online': {
        'nome': 'Provas Online',
        'subtitulo': '⚡ Prova Fácil - Provas Online',
        'export_prefix': 'agendamento_provas_online'
    }
}

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS base_provas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                polo TEXT,
                nome_polo TEXT,
                nome TEXT,
                data TEXT,
                hora TEXT,
                tipo TEXT,
                turno TEXT,
                codigo_modelo TEXT,
                nome_modelo TEXT,
                formato TEXT,
                codigo_academico TEXT,
                nome_academico TEXT,
                codigo_aluno TEXT,
                nome_aluno TEXT,
                codigo_local TEXT,
                nome_local TEXT,
                duracao TEXT,
                data_final_agendamento TEXT,
                hora_final_agendamento TEXT,
                tempo_para_iniciar_prova TEXT,
                monitoramento TEXT,
                navegador_seguro TEXT,
                bloquear_ips TEXT,
                modo_aplicacao TEXT,
                data_de_publicacao_de_nota TEXT,
                hora_de_publicacao_de_nota TEXT,
                tipo_liberacao_prova TEXT,
                disciplina_codigo TEXT
            )
        """)
        try:
            conn.execute("ALTER TABLE base_provas ADD COLUMN nome_polo TEXT")
        except sqlite3.OperationalError:
            pass

        conn.execute("CREATE INDEX IF NOT EXISTS idx_aluno ON base_provas(codigo_aluno)")

        conn.execute("""
            CREATE TABLE IF NOT EXISTS fila_agendamentos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                modulo TEXT DEFAULT 'amparo',
                item_json TEXT NOT NULL,
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        try:
            conn.execute("ALTER TABLE fila_agendamentos ADD COLUMN modulo TEXT DEFAULT 'amparo'")
        except sqlite3.OperationalError:
            pass

        conn.execute("""
            CREATE TABLE IF NOT EXISTS configuracoes_lote (
                chave TEXT PRIMARY KEY,
                valor TEXT
            )
        """)
        conn.commit()

init_db()

# --- DECORADORES DE PROTEÇÃO ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login_view'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('is_admin'):
            return jsonify({'error': 'Acesso exclusivo para administradores.'}), 403
        return f(*args, **kwargs)
    return decorated_function

# --- ROTAS DE AUTENTICAÇÃO ---
@app.route('/login', methods=['GET', 'POST'])
def login_view():
    if request.method == 'POST':
        usuario = request.form.get('username', '').strip()
        senha = request.form.get('password', '').strip()

        conta = USUARIOS.get(usuario)
        if conta and conta['senha'] == senha:
            session['logged_in'] = True
            session['usuario'] = usuario
            session['nome'] = conta['nome']
            session['is_admin'] = (conta['role'] == 'admin')
            return redirect(url_for('home'))
        return render_template('login.html', erro="Usuário ou senha inválidos.")
    
    if session.get('logged_in'):
        return redirect(url_for('home'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login_view'))

@app.route('/api/auth/status', methods=['GET'])
def auth_status():
    return jsonify({
        'logged_in': session.get('logged_in', False),
        'is_admin': session.get('is_admin', False),
        'usuario': session.get('usuario', ''),
        'nome': session.get('nome', '')
    })

# --- ROTAS DE NAVEGAÇÃO ---
@app.route('/')
@login_required
def home():
    return render_template('home.html', is_admin=session.get('is_admin', False), nome_usuario=session.get('nome', ''))

@app.route('/agendador/<modulo_id>')
@login_required
def agendador(modulo_id):
    if modulo_id not in MODULOS:
        return abort(404)
    info = MODULOS[modulo_id]
    return render_template('index.html', modulo_id=modulo_id, modulo_info=info, is_admin=session.get('is_admin', False))

# --- BASE DE PROVAS ---
@app.route('/api/status_base', methods=['GET'])
@login_required
def status_base():
    with get_db() as conn:
        total = conn.execute("SELECT COUNT(DISTINCT codigo_aluno) as total FROM base_provas").fetchone()['total']
    return jsonify({'carregada': total > 0, 'total_alunos': total})

@app.route('/api/upload_base', methods=['POST'])
@login_required
@admin_required
def upload_base():
    if 'file' not in request.files:
        return jsonify({'error': 'Nenhum arquivo enviado'}), 400

    file = request.files['file']
    if not file.filename.endswith('.csv'):
        return jsonify({'error': 'Arquivo precisa ser .csv'}), 400

    raw_bytes = file.stream.read()
    try:
        content = raw_bytes.decode('utf-8-sig')
    except UnicodeDecodeError:
        content = raw_bytes.decode('latin1')

    first_line = content.split('\n')[0]
    sep = ';' if first_line.count(';') > first_line.count(',') else ','

    reader = csv.DictReader(io.StringIO(content), delimiter=sep)
    headers = [h.strip() for h in reader.fieldnames or []]

    required = ['codigo_aluno', 'nome_academico', 'codigo_modelo', 'polo']
    for req in required:
        if req not in headers:
            return jsonify({'error': f'Coluna obrigatória ausente: {req}'}), 400

    rows_to_insert = []
    seen = set()
    dupes = 0

    for row in reader:
        c_aluno = (row.get('codigo_aluno') or '').strip()
        nome_acad = (row.get('nome_academico') or '').strip()
        c_modelo = (row.get('codigo_modelo') or '').strip()
        polo = (row.get('polo') or '').strip()
        nome_polo = (row.get('nome_polo') or '').strip()
        c_local = (row.get('codigo_local') or '').strip()

        key = (c_aluno, nome_acad, c_modelo, polo, c_local)
        if key in seen:
            dupes += 1
            continue
        seen.add(key)

        m = re.search(r'\(([^()]+)\)\s*$', nome_acad)
        disc_cod = m.group(1).strip() if m else ''

        rows_to_insert.append((
            polo, nome_polo, row.get('nome', '').strip(), row.get('data', '').strip(), row.get('hora', '').strip(),
            row.get('tipo', '').strip(), row.get('turno', '').strip(), c_modelo, row.get('nome_modelo', '').strip(),
            row.get('formato', '').strip(), row.get('codigo_academico', '').strip(), nome_acad, c_aluno,
            row.get('nome_aluno', '').strip(), c_local, row.get('nome_local', '').strip(), row.get('duracao', '').strip(),
            row.get('data_final_agendamento', '').strip(), row.get('hora_final_agendamento', '').strip(),
            row.get('tempo_para_iniciar_prova', '').strip(), row.get('monitoramento', '').strip(),
            row.get('navegador_seguro', '').strip(), row.get('bloquear_ips', '').strip(),
            row.get('modo_aplicacao', '').strip(), row.get('data_de_publicacao_de_nota', '').strip(),
            row.get('hora_de_publicacao_de_nota', '').strip(), row.get('tipo_liberacao_prova', '').strip(),
            disc_cod
        ))

    with get_db() as conn:
        conn.execute("DELETE FROM base_provas")
        conn.executemany("""
            INSERT INTO base_provas (
                polo, nome_polo, nome, data, hora, tipo, turno, codigo_modelo, nome_modelo,
                formato, codigo_academico, nome_academico, codigo_aluno, nome_aluno,
                codigo_local, nome_local, duracao, data_final_agendamento, hora_final_agendamento,
                tempo_para_iniciar_prova, monitoramento, navegador_seguro, bloquear_ips,
                modo_aplicacao, data_de_publicacao_de_nota, hora_de_publicacao_de_nota,
                tipo_liberacao_prova, disciplina_codigo
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, rows_to_insert)
        conn.commit()

    with get_db() as conn:
        total_alunos = conn.execute("SELECT COUNT(DISTINCT codigo_aluno) as total FROM base_provas").fetchone()['total']

    return jsonify({'success': True, 'alunos': total_alunos, 'dupes': dupes})

@app.route('/api/limpar_base', methods=['POST'])
@login_required
@admin_required
def limpar_base():
    with get_db() as conn:
        conn.execute("DELETE FROM base_provas")
        conn.commit()
    return jsonify({'success': True})

@app.route('/api/busca_aluno', methods=['GET'])
@login_required
def busca_aluno():
    aluno_id = request.args.get('aluno', '').strip()
    if not aluno_id:
        return jsonify({'status': 'vazio'})

    with get_db() as conn:
        rows = conn.execute("SELECT * FROM base_provas WHERE codigo_aluno = ?", (aluno_id,)).fetchall()

    if not rows:
        return jsonify({'status': 'sem_aluno'})

    dados = [dict(r) for r in rows]
    nome_aluno = dados[0]['nome_aluno']

    disciplinas = {}
    for d in dados:
        cod = d['disciplina_codigo']
        if cod not in disciplinas:
            limpo = re.sub(r'\s*\([^()]*\)\s*$', '', d['nome_academico'])
            disciplinas[cod] = {'codigo': cod, 'nome': limpo}

    return jsonify({
        'status': 'ok',
        'nome_aluno': nome_aluno,
        'disciplinas': list(disciplinas.values()),
        'registros': dados
    })

# --- FILA DE AGENDAMENTOS ---
@app.route('/api/fila', methods=['GET'])
@login_required
def get_fila():
    modulo = request.args.get('modulo', 'amparo')
    with get_db() as conn:
        rows = conn.execute("SELECT id, item_json FROM fila_agendamentos WHERE modulo = ? ORDER BY id ASC", (modulo,)).fetchall()
    items = []
    for r in rows:
        try:
            item = json.loads(r['item_json'])
            item['db_id'] = r['id']
            items.append(item)
        except Exception:
            continue
    return jsonify(items)

@app.route('/api/fila', methods=['POST'])
@login_required
def add_to_fila():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Dados inválidos'}), 400
    modulo = request.args.get('modulo', 'amparo')
    with get_db() as conn:
        cursor = conn.execute("INSERT INTO fila_agendamentos (modulo, item_json) VALUES (?, ?)", (modulo, json.dumps(data)))
        conn.commit()
        new_id = cursor.lastrowid
    data['db_id'] = new_id
    return jsonify({'success': True, 'item': data})

@app.route('/api/fila/<int:db_id>', methods=['PUT'])
@login_required
def update_fila_item(db_id):
    data = request.get_json()
    with get_db() as conn:
        conn.execute("UPDATE fila_agendamentos SET item_json = ? WHERE id = ?", (json.dumps(data), db_id))
        conn.commit()
    data['db_id'] = db_id
    return jsonify({'success': True, 'item': data})

@app.route('/api/fila/<int:db_id>', methods=['DELETE'])
@login_required
@admin_required
def delete_fila_item(db_id):
    with get_db() as conn:
        conn.execute("DELETE FROM fila_agendamentos WHERE id = ?", (db_id,))
        conn.commit()
    return jsonify({'success': True})

@app.route('/api/fila/limpar', methods=['POST'])
@login_required
@admin_required
def clear_fila():
    modulo = request.args.get('modulo', 'amparo')
    with get_db() as conn:
        conn.execute("DELETE FROM fila_agendamentos WHERE modulo = ?", (modulo,))
        conn.commit()
    return jsonify({'success': True})

# --- CONFIGURAÇÃO DE LOTE ---
@app.route('/api/lote', methods=['GET'])
@login_required
def get_lote():
    modulo = request.args.get('modulo', 'amparo')
    chave = f'params_{modulo}'
    with get_db() as conn:
        row = conn.execute("SELECT valor FROM configuracoes_lote WHERE chave = ?", (chave,)).fetchone()
    if row and row['valor']:
        try:
            return jsonify(json.loads(row['valor']))
        except Exception:
            return jsonify({})
    return jsonify({})

@app.route('/api/lote', methods=['POST'])
@login_required
@admin_required
def save_lote():
    modulo = request.args.get('modulo', 'amparo')
    chave = f'params_{modulo}'
    data = request.get_json() or {}
    with get_db() as conn:
        conn.execute("INSERT OR REPLACE INTO configuracoes_lote (chave, valor) VALUES (?, ?)", (chave, json.dumps(data)))
        conn.commit()
    return jsonify({'success': True})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)