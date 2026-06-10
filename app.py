from flask import Flask
from flask_login import LoginManager
from dotenv import load_dotenv
import os
from datetime import timedelta
from models import db, User, RoleEnum

load_dotenv()

login_manager = LoginManager()

def create_app():
    app = Flask(__name__)
    
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-key')
    app.config['SQLALCHEMY_DATABASE_URI'] = f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}/{os.getenv('DB_NAME')}"
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    app.config['REMEMBER_COOKIE_DURATION'] = timedelta(seconds=1)
    app.config['SESSION_COOKIE_DURATION'] = timedelta(days=30)
    
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'main.login'
    login_manager.login_message = 'Пожалуйста, авторизуйтесь'
    login_manager.login_message_category = 'warning'
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    from routes import bp
    app.register_blueprint(bp)
    
    return app

def init_database(app):
    # Создание таблиц и заполнение тестовыми данными
    with app.app_context():
        try:
            db.create_all()
            
            if User.query.count() == 0:
                admin = User(username='admin', email='admin@example.com', role=RoleEnum.ADMIN)
                admin.set_password('admin123')
                db.session.add(admin)
                
                user1 = User(username='alice', email='alice@example.com', phone='+73851230548', bio='Люблю котиков и программирование')
                user1.set_password('alice123')
                db.session.add(user1)
                
                user2 = User(username='bob', email='bob@example.com', phone='+74996105439', bio='Интересуюсь музыкой и спортом')
                user2.set_password('bob123')
                db.session.add(user2)
                
                user3 = User(username='charlie', email='charlie@example.com', bio='Новый пользователь')
                user3.set_password('charlie123')
                db.session.add(user3)
                
                db.session.commit()
                
        except Exception as e:
            print(f"Ошибка при инициализации базы данных: {e}")
            import traceback
            traceback.print_exc()
            raise e

if __name__ == '__main__':
    app = create_app()
    init_database(app)
    
    app.run(
        debug=True,
        host='0.0.0.0',
        port=5000,
    )