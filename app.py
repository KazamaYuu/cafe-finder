from flask import Flask, render_template, request, redirect, url_for, session, flash
import json, os

app = Flask(__name__)
app.secret_key = 'secret-key'

USER_FILE = 'users.json'
ADMIN_FILE = 'admin.json'
CAFE_FILE = 'cafes.json'


def load_json(filename):
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            return json.load(f)
    return []


def save_json(filename, data):
    with open(filename, 'w') as f:
        json.dump(data, f, indent=4)


@app.route('/')
def home():
    cafes = load_json(CAFE_FILE)
    q = request.args.get('q', '').lower()
    lokasi = request.args.get('lokasi', '')
    if q:
        cafes = [c for c in cafes if q in c['nama'].lower() or any(q in k.lower() for k in c['kategori'])]
    if lokasi:
        cafes = [c for c in cafes if c['lokasi'] == lokasi]
    return render_template('index.html', cafes=cafes, q=q, lokasi=lokasi)


@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        admins = load_json(ADMIN_FILE)
        users = load_json(USER_FILE)

        print("DEBUG admins:", admins)      
        print("DEBUG input:", username, password)

        for a in admins:
            if a['username'] == username and a['password'] == password:
                session['username'] = username
                session['role'] = 'admin'
                flash('Login admin berhasil')
                return redirect(url_for('home'))

        for u in users:
            if u['username'] == username and u['password'] == password:
                session['username'] = username
                session['role'] = 'user'
                flash('Login user berhasil')
                return redirect(url_for('home'))

        flash('Username atau password salah!')
    return render_template('login.html')


@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        users = load_json(USER_FILE)
        if any(u['username'] == username for u in users):
            flash('Username sudah dipakai!')
            return redirect(url_for('register'))
        users.append({'username': username, 'password': password})
        save_json(USER_FILE, users)
        flash('Registrasi berhasil! Silakan login.')
        return redirect(url_for('login'))
    return render_template('register.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('Logout berhasil')
    return redirect(url_for('home'))


@app.route('/admin', methods=['GET','POST'])
def admin_page():
    if 'username' not in session or session.get('role') != 'admin':
        flash('Hanya admin yang bisa mengakses halaman ini')
        return redirect(url_for('login'))

    cafes = load_json(CAFE_FILE)

    if request.method == 'POST':
        name = request.form['name']
        district = request.form['district']
        description = request.form['description']
        new_id = str(len(cafes) + 1)
        new_cafe = {
            "id": new_id,
            "nama": name,
            "lokasi": district,
            "kategori": [description],
            "menu": []
        }
        cafes.append(new_cafe)
        save_json(CAFE_FILE, cafes)
        flash('Cafe baru berhasil ditambahkan!')
        return redirect(url_for('admin_page'))

    return render_template('admin.html', cafes=cafes)

@app.route('/admin/delete/<cafe_id>', methods=['POST'])
def delete_cafe(cafe_id):
    if 'username' not in session or session.get('role') != 'admin':
        flash('Hanya admin yang bisa mengakses halaman ini')
        return redirect(url_for('login'))

    cafes = load_json(CAFE_FILE)
    cafes = [c for c in cafes if c['id'] != cafe_id]
    save_json(CAFE_FILE, cafes)
    flash('Cafe berhasil dihapus!')
    return redirect(url_for('admin_page'))


if __name__ == '__main__':
    app.run(debug=True)
