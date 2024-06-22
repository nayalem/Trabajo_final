import logging
import os
from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.utils import secure_filename
from flask_graphql import GraphQLView
import graphene
from graphene_sqlalchemy import SQLAlchemyObjectType, SQLAlchemyConnectionField

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


logging.basicConfig(level=logging.DEBUG)


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:@localhost:3306/adopciones'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Configuración para la carga de archivos
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 # 16 MB

# Inicialización de SQLAlchemy
db = SQLAlchemy(app)

# Definición del modelo SQLAlchemy para Registro y Perro
class Registro(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    telefono = db.Column(db.String(20), nullable=False)

class Perro(db.Model):
    __tablename__ = 'perritos'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    raza = db.Column(db.String(100), nullable=False)
    edad = db.Column(db.Integer, nullable=False)
    descripcion = db.Column(db.Text, nullable=False)
    imagen = db.Column(db.String(255), nullable=False)

    def __repr__(self):
        return f'<Perro {self.id}: {self.nombre}>'

# Definición de tipos de objeto GraphQL para SQLAlchemy
class RegistroObject(SQLAlchemyObjectType):
    class Meta:
        model = Registro
        interfaces = (graphene.relay.Node, )

class PerroObject(SQLAlchemyObjectType):
    class Meta:
        model = Perro
        interfaces = (graphene.relay.Node, )

# Definición de esquema GraphQL
class Query(graphene.ObjectType):
    registros = SQLAlchemyConnectionField(RegistroObject)
    perros = SQLAlchemyConnectionField(PerroObject)

schema = graphene.Schema(query=Query)


with app.app_context():
    db.create_all()


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/adopcion')
def adopcion():
    perros = Perro.query.all()
    return render_template('adopcion.html', perros=perros)

@app.route('/agregar_perro', methods=['GET', 'POST'])
def agregar_perro():
    if request.method == 'POST':
        nombre = request.form['nombre']
        raza = request.form['raza']
        edad = request.form['edad']
        descripcion = request.form['descripcion']
        imagen = request.files['imagen']  # Acceder al archivo de imagen

        if nombre and raza and edad and descripcion and imagen:
            try:
                # Guardar la imagen en la carpeta de uploads
                if imagen and allowed_file(imagen.filename):
                    filename = secure_filename(imagen.filename)
                    imagen.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

                # Crear un nuevo perro con la información
                nuevo_perro = Perro(nombre=nombre, raza=raza, edad=edad, descripcion=descripcion, imagen=filename)
                db.session.add(nuevo_perro)
                db.session.commit()
                logging.debug("Nuevo perro añadido correctamente")
                return redirect(url_for('adopcion'))
            except SQLAlchemyError as e:
                db.session.rollback()
                logging.error(f"Error al añadir un nuevo perro: {e}")
                return render_template('agregar_perro.html', error="Ocurrió un error al añadir el perro. Inténtalo de nuevo más tarde.")
            except Exception as e:
                logging.error(f"Error inesperado al añadir perro: {e}")
                return render_template('agregar_perro.html', error="Ocurrió un error inesperado. Inténtalo de nuevo más tarde.")
        else:
            return render_template('agregar_perro.html', error="Por favor, completa todos los campos.")
    else:
        return render_template('agregar_perro.html')
#----------------------------
@app.route('/eliminar_perro/<int:perro_id>', methods=['POST'])
def eliminar_perro(perro_id):
    perro = Perro.query.get_or_404(perro_id)
    try:
        db.session.delete(perro)
        db.session.commit()
        logging.debug(f"Perro con ID {perro_id} eliminado correctamente")
        perros_actualizados = Perro.query.all()
        return render_template('adopcion.html', perros=perros_actualizados)
    except SQLAlchemyError as e:
        db.session.rollback()
        logging.error(f"Error al eliminar el perro con ID {perro_id}: {e}")
        return render_template('adopcion.html', perros=Perro.query.all(), error="Ocurrió un error al eliminar el perro. Inténtalo de nuevo más tarde."), 500
    except Exception as e:
        logging.error(f"Error inesperado al eliminar perro: {e}")
        return render_template('adopcion.html', perros=Perro.query.all(), error="Ocurrió un error inesperado. Inténtalo de nuevo más tarde."), 500

@app.route('/pedidos', methods=['GET', 'POST'])
def pedidos():
    if request.method == 'POST':
        nombre = request.form['nombre']
        telefono = request.form['telefono']

        if nombre and telefono:
            try:
                nuevo_registro = Registro(nombre=nombre, telefono=telefono)
                db.session.add(nuevo_registro)
                db.session.commit()
                logging.debug("Registro guardado exitosamente en la base de datos")
                return render_template('confirmacion.html', success=True, nombre=nombre, telefono=telefono)
            except SQLAlchemyError as e:
                db.session.rollback()
                logging.error(f"Error al guardar en la base de datos: {e}")
                return render_template('pedidos.html', success=False, error=f'Ocurrió un error: {e}')
            except Exception as e:
                logging.error(f"Error inesperado: {e}")
                return render_template('pedidos.html', success=False, error=f'Ocurrió un error inesperado: {e}')
        else:
            logging.warning("Formulario incompleto")
            return render_template('pedidos.html', success=False, error='Por favor, rellena todos los campos del formulario.')
    else:
        return render_template('pedidos.html')

# Configuración de GraphQL
app.add_url_rule('/graphql', view_func=GraphQLView.as_view('graphql', schema=schema, graphiql=True))

# Punto de entrada para ejecutar la aplicación Flask
if __name__ == '__main__':
    app.run(debug=True, port=8080)














