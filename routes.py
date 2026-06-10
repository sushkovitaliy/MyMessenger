from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from models import db, User, Message, RoleEnum
from auth import admin_required
from sqlalchemy import and_
from datetime import datetime

bp = Blueprint('main', __name__)

# Аутентификация
@bp.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('main.chat'))
    return redirect(url_for('main.login'))

@bp.route('/login', methods=['GET', 'POST'])
def login():    
    if current_user.is_authenticated:
        return redirect(url_for('main.chat'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            if user.is_blocked:
                flash('Ваш аккаунт заблокирован. Обратитесь к администратору.', 'danger')
                return render_template('login.html')
            
            login_user(user)
            flash(f'Добро пожаловать, {user.username}!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page if next_page else url_for('main.chat'))
        else:
            flash('Неверное имя пользователя или пароль', 'danger')
    
    return render_template('login.html')

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.chat'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        phone = request.form.get('phone')
        password = request.form.get('password')
        password2 = request.form.get('password2')
        
        if password != password2:
            flash('Пароли не совпадают', 'danger')
            return render_template('register.html')
        
        if User.query.filter_by(username=username).first():
            flash('Пользователь с таким именем уже существует', 'danger')
            return render_template('register.html')
        
        if User.query.filter_by(email=email).first():
            flash('Пользователь с таким email уже существует', 'danger')
            return render_template('register.html')
        
        if phone and User.query.filter_by(phone=phone).first():
            flash('Пользователь с таким номером телефона уже существует', 'danger')
            return render_template('register.html')
        
        user = User(username=username, email=email, phone=phone if phone else None)
        user.set_password(password)
        
        if User.query.count() == 0:
            user.role = RoleEnum.ADMIN
            flash('Вы зарегистрированы как администратор!', 'success')
        
        db.session.add(user)
        db.session.commit()
        
        login_user(user)
        flash('Регистрация успешно завершена!', 'success')
        return redirect(url_for('main.chat'))
    
    return render_template('register.html')

@bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы вышли из системы', 'info')
    return redirect(url_for('main.login'))

# Профиль пользователя
@bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        phone = request.form.get('phone')
        birth_date = request.form.get('birth_date')
        bio = request.form.get('bio')
        
        if phone:
            existing = User.query.filter_by(phone=phone).first()
            if existing and existing.id != current_user.id:
                flash('Этот номер телефона уже используется другим пользователем', 'danger')
                return redirect(url_for('main.profile'))
            current_user.phone = phone
        
        if birth_date:
            try:
                current_user.birth_date = datetime.strptime(birth_date, '%Y-%m-%d').date()
            except ValueError:
                flash('Неверный формат даты', 'danger')
        
        current_user.bio = bio
        db.session.commit()
        flash('Профиль успешно обновлён', 'success')
        return redirect(url_for('main.profile'))
    
    return render_template('profile.html')

# Автообновление диалогов
@bp.route('/api/dialogs')
@login_required
def api_dialogs():
    sent_with = db.session.query(Message.receiver_id).filter(
        Message.sender_id == current_user.id,
        Message.is_deleted_for_sender == False
    ).distinct().all()
    
    received_from = db.session.query(Message.sender_id).filter(
        Message.receiver_id == current_user.id,
        Message.is_deleted_for_receiver == False
    ).distinct().all()
    
    user_ids = set([id for (id,) in sent_with] + [id for (id,) in received_from])
    users = User.query.filter(User.id.in_(user_ids), User.is_blocked == False).all()
    
    dialogs = []
    for user in users:
        last_message = Message.query.filter(
            and_(
                ((Message.sender_id == current_user.id) & (Message.receiver_id == user.id) & (Message.is_deleted_for_sender == False)) |
                ((Message.sender_id == user.id) & (Message.receiver_id == current_user.id) & (Message.is_deleted_for_receiver == False))
            )
        ).order_by(Message.created_at.desc()).first()
        
        if last_message:
            unread_count = Message.query.filter(
                Message.sender_id == user.id,
                Message.receiver_id == current_user.id,
                Message.is_read == False,
                Message.is_deleted_for_receiver == False
            ).count()
            
            dialogs.append({
                'user_id': user.id,
                'username': user.username,
                'avatar_letter': user.get_avatar_letter(),
                'last_message_text': last_message.text[:50] if last_message.text else '',
                'last_message_time': last_message.created_at.isoformat(),
                'unread_count': unread_count
            })
    
    dialogs.sort(key=lambda x: x['last_message_time'], reverse=True)
    
    return jsonify({'dialogs': dialogs})

@bp.route('/api/messages/<int:user_id>')
@login_required
def api_messages(user_id):
    after_time = request.args.get('after')
    
    query = Message.query.filter(
        and_(
            ((Message.sender_id == current_user.id) & (Message.receiver_id == user_id) & (Message.is_deleted_for_sender == False)) |
            ((Message.sender_id == user_id) & (Message.receiver_id == current_user.id) & (Message.is_deleted_for_receiver == False))
        )
    )
    
    if after_time:
        try:
            after_time = datetime.fromisoformat(after_time)
            query = query.filter(Message.created_at > after_time)
        except:
            pass
    
    messages = query.order_by(Message.created_at.asc()).all()
    
    result = []
    for msg in messages:
        result.append({
            'id': msg.id,
            'text': msg.text,
            'sender_id': msg.sender_id,
            'is_read': msg.is_read,
            'created_at': msg.created_at.isoformat()
        })
    
    # Помечаем сообщения от собеседника как прочитанные
    Message.query.filter(
        Message.sender_id == user_id,
        Message.receiver_id == current_user.id,
        Message.is_read == False
    ).update({'is_read': True})
    db.session.commit()
    
    return jsonify({'messages': result, 'current_user_id': current_user.id})

@bp.route('/api/search_users')
@login_required
def api_search_users():
    query = request.args.get('q', '').strip()
    
    existing_user_ids = set()
    existing_msgs = Message.query.filter(
        (Message.sender_id == current_user.id) | (Message.receiver_id == current_user.id)
    ).all()
    for msg in existing_msgs:
        existing_user_ids.add(msg.sender_id)
        existing_user_ids.add(msg.receiver_id)
    
    users = User.query.filter(
        User.id != current_user.id,
        User.is_blocked == False,
        User.id.notin_(existing_user_ids)
    )
    
    if query:
        users = users.filter(User.username.ilike(f'%{query}%'))
    
    users = users.limit(10).all()
    
    return jsonify({
        'users': [{'id': u.id, 'username': u.username, 'avatar_letter': u.get_avatar_letter()} for u in users]
    })

# Чат
@bp.route('/chat')
@login_required
def chat():
    return render_template('chat.html')

@bp.route('/chat/<int:user_id>')
@login_required
def conversation(user_id):
    other_user = User.query.get_or_404(user_id)
    return render_template('conversation.html', other_user=other_user)

@bp.route('/send_message/<int:user_id>', methods=['POST'])
@login_required
def send_message(user_id):
    other_user = User.query.get_or_404(user_id)
    
    if other_user.is_blocked:
        return jsonify({'error': 'Пользователь заблокирован'}), 403
    
    text = request.json.get('message', '').strip()
    
    if not text:
        return jsonify({'error': 'Введите сообщение'}), 400
    
    message = Message(
        text=text,
        sender_id=current_user.id,
        receiver_id=user_id
    )
    
    db.session.add(message)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': {
            'id': message.id,
            'text': message.text,
            'sender_id': message.sender_id,
            'created_at': message.created_at.isoformat()
        }
    })

# Удаление сообщений
@bp.route('/delete_message/<int:message_id>', methods=['DELETE'])
@login_required
def delete_message(message_id):
    message = Message.query.get_or_404(message_id)
    
    if message.sender_id != current_user.id and message.receiver_id != current_user.id:
        return jsonify({'error': 'Доступ запрещён'}), 403
    
    delete_for_all = request.json.get('delete_for_all', False)
    
    if delete_for_all:
        message.is_deleted_for_sender = True
        message.is_deleted_for_receiver = True
    else:
        message.delete_for_user(current_user.id)
    
    db.session.commit()
    
    return jsonify({'success': True})

# Удаление диалога
@bp.route('/delete_conversation/<int:user_id>', methods=['DELETE'])
@login_required
def delete_conversation(user_id):
    messages = Message.query.filter(
        ((Message.sender_id == current_user.id) & (Message.receiver_id == user_id)) |
        ((Message.sender_id == user_id) & (Message.receiver_id == current_user.id))
    ).all()
    
    for message in messages:
        message.delete_for_user(current_user.id)
    
    db.session.commit()
    
    return jsonify({'success': True})

# Административная панель
@bp.route('/admin/users')
@admin_required
def admin_users():
    users = User.query.all()
    return render_template('admin/users.html', users=users)

@bp.route('/admin/block_user/<int:user_id>', methods=['POST'])
@admin_required
def block_user(user_id):
    user = User.query.get_or_404(user_id)
    
    if user.id == current_user.id:
        flash('Вы не можете заблокировать самого себя', 'danger')
        return redirect(url_for('main.admin_users'))
    
    if user.is_admin():
        flash('Нельзя заблокировать администратора', 'danger')
        return redirect(url_for('main.admin_users'))
    
    user.block()
    db.session.commit()
    flash(f'Пользователь {user.username} заблокирован', 'success')
    return redirect(url_for('main.admin_users'))

@bp.route('/admin/unblock_user/<int:user_id>', methods=['POST'])
@admin_required
def unblock_user(user_id):
    user = User.query.get_or_404(user_id)
    user.unblock()
    db.session.commit()
    flash(f'Пользователь {user.username} разблокирован', 'success')
    return redirect(url_for('main.admin_users'))

@bp.route('/admin/delete_user/<int:user_id>', methods=['POST'])
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    
    if user.id == current_user.id:
        flash('Вы не можете удалить самого себя', 'danger')
        return redirect(url_for('main.admin_users'))
    
    if user.is_admin():
        flash('Нельзя удалить администратора', 'danger')
        return redirect(url_for('main.admin_users'))
    
    username = user.username
    db.session.delete(user)
    db.session.commit()
    
    flash(f'Пользователь {username} удалён', 'success')
    return redirect(url_for('main.admin_users'))