from flask import Flask, render_template, request, flash, url_for, redirect, get_flashed_messages, session
from flask_mail import Mail, Message
from flask_session import Session
from services.config import conectar
from uuid import uuid4
from dotenv import load_dotenv
from fernet import Fernet
from datetime import datetime
from services import tasks
import hashlib
import os

load_dotenv('./.env')

chave_fernet = os.getenv('fernet_key')
cipher_suite = Fernet(chave_fernet.encode())

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('key')
app.config['MAIL_SERVER'] = os.getenv('server')
app.config['MAIL_PORT'] = os.getenv('port')
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv('mail')
app.config['MAIL_PASSWORD'] = os.getenv('code')
app.config['SESSION_TYPE'] = 'filesystem'
app.config['PERMANENT_SESSION_LIFETIME'] = 3 * 60 * 60 # 3 horas

mail = Mail(app)
Session(app)

@app.route("/")
def index():
    if 'user' in session:
        flash("AVISO: Você já está logado.")

        if session['tipo_conta'] == "ALUNO":
            return redirect(url_for('home_aluno'))
        elif session['tipo_conta'] == "PROF":
            return redirect(url_for('home_prof'))

    feedbacks = get_flashed_messages()
    return render_template("index.html", feedbacks=feedbacks)

@app.route("/home")
def home():
    if 'user' not in session:
        flash("ERRO: Realize o login primeiro.")
        return redirect(url_for('index'))
    else:
        if session['tipo_conta'] == "PROF":
            return redirect(url_for('home_prof'))
        else:
            return redirect(url_for('home_aluno'))

@app.route("/home/prof")
def home_prof():
    if 'user' not in session:
        flash("ERRO: Realize o login primeiro.")
        return redirect(url_for('index'))
    else:
        tipo = session['tipo_conta']
        if tipo != "PROF":
            flash("ERRO: Acesso negado.")
            return redirect(url_for('home_aluno'))

        db = conectar()
        cursor = db.cursor(prepared=True)

        turmas, qtde_membros = obter_lista_turma(session['userid'], session['tipo_conta'], db, cursor)
        convites = obter_convites(session['user'], db, cursor)

        feedbacks = get_flashed_messages()
        return render_template("home_prof.html", nome=session['username'], ConverterBytes=ConverterBytes, feedbacks=feedbacks, turmas=enumerate(turmas), qtde_membros=qtde_membros, convites=convites, cipher_suite=cipher_suite)

@app.get("/home/prof/turma/<int:turma_id>/boletim")
def editar_padrao_boletim(turma_id):
    if 'user' not in session:
        flash("ERRO: Realize o login primeiro.")
        return redirect(url_for('index'))
    else:
        if session['tipo_conta'] != "PROF":
            flash("ERRO: Acesso negado.")
            return redirect(url_for('home_aluno'))

    db = conectar()
    cursor = db.cursor(prepared=True)

    cursor.execute("SELECT * FROM turmas_membros WHERE turma_id = %s AND prof_id = %s", (turma_id, session['userid'],))
    membro = cursor.fetchone()

    if membro:
        return render_template("editar_boletim.html", turma_id=turma_id)
    else:
        flash("ERRO: Boletim inacessível.")
        return redirect(f'/home/prof/turma/{turma_id}')

@app.post("/editar-boletim")
def editar_boletim():
    materias = request.form.getlist('materia[]')
    periodo = request.form.get('periodo')
    media = request.form.get('media')
    id = request.form.get('turma_id')

    if periodo == 'bimestre':
        quantidade_notas = 4
    elif periodo == 'trimestre':
        quantidade_notas = 3
    elif periodo == 'semestre':
        quantidade_notas = 2
    else:
        flash("ERRO: Tipo de período inválido!")
        return redirect(f'/home/prof/turma/{id}')

    db = conectar()
    cursor = db.cursor(prepared=True)

    cursor.execute("SELECT id, turma_id FROM periodos WHERE turma_id = %s", (id,))
    duplicate = cursor.fetchone()

    if duplicate:
        cursor.execute("SELECT id FROM materias WHERE periodo_id = %s", (duplicate[0],))
        materias_ids = cursor.fetchall()
        for materia_id in materias_ids:
            cursor.execute("DELETE FROM notas WHERE materia_id = %s", (materia_id[0],))
        cursor.execute("DELETE FROM materias WHERE periodo_id = %s", (duplicate[0],))
        cursor.execute("DELETE FROM periodos WHERE id = %s", (duplicate[0],))
        db.commit()
        cursor.execute("INSERT INTO periodos(turma_id, media_aprovacao, tipo) VALUES (%s, %s, %s)", (id, media, periodo,))
        periodo_id = cursor.lastrowid

        try:
            for materia in materias:
                cursor.execute("INSERT INTO materias (periodo_id, nome) VALUES (%s, %s)", (periodo_id, materia[0],))
        except Exception as e:
            flash(f"ERRO: Erro ao inserir no banco: {e}")
            cursor.close()
            db.close()
            return redirect(f'/home/prof/turma/{id}')

        cursor.execute("SELECT aluno_id FROM turmas_membros WHERE turma_id = %s AND aluno_id IS NOT NULL", (id,))
        alunos = cursor.fetchall()

        if alunos:
            for aluno in alunos:
                aluno_id = aluno[0]
                for materia in materias:
                    cursor.execute("SELECT id FROM materias WHERE nome = %s AND periodo_id = %s", (materia, periodo_id,))
                    materia_id = cursor.fetchone()[0]
                    for i in range(quantidade_notas):
                        cursor.execute("INSERT INTO notas (aluno_id, materia_id, valor, num_periodo) VALUES (%s, %s, 0, %s)", (aluno_id, materia_id, i,))
            flash("AVISO: Todas as notas foram redefinidas.")
        else:
            flash("ERRO: Nenhum aluno foi encontrado, não foi possível configurar o boletim.")
            cursor.close()
            db.close()
            return redirect(f'/home/prof/turma/{id}')

        db.commit()
        cursor.close()
        db.close()

        flash("SUCESSO: Boletim reconfigurado com sucesso!")
        return redirect(f'/home/prof/turma/{id}')

    else:
        cursor.execute("INSERT INTO periodos(turma_id, media_aprovacao, tipo) VALUES (%s, %s, %s)", (id, media, periodo,))
        periodo_id = cursor.lastrowid

        try:
            for materia in materias:
                cursor.execute("INSERT INTO materias (periodo_id, nome) VALUES(%s, %s)", (periodo_id, materia,))
        except Exception as e:
            flash(f"ERRO: Erro ao inserir no banco: {e}")
            cursor.close()
            db.close()
            return redirect(f'/home/prof/turma/{id}')

        cursor.execute("SELECT aluno_id FROM turmas_membros WHERE turma_id = %s AND aluno_id IS NOT NULL", (id,))
        alunos = cursor.fetchall()

        if alunos:
            for aluno in alunos:
                aluno_id = aluno[0]
                for materia in materias:
                    cursor.execute("SELECT id FROM materias WHERE nome = %s AND periodo_id = %s", (materia, periodo_id,))
                    materia_id = cursor.fetchone()[0]
                    for i in range(quantidade_notas):
                        cursor.execute("INSERT INTO notas (aluno_id, materia_id, valor, num_periodo) VALUES (%s, %s, 0, %s)", (aluno_id, materia_id, i,))
        else:
            flash("ERRO: Nenhum aluno foi encontrado, não foi possível configurar o boletim.")
            cursor.close()
            db.close()
            return redirect(f'/home/prof/turma/{id}')

        db.commit()
        cursor.close()
        db.close()

        flash("SUCESSO: Boletim configurado com sucesso!")
        return redirect(f'/home/prof/turma/{id}')

@app.route("/home/prof/turma/<int:turma_id>/boletim/inserir/<int:aluno_id>")
def inserir_nota_form(turma_id, aluno_id):
    if 'user' not in session:
        flash("ERRO: Realize o login primeiro.")
        return redirect(url_for('index'))
    else:
        if session['tipo_conta'] != "PROF":
            flash("ERRO: Acesso negado.")
            return redirect(url_for('home_aluno'))

    db = conectar()
    cursor = db.cursor(prepared=True)

    boletim, tipo_periodo, turma, aluno = obter_dados_boletim(turma_id, aluno_id, db, cursor)

    feedbacks = get_flashed_messages()
    cursor.close()
    db.close()
    return render_template("inserir_boletim.html", feedbacks=feedbacks, aluno_id=aluno_id, ConverterBytes=ConverterBytes, cipher_suite=cipher_suite, boletim=boletim, tipo_periodo=tipo_periodo, turma_id=turma_id, nome_aluno=aluno, nome_turma=turma)

@app.post("/inserir-nota")
def inserir_nota():
    if 'user' not in session:
        flash("ERRO: Realize o login primeiro.")
        return redirect(url_for('index'))
    else:
        if session['tipo_conta'] != "PROF":
            flash("ERRO: Acesso negado.")
            return redirect(url_for('home_aluno'))

    turma_id = request.form.get('turma_id')
    aluno_id = request.form.get('aluno_id')

    db = conectar()
    cursor = db.cursor(prepared=True)

    for key, value in request.form.items():
        if key.startswith('nota_materia_'):
            parts = key.split('_')
            materia_id = int(parts[2])
            periodo = int(parts[3])
            valor = float(value)

            cursor.execute("""
                UPDATE notas SET valor = %s
                WHERE materia_id = %s
                AND aluno_id = %s
                AND num_periodo = %s
            """, (valor, materia_id, aluno_id, periodo))

            # Log para verificar se a consulta está sendo executada
            print(f"Consulta executada: {cursor.statement}")

    db.commit()
    cursor.close()
    db.close()
    flash("SUCESSO: Notas inseridas com sucesso!")
    return redirect(f"/home/prof/turma/{turma_id}/boletim/inserir/{aluno_id}")

@app.get("/remover/<int:turma_id>/<int:id>")
def remover_aluno(turma_id, id):
    if 'user' not in session:
        flash("ERRO: Realize o login primeiro.")
        return redirect(url_for('index'))
    else:
        if session['tipo_conta'] != "PROF":
            flash("ERRO: Acesso negado.")
            return redirect(url_for('home_aluno'))

    db = conectar()
    cursor = db.cursor(prepared=True)

    cursor.execute("DELETE FROM turmas_membros WHERE turma_id = %s AND aluno_id = %s", (turma_id, id))
    db.commit()
    cursor.close()
    db.close()

    flash("SUCESSO: Aluno removido da turma.")
    return redirect(f'/home/prof/turma/{turma_id}')

@app.get("/sair/<int:turma_id>")
def sair_turma(turma_id):
    if 'user' not in session:
        flash("ERRO: Realize o login primeiro.")
        return redirect(url_for('index'))
    else:
        if session['tipo_conta'] != "PROF":
            flash("ERRO: Acesso negado.")
            return redirect(url_for('home_aluno'))

    db = conectar()
    cursor = db.cursor(prepared=True)

    cursor.execute("SELECT prof_id FROM turmas WHERE prof_id = %s AND id = %s", (session['userid'], turma_id,))
    criador = cursor.fetchone()

    if criador:
        flash("ERRO: O criador não pode sair da turma! Para sair dela, deverá apagar a turma.")
        return redirect(f'/home/prof/turma/{turma_id}')
    else:
        cursor.execute("DELETE FROM turmas_membros WHERE prof_id = %s", (session['userid'],))
        db.commit()
        cursor.close()
        db.close()
        flash("SUCESSO: Você saiu da turma.")

        return redirect(url_for('home_prof'))

@app.get("/apagar-turma/<int:id>")
def apagar_turma(id):
    if 'user' not in session:
        flash("ERRO: Realize o login primeiro.")
        return redirect(url_for('index'))
    else:
        if session['tipo_conta'] != "PROF":
            flash("ERRO: Acesso negado.")
            return redirect(url_for('home_aluno'))

    db = conectar()
    cursor = db.cursor(prepared=True)

    cursor.execute("SELECT prof_id FROM turmas WHERE prof_id = %s AND id = %s", (session['userid'], id,))
    criador = cursor.fetchone()

    if criador:
        cursor.execute("DELETE FROM turmas WHERE id = %s", (id,))
        cursor.execute("DELETE FROM turmas_membros WHERE turma_id = %s", (id,))
        cursor.execute("DELETE FROM turmas_convites WHERE turma_id = %s", (id,))
        cursor.execute("SELECT id FROM periodos WHERE turma_id = %s", (id,))
        periodo_id = cursor.fetchone()
        if periodo_id:
            cursor.execute("SELECT id FROM materias WHERE periodo_id = %s", (periodo_id[0],))
            materias_ids = cursor.fetchall()
            for materia_id in materias_ids:
                cursor.execute("DELETE FROM notas WHERE materia_id = %s", (materia_id[0],))
            cursor.execute("DELETE FROM materias WHERE periodo_id = %s", (periodo_id[0],))
            cursor.execute("DELETE FROM periodos WHERE turma_id = %s", (id,))
        db.commit()
        cursor.close()
        db.close()
        flash("SUCESSO: Turma deletada com sucesso.")
        return redirect(url_for('home_prof'))

    else:
        flash("ERRO: Sem permissão.")
        return redirect(url_for('home_prof')) if session['tipo_conta'] == "PROF" else redirect(url_for('home_aluno'))

@app.route("/home/aluno", methods=['GET', 'POST'])
def home_aluno():
    if 'user' not in session:
        flash("ERRO: Realize o login primeiro.")
        return redirect(url_for('index'))
    else:
        tipo = session['tipo_conta']
        if tipo != "ALUNO":
            flash("ERRO: Acesso negado.")
            return redirect(url_for('home_prof'))

        db = conectar()
        cursor = db.cursor(prepared=True)

        if request.method == 'GET':
            boletim=None
            tipo_periodo=None
            turma=None
            aluno=None

            turmas = obter_lista_turma(session['userid'], session['tipo_conta'], db, cursor)
            convites = obter_convites(session['user'], db, cursor)
        else:
            turma_id = request.form.get('turma_option')
            if turma_id == 0:
                raise ValueError("O id da turma não pode ser zero.")
            else:
                boletim, tipo_periodo, turma, aluno = obter_dados_boletim(turma_id, session['userid'], db, cursor)
            turmas = obter_lista_turma(session['userid'], session['tipo_conta'], db, cursor)
            convites = obter_convites(session['user'], db, cursor)

        feedbacks = get_flashed_messages()
        cursor.close()
        db.close()
        return render_template("home_aluno.html", ConverterBytes=ConverterBytes, nome=session['username'], feedbacks=feedbacks, convites=convites, cipher_suite=cipher_suite, boletim=boletim, tipo_periodo=tipo_periodo, nome_turma=turma, nome_aluno=aluno, turmas=turmas)

@app.route("/conta")
def conta():
    if 'user' not in session:
        flash("ERRO: Realize o login primeiro.")
        return redirect(url_for('index'))

    db = conectar()
    cursor = db.cursor(prepared=True)

    cursor.execute("SELECT nome FROM usuarios WHERE id = %s", (session['userid'],))
    nome_db = cursor.fetchone()
    nome = cipher_suite.decrypt(bytes(nome_db[0])).decode()

    session['username'] = nome

    cursor.close()
    db.close()
    feedbacks = get_flashed_messages()
    return render_template("conta.html", nome=session['username'], feedbacks=feedbacks)

@app.get("/apagar/<int:id>")
def apagar_conta(id):
    if 'user' not in session:
        flash("ERRO: Realize o login primeiro.")
        return redirect(url_for('index'))
    else:
        if session['userid'] == id:
            db = conectar()
            cursor = db.cursor(prepared=True)

            cursor.execute("DELETE FROM usuarios WHERE id = %s", (id,))
            cursor.execute("DELETE FROM email_map WHERE email = %s", (session['user'],))
            if session['tipo_conta'] == "PROF":
                cursor.execute("DELETE FROM turmas WHERE prof_id = %s", (session['userid'],))
                cursor.execute("DELETE FROM turmas_membros WHERE prof_id = %s", (session['userid'],))
            elif session['tipo_conta'] == "ALUNO":
                cursor.execute("DELETE FROM turmas_membros WHERE aluno_id = %s", (session['userid'],))
            db.commit()
            cursor.close()
            db.close()
            return redirect(url_for('logout'))
        else:
            flash("ERRO: Requisição inválida.")
            return redirect(url_for('index'))

@app.post("/alterar/nome/<int:id>")
def alterar_nome(id):
    db = conectar()
    cursor = db.cursor(prepared=True)

    nome = request.form.get('nome').strip()
    nome_cript = cipher_suite.encrypt(nome.encode())

    try:
        cursor.execute("UPDATE usuarios SET nome = %s WHERE id = %s", (nome_cript, id,))
    except Exception as e:
        flash(f"ERRO: Ocorreu um erro ao alterar o nome: {e}")
        cursor.close()
        db.close()
        return redirect(url_for('conta'))

    db.commit()
    cursor.close()
    db.close()
    flash("SUCESSO: Nome alterado com sucesso!")
    return redirect(url_for('conta'))

@app.route("/cadastro")
def cadastro():
    if 'user' in session:
        flash("AVISO: Você já está logado")

        if session['tipo_conta'] == "ALUNO":
            return redirect(url_for('home_aluno'))
        elif session['tipo_conta'] == "PROF":
            return redirect(url_for('home_prof'))

    return render_template("cadastro.html")

@app.route("/logout")
def logout():
    session.pop('user', None)
    return redirect(url_for('index'))

@app.post("/login")
def login():
    if 'user' in session:
        flash("AVISO: Você já está logado.")

        if session['tipo_conta'] == "ALUNO":
            return redirect(url_for('home_aluno'))
        elif session['tipo_conta'] == "PROF":
            return redirect(url_for('home_prof'))

    email = request.form.get('email').replace(" ", "")
    senha = request.form.get('senha')

    db = conectar()
    cursor = db.cursor(prepared=True)

    retorno = verificar_login(email, senha, db, cursor)

    cursor.close()
    db.close()

    if retorno == 2:
        flash('ERRO: A conta precisa ser autenticada antes de realizar o login.')
        return redirect(url_for('index'))
    elif retorno == False:
        flash('ERRO: Email e/ou senha incorretos.')
        return redirect(url_for('index'))
    else:
        db2 = conectar()
        cursor2 = db2.cursor(prepared=True)
        atualizar_ultimo_login(email, db2, cursor2)
        session['user'] = email
        session['userid'] = retorno[1]
        session['username'] = cipher_suite.decrypt(bytes(retorno[2])).decode()
        session['tipo_conta'] = retorno[3]

        cursor2.close()
        db2.close()
        if session['tipo_conta'] == "ALUNO":
            return redirect(url_for('home_aluno'))
        elif session['tipo_conta'] == "PROF":
            return redirect(url_for('home_prof'))

@app.route("/nova-senha")
def nova_senha():
    return render_template("nova_senha.html")

@app.post("/nova-senha/email")
def nova_senha_email():
    email = request.form.get('email').replace(" ", "")
    db = conectar()
    cursor = db.cursor(prepared=True)
    email_hash = hashlib.sha256(email.encode('utf-8')).hexdigest()

    cursor.execute("SELECT email_hash FROM usuarios WHERE email_hash = %s", (email_hash,))
    resultado = cursor.fetchone()

    if resultado:
        dia_solic = datetime.now().date()
        token = uuid4().hex
        if enviar_email(db, cursor, "alterar senha", email, token, turma_id=None, prof_id=None):
            cursor.execute("INSERT INTO alt_senha(token, email_hash, dia_solic) VALUES(%s, %s, %s) ON DUPLICATE KEY UPDATE token = %s, dia_solic = %s", (token, email_hash, dia_solic, token, dia_solic,))
            flash("SUCESSO: Link enviado ao email fornecido.")
        else:
            flash("ERRO: Não foi possível enviar o email.")
    else:
        flash("ERRO: O email informado não existe.")

    db.commit()
    cursor.close()
    db.close()
    return redirect(url_for('index'))

@app.get("/nova-senha/ok/<email>/<token>")
def form_nova_senha(email, token):
    db = conectar()
    cursor = db.cursor(prepared=True)

    cursor.execute("SELECT token FROM alt_senha WHERE email_hash = %s", (email,))
    resultado = cursor.fetchone()

    if resultado:
        token_alt = resultado[0]
        cursor.execute("SELECT token FROM usuarios WHERE email_hash = %s", (email,))
        resultado = cursor.fetchone()

        if resultado and token_alt == token:
            token_usuario = resultado[0]

            cursor.execute("SELECT email FROM email_map WHERE token = %s", (token_usuario,))
            db_email = cursor.fetchone()

            cursor.close()
            db.close()
            return render_template("nova_senha_ok.html", email=db_email)
        else:
            flash("ERRO: Dados inválidos ou inexistentes. (2)")
            cursor.close()
            db.close()
            return redirect(url_for('index'))
    else:
        flash("ERRO: Dados inválidos ou inexistentes. (1)")
        cursor.close()
        db.close()
        return redirect(url_for('index'))

@app.post("/alterar/senha")
def alterar_senha():
    db = conectar()
    cursor = db.cursor(prepared=True)
    email = request.form.get('email')
    senha = request.form.get('senha')

    email_hash = hashlib.sha256(email.encode('utf-8')).hexdigest()
    senha_cript = cipher_suite.encrypt(senha.encode())

    try:
        cursor.execute("UPDATE usuarios SET senha_cript = %s WHERE email_hash = %s", (senha_cript, email_hash,))
        cursor.execute("DELETE FROM alt_senha WHERE email_hash = %s", (email_hash,))
    except:
        flash("ERRO: Ocorreu um erro na alteração da senha.")
        cursor.close()
        db.close()
        return redirect(url_for('index'))

    db.commit()
    cursor.close()
    db.close()

    flash('SUCESSO: Senha alterada com sucesso!')
    return redirect(url_for('index'))

@app.route("/sobre")
def sobre():
    return render_template("sobre.html")

@app.post("/cadastro/<tipo_conta>")
def cadastrar(tipo_conta):
    email = request.form.get('email').replace(" ", "")
    nome = request.form.get('nome').strip()
    senha = request.form.get('senha')

    nome_cript = cipher_suite.encrypt(nome.encode())

    senha_cript = cipher_suite.encrypt(senha.encode())

    db = conectar()
    cursor = db.cursor(prepared=True)

    try:
        if tipo_conta.upper() == "ALUNO":
            if criar_usuario(email, nome_cript, senha_cript, 'ALUNO', db, cursor):
                flash("ERRO: Já existe uma conta com esse email.")
                cursor.close()
                db.close()
                return redirect(url_for('index'))

        elif tipo_conta.upper() == "PROF":
            if criar_usuario(email, nome_cript, senha_cript, 'PROF', db, cursor):
                flash("ERRO: Já existe uma conta com esse email.")
                cursor.close()
                db.close()
                return redirect(url_for('index'))

    except Exception as e:
        flash(f"ERRO: Ocorreu um erro ao criar o usuário: {e}")
        cursor.close()
        db.close()
        return redirect(url_for('index'))

    cursor.close()
    db.close()
    return redirect(url_for('email_auth'))

@app.route("/home/prof/criar-turma/form")
def criar_turma_form():
    if 'user' not in session:
        flash("ERRO: Realize o login primeiro.")
        return redirect(url_for('index'))
    else:
        if session['tipo_conta'] != "PROF":
            flash("ERRO: Acesso negado.")
            return redirect(url_for('home_aluno'))

        feedbacks = get_flashed_messages()
        return render_template("criar_turma.html", nome=session['username'], feedbacks=feedbacks)

@app.post("/criar-turma")
def criar_turma():
    turma = request.form.get('turma').strip()
    limite = request.form.get('limite')

    db = conectar()
    cursor = db.cursor(prepared=True)

    turma_cript = cipher_suite.encrypt(turma.encode())

    try:
        if limite:
            num_limite = request.form.get('num_limite')
            cursor.execute("INSERT INTO turmas(nome, limite, limite_valor, prof_id) VALUES(%s, 'S', %s, %s)", (turma_cript, num_limite, session['userid'],))
            turma_id = cursor.lastrowid
            cursor.execute("INSERT INTO turmas_membros(turma_id, prof_id) VALUES(%s, %s)", (turma_id, session['userid'],))
            db.commit()

        else:
            cursor.execute("INSERT INTO turmas(nome, prof_id) VALUES(%s, %s)", (turma_cript, session['userid'],))
            turma_id = cursor.lastrowid
            cursor.execute("INSERT INTO turmas_membros(turma_id, prof_id) VALUES(%s, %s)", (turma_id, session['userid'],))
            db.commit()
    except:
        flash("ERRO: Não foi possível criar a turma.")
        cursor.close()
        db.close()
        return redirect(url_for('criar_turma_form'))

    cursor.close()
    db.close()
    flash("SUCESSO: Turma criada com sucesso!")
    return redirect(url_for('home_prof'))

@app.get("/home/prof/turma/<int:id>")
def prof_turma(id):
    if 'user' not in session:
        flash("ERRO: Realize o login primeiro.")
        return redirect(url_for('index'))
    else:
        if session['tipo_conta'] != "PROF":
            flash("ERRO: Acesso negado.")
            return redirect(url_for('home_aluno'))

        db = conectar()
        cursor = db.cursor(prepared=True)

        cursor.execute("SELECT prof_id FROM turmas_membros WHERE prof_id = %s AND turma_id = %s", (session['userid'], id,))
        membro = cursor.fetchone()

        if membro:
            dados_turma, tem_alunos = obter_dados_turma(db, cursor, id)
            feedbacks = get_flashed_messages()
            cursor.close()
            db.close()
            return render_template("turma.html", dados_turma=dados_turma, ConverterBytes=ConverterBytes, tem_alunos=tem_alunos, feedbacks=feedbacks, turma_id=id, cipher_suite=cipher_suite)
        else:
            flash("ERRO: Acesso negado.")
            cursor.close()
            db.close()
            return redirect(url_for('home_prof'))

@app.post("/convidar/<int:turma_id>/<int:prof_id>")
def turma_convidar(turma_id, prof_id):
    if 'user' not in session:
        flash("ERRO: Realize o login primeiro.")
        return redirect(url_for('index'))

    email = request.form.get('email').replace(" ", "")

    if email == session['user']:
        flash("ERRO: Não é possível convidar a si mesmo.")
        return redirect(f'/home/prof/turma/{turma_id}')

    email_hash = hashlib.sha256(email.encode('utf-8')).hexdigest()
    hoje = datetime.now().date()

    db = conectar()
    cursor = db.cursor(prepared=True)
    
    cursor.execute("SELECT limite_valor FROM turmas WHERE id = %s", (turma_id,))
    limite_membros = cursor.fetchone()
    
    if limite_membros:
        cursor.execute("SELECT COUNT(*) FROM turmas_membros WHERE turma_id = %s", (turma_id,))
        qtde_membros = cursor.fetchone()
        
        if qtde_membros[0] == limite_membros[0]:
            flash("ERRO: A turma está cheia.")
            cursor.close()
            db.close()
            return redirect(f'/home/prof/turma/{turma_id}')

    cursor.execute("SELECT id, email_hash FROM usuarios WHERE email_hash = %s", (email_hash,))
    exists = cursor.fetchone()

    if exists:
        cursor.execute("SELECT email_hash FROM turmas_convites WHERE email_hash = %s", (email_hash,))
        convidado = cursor.fetchone()

        if convidado:
            flash("ERRO: Convite não enviado pois o usuário já foi convidado.")
            cursor.close()
            db.close()
            return redirect(f'/home/prof/turma/{turma_id}')

        cursor.execute("SELECT * FROM turmas_membros WHERE turma_id = %s AND prof_id = %s OR aluno_id = %s", (turma_id, exists[0], exists[0],))
        membro = cursor.fetchone()

        if membro:
            flash("ERRO: O usuário informado já está na turma.")
            cursor.close()
            db.close()
            return redirect(f'/home/prof/turma/{turma_id}')

        cursor.execute("INSERT INTO turmas_convites(email_hash, prof_id, turma_id, criado_em) VALUES(%s, %s, %s, %s)", (email_hash, prof_id, turma_id, hoje,))
        db.commit()

        if enviar_email(db, cursor, "convite", email, token=None, turma_id=turma_id, prof_id=prof_id):
            flash("SUCESSO: Convite enviado com sucesso!")

        else:
            flash("ERRO: Não foi possivel enviar o email de convite.")

        cursor.close()
        db.close()
        return redirect(f'/home/prof/turma/{turma_id}')
    else:
        cursor.close()
        db.close()
        flash("ERRO: O email informado não existe.")
        return redirect(f'/home/prof/turma/{turma_id}')

@app.get("/convite/aceitar/<int:id>")
def aceitar_convite(id):
    if 'user' not in session:
        flash("ERRO: Realize o login primeiro.")
        return redirect(url_for('index'))

    db = conectar()
    cursor = db.cursor(prepared=True)

    email_hash = hashlib.sha256(session['user'].encode('utf-8')).hexdigest()

    cursor.execute("SELECT turma_id, email_hash FROM turmas_convites WHERE id = %s AND email_hash = %s", (id, email_hash))
    resultado = cursor.fetchone()

    if resultado:
        turma_id = resultado[0]
        
        cursor.execute("SELECT COUNT(*) FROM turmas_membros WHERE turma_id = %s", (turma_id,))
        qtde_membros = cursor.fetchone()
        
        cursor.execute("SELECT limite_valor FROM turmas WHERE id = %s", (turma_id,))
        limite_membros = cursor.fetchone()
            
        if limite_membros and qtde_membros[0] == limite_membros[0]:
            flash("ERRO: A turma está cheia.")
            cursor.close()
            db.close()
            return redirect(url_for('home'))
        
        else:
            if session['tipo_conta'] == "PROF":
                cursor.execute("INSERT INTO turmas_membros(turma_id, prof_id) VALUES(%s, %s)", (turma_id, session['userid'],))
                cursor.execute("DELETE FROM turmas_convites WHERE id = %s", (id,))
                db.commit()
                cursor.close()
                db.close()
                flash("SUCESSO: Convite aceito com sucesso!")
                return redirect(url_for('home_prof'))

            elif session['tipo_conta'] == "ALUNO":
                cursor.execute("INSERT INTO turmas_membros(turma_id, aluno_id) VALUES(%s, %s)", (turma_id, session['userid'],))
                cursor.execute("DELETE FROM turmas_convites WHERE id = %s", (id,))
                db.commit()
                cursor.close()
                db.close()
                flash("SUCESSO: Convite aceito com sucesso!")
                return redirect(url_for('home_aluno'))
    else:
        cursor.close()
        db.close()
        flash("ERRO: Convite inexistente.")
        if session['tipo_conta'] == "PROF":
            return redirect(url_for('home_prof'))
        elif session['tipo_conta'] == "ALUNO":
            return redirect(url_for('home_aluno'))

@app.get("/convite/recusar/<int:id>")
def recusar_convite(id):
    if 'user' not in session:
        flash("ERRO: Realize o login primeiro.")
        return redirect(url_for('index'))

    db = conectar()
    cursor = db.cursor(prepared=True)

    email_hash = hashlib.sha256(session['user'].encode('utf-8')).hexdigest()

    cursor.execute("SELECT turma_id, email_hash FROM turmas_convites WHERE id = %s AND email_hash = %s", (id, email_hash))
    resultado = cursor.fetchone()

    if resultado:
        cursor.execute("DELETE FROM turmas_convites WHERE id = %s", (id,))
        db.commit()
        cursor.close()
        db.close()
        flash("SUCESSO: Convite recusado.")
        if session['tipo_conta'] == "PROF":
            return redirect(url_for('home_prof'))
        elif session['tipo_conta'] == "ALUNO":
            return redirect(url_for('home_aluno'))
    else:
        cursor.close()
        db.close()
        flash("ERRO: Convite inexistente.")
        if session['tipo_conta'] == "PROF":
            return redirect(url_for('home_prof'))
        elif session['tipo_conta'] == "ALUNO":
            return redirect(url_for('home_aluno'))

@app.route("/email/auth")
def email_auth():
    return render_template("auth.html")

@app.get("/auth/<email>/<token>")
def auth(email, token):
    db = conectar()
    cursor = db.cursor()

    cursor.execute("SELECT token FROM usuarios WHERE (email_hash = %s AND auth = 0)", (email,))
    db_token = cursor.fetchone()

    if db_token and token == db_token[0]:
        cursor.execute("UPDATE usuarios SET auth = 1 WHERE email_hash = %s", (email,))
        db.commit()
        cursor.close()
        db.close()

        flash('SUCESSO: Conta autenticada com sucesso! Você pode fazer o login.')
        return redirect(url_for('index'))
    else:
        flash('ERRO: Token inválido ou a conta já foi autenticada.')
        cursor.close()
        db.close()
        return redirect(url_for('index'))

# NOTE: Funções para usar
def criar_usuario(email, nome, senha, tipo_conta, db, cursor):
    cursor.execute("SELECT email FROM email_map WHERE email = %s", (email,))
    duplicate = cursor.fetchone()

    if duplicate:
        return True
    else:
        hash_obj_e = hashlib.sha256(email.encode('utf-8'))
        email_hash = hash_obj_e.hexdigest()
        token = uuid4().hex
        hoje = datetime.today().date()

        sql = "INSERT INTO usuarios(nome, email_hash, token, senha_cript, tipo_conta, dia_criacao) VALUES(%s, %s, %s, %s, %s, %s);"
        val = (nome, email_hash, token, senha, tipo_conta, hoje,)
        cursor.execute(sql, val)

        sql = "INSERT INTO email_map (email, token) values (%s, %s)"
        val = (email, token,)
        cursor.execute(sql, val)

        assunto = "Validação de Conta"
        sender = "noreply@app.com"
        corpo = "Clique no link abaixo para validar seu email:"
        msg = Message(assunto, sender=sender, recipients=[email])
        msg.body = ""
        data = {
            'app_name': "GradeSphere Mail",
            'title': assunto,
            'body': corpo
        }

        msg.html = render_template("email_auth.html", data=data, email=email_hash, token=token)

        mail.send(msg)

        db.commit()
        return False

def cript_senha(senha):
    cripted_senha = cipher_suite.encrypt(senha.encode())

    return cripted_senha

def verificar_login(email, senha, db, cursor):
    hash_obj_e = hashlib.sha256(email.encode('utf-8'))
    email_hash = hash_obj_e.hexdigest()

    cursor.execute("SELECT id, nome, tipo_conta, senha_cript, auth FROM usuarios WHERE email_hash = %s", (email_hash,))
    resultado = cursor.fetchone()

    if resultado:
        id, nome, tipo, result_senha, auth = resultado

        if auth == 0:
            return 2
        elif senha == cipher_suite.decrypt(bytes(result_senha)).decode():
            return True, id, nome, tipo
        else:
            return False
    else:
        return False

def atualizar_ultimo_login(email, db, cursor):
    email_hash = hashlib.sha256(email.encode('utf-8')).hexdigest()
    hoje = datetime.now().date()

    cursor.execute("UPDATE usuarios SET ultimo_login = %s WHERE email_hash = %s", (hoje, email_hash,))
    db.commit()

def obter_lista_turma(id, tipo_conta, db, cursor):
    lista = []

    if tipo_conta == "PROF":
        cursor.execute("""
            SELECT turmas.id, turmas.nome FROM turmas
            INNER JOIN turmas_membros tm ON turmas.id = tm.turma_id
            WHERE tm.prof_id = %s
        """, (id,))

        resultados = cursor.fetchall()

        for turma_id, _ in resultados:
            cursor.execute("SELECT COUNT(turma_id) AS qtde_membros FROM turmas_membros WHERE turma_id = %s", (turma_id,))
            qtde_membros = cursor.fetchone()

            lista.append(qtde_membros[0])

        return resultados, lista

    elif tipo_conta == "ALUNO":
        cursor.execute("""
            SELECT turmas.id, turmas.nome FROM turmas
            INNER JOIN turmas_membros tm ON turmas.id = tm.turma_id
            WHERE tm.aluno_id = %s
        """, (id,))

        resultados = cursor.fetchall()

        return resultados
    else:
        return None

def obter_dados_turma(db, cursor, id):
    cursor.execute("SELECT COUNT(aluno_id) FROM turmas_membros WHERE turma_id = %s", (id,))
    tem_alunos = cursor.fetchone()[0] > 0

    if tem_alunos:
        cursor.execute("""
            SELECT
                t.nome AS nome_turma,
                a.nome AS nome_aluno,
                COUNT(tm.aluno_id) AS qtde_alunos,
                a.id AS id_aluno
            FROM turmas t
            INNER JOIN turmas_membros tm ON t.id = tm.turma_id
            INNER JOIN usuarios a ON tm.aluno_id = a.id
            WHERE t.id = %s
            GROUP BY t.id, a.nome;
        """, (id,))

        resultados = cursor.fetchall()
    else:
        cursor.execute("SELECT nome FROM turmas WHERE id = %s", (id,))
        resultados = cursor.fetchall()
    return resultados, tem_alunos

def obter_convites(email, db, cursor):
    email_hash = hashlib.sha256(email.encode('utf-8')).hexdigest()

    cursor.execute("""
        SELECT
            tc.id AS convite_id,
            t.nome AS nome_turma,
            p.nome AS nome_prof,
            tc.criado_em AS dia_convite
        FROM turmas_convites tc
        INNER JOIN turmas t ON tc.turma_id = t.id
        INNER JOIN usuarios p ON tc.prof_id = p.id
        WHERE tc.email_hash = %s
        ORDER BY tc.criado_em DESC
    """, (email_hash,))

    resultados = cursor.fetchall()
    return resultados

def obter_dados_boletim(turma_id, aluno_id, db, cursor):
    # Consultar o tipo de período para determinar a quantidade de notas
    cursor.execute("""
            SELECT tipo FROM periodos
            WHERE turma_id = %s
    """, (turma_id,))
    tipo_periodo = cursor.fetchone() # 'semestre', 'trimestre', 'bimestre'

    cursor.execute("SELECT t.nome AS turma, a.nome AS aluno FROM turmas t, usuarios a WHERE t.id = %s AND a.id = %s", (turma_id, aluno_id,))
    turma, aluno = cursor.fetchone()

    if tipo_periodo[0]:
        # Definir a quantidade de notas com base no tipo de período
        if tipo_periodo[0] == 'semestre':
            quantidade_notas = 2
        elif tipo_periodo[0] == 'trimestre':
            quantidade_notas = 3
        elif tipo_periodo[0] == 'bimestre':
            quantidade_notas = 4
        else:
            quantidade_notas = 0

        # Consultar as notas do aluno
        cursor.execute("""
                SELECT
                    n.id AS nota_id,
                    n.valor AS nota,
                    n.num_periodo AS num_periodo,
                    n.materia_id AS materia_id
                FROM
                    notas n
                WHERE
                    n.aluno_id = %s
                ORDER BY n.num_periodo DESC
        """, (aluno_id,))

        notas = cursor.fetchall()

        # Consultar as matérias e detalhes do período
        cursor.execute("""
                SELECT
                    m.id AS materia_id,
                    m.nome AS materia_nome,
                    p.media_aprovacao AS media_aprovacao,
                    p.tipo AS tipo_periodo
                FROM
                    materias m
                JOIN
                    periodos p ON m.periodo_id = p.id
                WHERE
                    p.turma_id = %s
        """, (turma_id,))

        materias = cursor.fetchall()

        boletim = {}

        for materia in materias:
            materia_id = materia[0]
            boletim[materia_id] = {
                'nome': materia[1],
                'media_aprovacao': materia[2],
                'tipo_periodo': materia[3],
                'notas': [None] * quantidade_notas
            }

        # Associa as notas às matérias
        for nota in notas:
            materia_id = nota[3]
            if materia_id in boletim:
                boletim[materia_id]['notas'][nota[2]] = nota[1]

        return boletim, tipo_periodo, turma, aluno
    else:
        return None, None, turma, aluno

# NOTE: Para contas EXISTENTES
def enviar_email(db, cursor, tipo, email, token, turma_id, prof_id):
    email_hash = hashlib.sha256(email.encode('utf-8')).hexdigest()

    sender = "noreply@app.com"
    cursor.execute("SELECT * FROM usuarios WHERE email_hash = %s", (email_hash,))
    exists = cursor.fetchone()

    if exists:
        if tipo == "alterar senha":
            assunto = "Alteração de Senha"
            corpo = "Alguém solicitou uma alteração de senha em sua conta. Para prosseguir, clique no link abaixo:"
            msg = Message(assunto, sender=sender, recipients=[email])
            msg.body = ""
            data = {
                'app_name': "GradeSphere Mail",
                'title': assunto,
                'body': corpo
            }

            msg.html = render_template("email_senha.html", data=data, email=email_hash, token=token)

            mail.send(msg)
            return True

        elif tipo == "convite":
            cursor.execute("SELECT nome FROM turmas WHERE id = %s", (turma_id,))
            resultado = cursor.fetchone()

            cursor.execute("SELECT nome FROM usuarios WHERE id = %s", (prof_id,))
            resultado2 = cursor.fetchone()

            if resultado and resultado2:
                turma = cipher_suite.decrypt(bytes(resultado[0])).decode()
                prof_nome = cipher_suite.decrypt(bytes(resultado2[0])).decode()

                assunto = f"Você recebeu um convite de {prof_nome}!"
                corpo = f"Você recebeu um convite para a turma: {turma}, enviado pelo(a) professor(a) {prof_nome}."
                msg = Message(assunto, sender=sender, recipients=[email])
                msg.body = ""
                data = {
                    'app_name': "GradeSphere Mail",
                    'title': assunto,
                    'body': corpo
                }

                msg.html = render_template("email_convite.html", data=data)

                mail.send(msg)
                return True
            else:
                return False
    else:
        return False

# NOTE: Classe criada para resolver problemas de compatibilidade.
# Em meu computador, a função .decrypt(valor) funcionava, pois
# assumia que o "valor" já era bytes. Mas em meu NOTEBOOK,
# não assumia que o valor era bytes. Então, criei uma função que retorna
# esse valor em bytes como uma função de Classe para que possa ser utilizada
# adequadamente de forma flexível pelo Flask, com Python.
class ConverterBytes:
    @classmethod
    def to_bytes(cls, val):
        return bytes(val)

if __name__=="__main__":
    tasks.scheduler.start()
    app.run(debug=True)
