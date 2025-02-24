from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
import string
import random
from datetime import datetime
import bcrypt

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# 初始化数据库
def init_db():
    conn = sqlite3.connect('short_url.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                 username TEXT NOT NULL UNIQUE,
                 password TEXT NOT NULL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS links
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                 user_id INTEGER,
                 long_url TEXT NOT NULL,
                 short_url TEXT NOT NULL UNIQUE,
                 clicks INTEGER DEFAULT 0,
                 created_at TEXT NOT NULL,
                 FOREIGN KEY (user_id) REFERENCES users(id))''')
    conn.commit()
    conn.close()

# 生成短链接
def generate_short_url(custom_suffix=None):
    if custom_suffix:
        return custom_suffix
    characters = string.ascii_letters + string.digits
    short_url = ''.join(random.choice(characters) for i in range(6))
    return short_url

# 注册页面
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password'].encode('utf-8')
        hashed = bcrypt.hashpw(password, bcrypt.gensalt())
        conn = sqlite3.connect('short_url.db')
        c = conn.cursor()
        try:
            c.execute("INSERT INTO users (username, password) VALUES (?,?)", (username, hashed))
            conn.commit()
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            return "Username already exists. Please choose another one."
        finally:
            conn.close()
    return render_template('register.html')

# 登录页面
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password'].encode('utf-8')
        conn = sqlite3.connect('short_url.db')
        c = conn.cursor()
        c.execute("SELECT id, password FROM users WHERE username =?", (username,))
        user = c.fetchone()
        conn.close()
        if user:
            user_id, hashed = user
            if bcrypt.checkpw(password, hashed):
                session['user_id'] = user_id
                return redirect(url_for('index'))
        return "Invalid username or password."
    return render_template('login.html')

# 主页
@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user_id = session['user_id']
    conn = sqlite3.connect('short_url.db')
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM links WHERE user_id =?", (user_id,))
    link_count = c.fetchone()[0]
    c.execute("SELECT short_url, long_url, clicks, created_at FROM links WHERE user_id =? ORDER BY created_at DESC LIMIT 5", (user_id,))
    latest_links = c.fetchall()
    conn.close()
    return render_template('index.html', link_count=link_count, latest_links=latest_links)

# 已创建的链接列表页面
@app.route('/link_list', methods=['GET', 'POST'])
def link_list():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user_id = session['user_id']
    conn = sqlite3.connect('short_url.db')
    c = conn.cursor()
    if request.method == 'POST':
        long_url = request.form['long_url']
        custom_suffix = request.form.get('custom_suffix')
        short_url = generate_short_url(custom_suffix)
        created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        try:
            c.execute("INSERT INTO links (user_id, long_url, short_url, created_at) VALUES (?,?,?,?)", (user_id, long_url, short_url, created_at))
            conn.commit()
        except sqlite3.IntegrityError:
            return "Custom suffix already exists. Please choose another one."
    c.execute("SELECT short_url, long_url, clicks, created_at FROM links WHERE user_id =?", (user_id,))
    links = c.fetchall()
    conn.close()
    return render_template('link_list.html', links=links)

# 编辑链接页面
@app.route('/edit_link/<short_url>', methods=['GET', 'POST'])
def edit_link(short_url):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user_id = session['user_id']
    conn = sqlite3.connect('short_url.db')
    c = conn.cursor()
    if request.method == 'POST':
        new_long_url = request.form['long_url']
        new_custom_suffix = request.form.get('custom_suffix')
        new_short_url = generate_short_url(new_custom_suffix)
        try:
            c.execute("UPDATE links SET long_url =?, short_url =? WHERE short_url =? AND user_id =?", (new_long_url, new_short_url, short_url, user_id))
            conn.commit()
            return redirect(url_for('link_list'))
        except sqlite3.IntegrityError:
            return "Custom suffix already exists. Please choose another one."
    c.execute("SELECT long_url FROM links WHERE short_url =? AND user_id =?", (short_url, user_id))
    result = c.fetchone()
    if result:
        long_url = result[0]
        return render_template('edit_link.html', short_url=short_url, long_url=long_url)
    else:
        return "Link not found."

# 链接详情页面
@app.route('/link_detail/<short_url>')
def link_detail(short_url):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = sqlite3.connect('short_url.db')
    c = conn.cursor()
    c.execute("SELECT clicks FROM links WHERE short_url =?", (short_url,))
    result = c.fetchone()
    if result:
        clicks = result[0]
        return render_template('link_detail.html