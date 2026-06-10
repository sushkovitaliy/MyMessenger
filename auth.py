from functools import wraps
from flask import flash, redirect, url_for
from flask_login import current_user

def login_required_redirect(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Пожалуйста, авторизуйтесь для доступа к этой странице', 'warning')
            return redirect(url_for('main.login'))
        return f(*args, **kwargs)
    return decorated_function

def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Пожалуйста, авторизуйтесь', 'warning')
                return redirect(url_for('main.login'))
            
            if current_user.role.value not in roles:
                flash('У вас недостаточно прав для доступа к этой странице', 'danger')
                return redirect(url_for('main.chat'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def admin_required(f):
    # Декоратор для страниц, доступных только администраторам
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Пожалуйста, авторизуйтесь', 'warning')
            return redirect(url_for('main.login'))
        
        if not current_user.is_admin():
            flash('Доступ запрещен. Требуются права администратора.', 'danger')
            return redirect(url_for('main.chat'))
        
        return f(*args, **kwargs)
    return decorated_function