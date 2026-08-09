from flask import Blueprint, request, jsonify

from modules.db import db_connection
from modules.auth import auth as auth_module

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')


def _extract_bearer_token():
    auth = request.headers.get('Authorization', '')
    if auth.startswith('Bearer '):
        return auth[len('Bearer '):].strip()
    token_arg = request.args.get('token')
    if token_arg:
        return token_arg.strip()
    return None


def get_current_user():
    token = _extract_bearer_token()
    if not token:
        return None
    with db_connection() as conn:
        return auth_module.get_user_from_token(conn, token)


def _is_admin_role(role):
    return role in ('admin', 'superadmin')


def _require_admin():
    user = getattr(request, 'current_user', None)
    if not user or not _is_admin_role(user.get('role')):
        return jsonify({'error': 'Доступ запрещён (нужна роль admin)'}), 403
    return None


# Пути, для которых пишущий (не-GET) запрос не требует ни авторизации, ни
# проверки роли. Пока только logout — он должен быть доступен даже с
# истёкшим/невалидным токеном (сам роут и раньше не проверял валидность
# токена, просто отзывал его "если он вообще был" — не меняем это поведение).
_AUTH_EXEMPT_WRITE_PATHS = ('/api/auth/logout',)


@auth_bp.before_app_request
def load_current_user():
    if request.path.startswith('/api/') and not request.path.startswith('/api/auth/login'):
        request.current_user = get_current_user()

        # Раньше эта функция только ПОДГРУЖАЛА пользователя — ничего не
        # проверяла. На практике это означало, что /api/engine и другие
        # пишущие роуты (PUT/POST/DELETE) были доступны вообще без токена,
        # т.к. ни один из них не был обёрнут в @require_auth. Так как
        # auth_bp регистрируется первым (см. routes/__init__.py), это
        # единственное место, которое реально видит КАЖДЫЙ запрос ко всем
        # blueprint'ам — поэтому проверка добавлена именно тут, а не
        # точечно в каждом роуте.
        if request.method not in ('GET', 'HEAD', 'OPTIONS') and request.path not in _AUTH_EXEMPT_WRITE_PATHS:
            user = request.current_user
            if not user:
                return jsonify({'error': 'Требуется авторизация'}), 401
            if user.get('role') == 'reader':
                return jsonify({'error': 'Недостаточно прав: доступен только просмотр'}), 403


@auth_bp.route('/login', methods=['POST'])
def auth_login():
    try:
        data = request.json or {}
        username = (data.get('username') or '').strip()
        password = data.get('password') or ''
        with db_connection() as conn:
            user = auth_module.get_user_by_username(conn, username)
            if not user or not auth_module.verify_password(password, user['password_hash']):
                return jsonify({'error': 'Неверный логин или пароль'}), 401
            token = auth_module.issue_token(conn, user['id'])
            # Записываем время последнего входа
            if user.get('source') == 'file':
                auth_module.update_file_user_last_login(user['id'])
            else:
                auth_module.update_last_login(conn, user['id'])
        return jsonify({
            'success': True,
            'token': token,
            'user': {
                'id': user['id'],
                'username': user['username'],
                'role': user['role']
            }
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@auth_bp.route('/logout', methods=['POST'])
def auth_logout():
    token = _extract_bearer_token()
    if token:
        with db_connection() as conn:
            auth_module.revoke_token(conn, token)
    return jsonify({'success': True})


@auth_bp.route('/me', methods=['GET'])
def auth_me():
    user = getattr(request, 'current_user', None)
    if not user:
        return jsonify({'error': 'Требуется авторизация'}), 401
    return jsonify({
        'id': user['id'],
        'username': user['username'],
        'role': user['role']
    })


@auth_bp.route('/admin/users', methods=['GET'])
def admin_list_users():
    denied = _require_admin()
    if denied:
        return denied
    try:
        with db_connection() as conn:
            users = auth_module.list_users(conn)
            cur = conn.cursor()
            cur.execute('SELECT user_id, COUNT(*) FROM tokens GROUP BY user_id')
            sessions = {row[0]: row[1] for row in cur.fetchall()}
        # count file-based tokens per username
        file_sessions = {}
        try:
            for t in auth_module._load_file_tokens():
                uname = t.get('username')
                if not uname:
                    continue
                file_sessions[uname] = file_sessions.get(uname, 0) + 1
        except Exception:
            file_sessions = {}
        for u in users:
            if u.get('source') == 'file':
                u['active_sessions'] = file_sessions.get(u.get('username'), 0)
            else:
                u['active_sessions'] = sessions.get(u['id'], 0)
        return jsonify(users)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@auth_bp.route('/admin/users', methods=['POST'])
def admin_create_user():
    denied = _require_admin()
    if denied:
        return denied
    try:
        data = request.json or {}
        username = (data.get('username') or '').strip()
        password = data.get('password') or ''
        role = data.get('role') or 'user'
        if role not in ('user', 'admin', 'superadmin', 'reader'):
            return jsonify({'error': 'Недопустимая роль'}), 400
        current_user = getattr(request, 'current_user', {}) or {}
        if role in ('admin', 'superadmin') and current_user.get('role') != 'superadmin':
            return jsonify({'error': 'Назначать роль admin/superadmin может только суперадмин'}), 403
        if not username or not password:
            return jsonify({'error': 'Логин и пароль обязательны'}), 400
        if len(password) < 6:
            return jsonify({'error': 'Пароль должен быть не короче 6 символов'}), 400
        with db_connection() as conn:
            if auth_module.get_user_by_username(conn, username):
                return jsonify({'error': 'Пользователь с таким логином уже существует'}), 409
            # create as file-based user
            uid = auth_module.create_file_user(username, password, role=role)
        return jsonify({'success': True, 'id': uid})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@auth_bp.route('/admin/users/<int:user_id>', methods=['DELETE'])
def admin_delete_user(user_id):
    denied = _require_admin()
    if denied:
        return denied
    current_user = getattr(request, 'current_user', {}) or {}
    if current_user.get('id') == user_id:
        return jsonify({'error': 'Нельзя удалить самого себя'}), 400
    try:
        with db_connection() as conn:
            target_user = auth_module.get_user_by_id(conn, user_id)
            if not target_user:
                return jsonify({'error': 'Пользователь не найден'}), 404
            if _is_admin_role(target_user.get('role')) and current_user.get('role') != 'superadmin':
                return jsonify({'error': 'Удалять администраторов может только суперадмин'}), 403
            if target_user.get('source') == 'file':
                ok = auth_module.delete_file_user(user_id)
            else:
                ok = auth_module.delete_user(conn, user_id)
            if not ok:
                return jsonify({'error': 'Пользователь не найден'}), 404
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@auth_bp.route('/admin/users/<int:user_id>/password', methods=['POST'])
def admin_change_password(user_id):
    denied = _require_admin()
    if denied:
        return denied
    try:
        data = request.json or {}
        password = data.get('password') or ''
        if not password or len(password) < 6:
            return jsonify({'error': 'Пароль должен быть не короче 6 символов'}), 400
        with db_connection() as conn:
            target_user = auth_module.get_user_by_id(conn, user_id)
            if not target_user:
                return jsonify({'error': 'Пользователь не найден'}), 404
            if target_user.get('source') == 'file':
                ok = auth_module.update_file_user_password(user_id, password)
            else:
                ok = auth_module.update_user_password(conn, user_id, password)
            if not ok:
                return jsonify({'error': 'Не удалось обновить пароль'}), 400
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@auth_bp.route('/admin/users/<int:user_id>/revoke', methods=['POST'])
def admin_revoke_user(user_id):
    denied = _require_admin()
    if denied:
        return denied
    try:
        with db_connection() as conn:
            auth_module.revoke_all_for_user(conn, user_id)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
