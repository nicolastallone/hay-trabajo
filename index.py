import os
from flask import Flask, request, render_template, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename

app = Flask(__name__)

# CONFIGURACIÓN
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///hay_trabajo.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'hay_trabajo_2026_pro'
app.config['UPLOAD_FOLDER'] = 'static/uploads'

db = SQLAlchemy(app)

# --- MODELOS ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tipo = db.Column(db.String(20)) # 'empleado' o 'comercio'
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    esta_suscrito = db.Column(db.Boolean, default=False)
    
    # Datos Personales / Comerciales
    nombre_completo = db.Column(db.String(100), default="")
    dni = db.Column(db.String(20), default="")
    whatsapp = db.Column(db.String(20), default="")
    direccion = db.Column(db.String(200), default="")
    foto_perfil = db.Column(db.String(200), default="default.png")
    archivo_cv = db.Column(db.String(200), default="")
    rubro = db.Column(db.String(50), default="Otros")
    descripcion_perfil = db.Column(db.Text, default="")

    postulaciones = db.relationship('Application', backref='candidato', lazy=True, cascade="all, delete-orphan")
    avisos = db.relationship('JobPosting', backref='creador', lazy=True, cascade="all, delete-orphan")

class JobPosting(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    comercio_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    titulo = db.Column(db.String(100), nullable=False)
    rubro = db.Column(db.String(50), default="Otros")
    descripcion = db.Column(db.Text)
    activo = db.Column(db.Boolean, default=True)
    
    aplicantes = db.relationship('Application', backref='empleo', lazy=True, cascade="all, delete-orphan")

class Application(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey('job_posting.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    servicio_ofrecido = db.Column(db.Text, default="")

# --- RUTAS ---
@app.route('/')
def home(): return render_template('registro.html')

@app.route('/login')
def login_page(): return render_template('login.html')

@app.route('/registro_proceso', methods=['POST'])
def registro_proceso():
    email = request.form.get('email', '').lower().strip()
    if User.query.filter_by(email=email).first():
        flash("Email ya registrado", "error")
        return redirect(url_for('home'))
    nuevo = User(tipo=request.form.get('tipo'), email=email, password=request.form.get('password'))
    db.session.add(nuevo); db.session.commit()
    session['user_id'] = nuevo.id
    return redirect(url_for('perfil_usuario'))

@app.route('/login_proceso', methods=['POST'])
def login_proceso():
    u = User.query.filter_by(email=request.form.get('email', '').lower().strip(), password=request.form.get('password')).first()
    if u: 
        session['user_id'] = u.id
        return redirect(url_for('perfil_usuario'))
    return redirect(url_for('login_page'))

@app.route('/perfil')
def perfil_usuario():
    u = User.query.get(session.get('user_id'))
    if not u: return redirect(url_for('login_page'))
    
    rubros = ["Gastronomia", "Ropa", "Zapateria", "Almacen", "Ferreteria", "Otros"]
    rubro_sel = request.args.get('rubro', 'Todos')
    
    if u.tipo == 'empleado':
        if rubro_sel == 'Todos':
            empleos = JobPosting.query.filter_by(activo=True).all()
        else:
            empleos = JobPosting.query.filter_by(rubro=rubro_sel, activo=True).all()
        ids_postulados = [p.job_id for p in u.postulaciones]
        return render_template('empleado.html', usuario=u, empleos=empleos, rubros=rubros, ids_postulados=ids_postulados, rubro_sel=rubro_sel)
    else:
        if rubro_sel == 'Todos':
            talentos = User.query.filter_by(tipo='empleado').all()
        else:
            talentos = User.query.filter_by(tipo='empleado', rubro=rubro_sel).all()
        return render_template('comercio.html', usuario=u, talentos=talentos, rubros=rubros, rubro_sel=rubro_sel)

@app.route('/editar_perfil', methods=['POST'])
def editar_perfil():
    u = User.query.get(session.get('user_id'))
    u.nombre_completo = request.form.get('nombre')
    u.dni = request.form.get('dni')
    u.whatsapp = request.form.get('whatsapp')
    u.direccion = request.form.get('direccion')
    u.rubro = request.form.get('rubro')
    u.descripcion_perfil = request.form.get('descripcion')
    
    if 'foto' in request.files:
        f = request.files['foto']
        if f.filename:
            nom = secure_filename(f"perfil_{u.id}_{f.filename}")
            f.save(os.path.join(app.config['UPLOAD_FOLDER'], nom)); u.foto_perfil = nom
    if 'cv' in request.files:
        c = request.files['cv']
        if c.filename:
            nom = secure_filename(f"cv_{u.id}_{c.filename}")
            c.save(os.path.join(app.config['UPLOAD_FOLDER'], nom)); u.archivo_cv = nom
            
    db.session.commit()
    return redirect(url_for('perfil_usuario'))

@app.route('/publicar_empleo', methods=['POST'])
def publicar_empleo():
    u = User.query.get(session.get('user_id'))
    if u.esta_suscrito:
        nuevo = JobPosting(comercio_id=u.id, titulo=request.form.get('titulo'), 
                           rubro=request.form.get('rubro'), descripcion=request.form.get('descripcion'))
        db.session.add(nuevo); db.session.commit()
    return redirect(url_for('perfil_usuario'))

@app.route('/postular/<int:job_id>', methods=['POST'])
def postular(job_id):
    uid = session.get('user_id')
    u = User.query.get(uid)
    if u.esta_suscrito:
        if not Application.query.filter_by(job_id=job_id, user_id=uid).first():
            nueva = Application(job_id=job_id, user_id=uid, servicio_ofrecido=request.form.get('servicio'))
            db.session.add(nueva); db.session.commit()
    return redirect(url_for('perfil_usuario'))

@app.route('/despostular/<int:job_id>')
def despostular(job_id):
    p = Application.query.filter_by(job_id=job_id, user_id=session.get('user_id')).first()
    if p: db.session.delete(p); db.session.commit()
    return redirect(url_for('perfil_usuario'))

@app.route('/gestion_empleo/<int:id>/<string:accion>')
def gestion_empleo(id, accion):
    j = JobPosting.query.get(id)
    if j.comercio_id == session.get('user_id'):
        if accion == 'borrar': db.session.delete(j)
        elif accion == 'pausar': j.activo = not j.activo
        db.session.commit()
    return redirect(url_for('perfil_usuario'))

@app.route('/admin')
def admin_panel():
    users = User.query.all()
    c_count = User.query.filter_by(tipo='comercio').count()
    e_count = User.query.filter_by(tipo='empleado').count()
    return render_template('admin.html', usuarios=users, c_count=c_count, e_count=e_count)

@app.route('/admin_accion/<int:id>/<string:accion>')
def admin_accion(id, accion):
    u = User.query.get(id)
    if accion == 'toggle': u.esta_suscrito = not u.esta_suscrito
    elif accion == 'eliminar': db.session.delete(u)
    db.session.commit()
    return redirect(url_for('admin_panel'))

@app.route('/logout')
def logout(): session.clear(); return redirect(url_for('login_page'))

if __name__ == '__main__':
    with app.app_context():
        if not os.path.exists(app.config['UPLOAD_FOLDER']): os.makedirs(app.config['UPLOAD_FOLDER'])
        db.create_all()
    app.run(host="0.0.0.0", port=5000)
