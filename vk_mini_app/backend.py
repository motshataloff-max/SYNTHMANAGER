"""
VK Mini App Backend
===================
Flask-сервер для VK Mini App. Работает с общей БД.
"""
import os
import sqlite3
import secrets
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory

app = Flask(__name__, static_folder='frontend')

# Путь к общей БД (на уровень выше, в папке data)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, 'data', 'bot.db')

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# ==========================================
# FRONTEND
# ==========================================
@app.route('/')
def index():
    return send_from_directory('frontend', 'index.html')

# ==========================================
# API: АВТОРИЗАЦИЯ И СВЯЗЫВАНИЕ АККАУНТОВ
# ==========================================
@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    vk_id = data.get('vk_id')
    client_code = data.get('client_code', '').upper().strip()
    
    if not vk_id:
        return jsonify({"error": "vk_id required"}), 400
    
    conn = get_db()
    
    # 1. Ищем, привязан ли уже этот VK ID
    cur = conn.execute("SELECT * FROM users WHERE vk_id = ?", (vk_id,))
    user = cur.fetchone()
    
    if user:
        conn.close()
        return jsonify({"success": True, "user": dict(user), "message": "С возвращением!"})
    
    # 2. Если указан код клиента, ищем по нему
    if client_code:
        cur = conn.execute("SELECT * FROM users WHERE client_code = ?", (client_code,))
        user = cur.fetchone()
        
        if user:
            # Связываем VK ID с существующим Telegram-аккаунтом
            conn.execute("UPDATE users SET vk_id = ? WHERE telegram_id = ?", (vk_id, user['telegram_id']))
            conn.commit()
            conn.close()
            return jsonify({"success": True, "user": dict(user), "message": "Аккаунты успешно связаны!"})
        else:
            conn.close()
            return jsonify({"error": "Неверный код клиента. Проверьте его в Telegram-боте."}), 404
    
    # 3. Если кода нет, создаем нового пользователя (только для VK)
    new_code = f"SYNTH-{secrets.token_hex(2).upper()}"
    # Используем отрицательный vk_id, чтобы не конфликтовать с telegram_id
    conn.execute("""
        INSERT INTO users (telegram_id, username, full_name, client_code, vk_id)
        VALUES (?, ?, ?, ?, ?)
    """, (-int(vk_id), f"vk_{vk_id}", f"VK Пользователь", new_code, vk_id))
    conn.commit()
    
    cur = conn.execute("SELECT * FROM users WHERE vk_id = ?", (vk_id,))
    user = cur.fetchone()
    conn.close()
    
    return jsonify({
        "success": True,
        "user": dict(user),
        "message": f"Создан новый аккаунт. Ваш код: {new_code}"
    })

# ==========================================
# API: ТИКЕТЫ
# ==========================================
@app.route('/api/tickets', methods=['GET'])
def get_tickets():
    vk_id = request.args.get('vk_id')
    if not vk_id:
        return jsonify({"error": "vk_id required"}), 400
    
    conn = get_db()
    # Ищем заявки как по vk_id (отрицательный), так и по telegram_id (если аккаунты связаны)
    cur = conn.execute("""
        SELECT ticket_number, title, description, budget, status, created_at 
        FROM tickets 
        WHERE user_id = ? OR user_id = (SELECT telegram_id FROM users WHERE vk_id = ?)
        ORDER BY created_at DESC
    """, (-int(vk_id), vk_id))
    
    tickets = [dict(row) for row in cur.fetchall()]
    conn.close()
    
    return jsonify({"tickets": tickets})

# ==========================================
# API: СОЗДАНИЕ ЗАЯВКИ
# ==========================================
@app.route('/api/order', methods=['POST'])
def create_order():
    data = request.json
    vk_id = data.get('vk_id')
    title = data.get('title')
    description = data.get('description', '')
    budget = data.get('budget')
    contact = data.get('contact', '')
    
    if not all([vk_id, title, budget]):
        return jsonify({"error": "Заполните название и бюджет"}), 400
    
    conn = get_db()
    
    # Получаем реальный user_id (если связан, то telegram_id, иначе -vk_id)
    cur = conn.execute("SELECT telegram_id FROM users WHERE vk_id = ?", (vk_id,))
    row = cur.fetchone()
    user_id = row['telegram_id'] if row else -int(vk_id)
    
    # Генерируем номер тикета
    cur = conn.execute("SELECT current_number FROM ticket_counter WHERE id = 1")
    current = (cur.fetchone()[0] if cur.fetchone() else 0) + 1
    ticket_number = f"SYNTH-{datetime.now().year}-{current:04d}"
    conn.execute("UPDATE ticket_counter SET current_number = ? WHERE id = 1", (current,))
    
    # Создаем тикет
    conn.execute("""
        INSERT INTO tickets (ticket_number, user_id, channel, type, title, description, budget, status)
        VALUES (?, ?, 'vk', 'project', ?, ?, ?, 'new')
    """, (ticket_number, user_id, title, f"{description}\n\n📱 Контакт: {contact}", budget))
    
    conn.execute("""
        INSERT INTO ticket_history (ticket_number, action, old_value, new_value, changed_by)
        VALUES (?, 'created', NULL, 'new', ?)
    """, (ticket_number, user_id))
    
    conn.commit()
    conn.close()
    
    return jsonify({"success": True, "ticket_number": ticket_number})

# ==========================================
# API: ПОДДЕРЖКА
# ==========================================
@app.route('/api/support', methods=['POST'])
def create_support():
    data = request.json
    vk_id = data.get('vk_id')
    message = data.get('message')
    
    if not all([vk_id, message]):
        return jsonify({"error": "Введите сообщение"}), 400
    
    conn = get_db()
    
    cur = conn.execute("SELECT telegram_id FROM users WHERE vk_id = ?", (vk_id,))
    row = cur.fetchone()
    user_id = row['telegram_id'] if row else -int(vk_id)
    
    cur = conn.execute("SELECT current_number FROM ticket_counter WHERE id = 1")
    current = (cur.fetchone()[0] if cur.fetchone() else 0) + 1
    ticket_number = f"SYNTH-{datetime.now().year}-{current:04d}"
    conn.execute("UPDATE ticket_counter SET current_number = ? WHERE id = 1", (current,))
    
    conn.execute("""
        INSERT INTO tickets (ticket_number, user_id, channel, type, title, description, status)
        VALUES (?, ?, 'vk', 'support', 'Обращение в поддержку (VK)', ?, 'new')
    """, (ticket_number, user_id, message))
    
    conn.commit()
    conn.close()
    
    return jsonify({"success": True, "ticket_number": ticket_number})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8081))
    app.run(host='0.0.0.0', port=port)
