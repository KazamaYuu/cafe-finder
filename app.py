
# ---------- Maps All Cafes ----------
# (Pindahkan ke bawah setelah deklarasi app)
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import os, json
from datetime import datetime

app = Flask(__name__)
app.secret_key = "rahasia-supersafe"  # ganti sebelum deploy

# Paths
UPLOAD_FOLDER = os.path.join('static', 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXT = {'png', 'jpg', 'jpeg', 'gif'}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

CAFE_FILE = 'cafes.json'
USERS_FILE = 'users.json'
ADMIN_FILE = 'admin.json'
REVIEWS_FILE = 'reviews.json'

# ---------- Helpers: load/save JSON ----------
def read_json(path, default):
    if not os.path.exists(path):
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(default, f, indent=2, ensure_ascii=False)
        return default
    with open(path, 'r', encoding='utf-8') as f:
        try:
            return json.load(f)
        except:
            return default

def write_json(path, obj):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)

# ---------- Reviews helpers ----------
def load_reviews():
    return read_json(REVIEWS_FILE, [])

def save_reviews(data):
    write_json(REVIEWS_FILE, data)

def get_reviews_for_cafe(cafe_id):
    reviews = load_reviews()
    return [r for r in reviews if str(r.get('cafe_id')) == str(cafe_id)]

# ---------- Auth: load users & admins ----------
def load_auth():
    users_list = read_json(USERS_FILE, [])
    admins_list = read_json(ADMIN_FILE, [])
    users = {}
    for u in users_list:
        role = u.get('role', 'user')
        users[u['username']] = {'password': u['password'], 'role': role}
    for a in admins_list:
        uname = a.get('username')
        pwd = a.get('password', '')
        users[uname] = {'password': pwd, 'role': 'admin'}
    return users

def save_new_user(username, raw_password):
    users_list = read_json(USERS_FILE, [])
    pwd_hash = generate_password_hash(raw_password)
    users_list.append({'username': username, 'password': pwd_hash, 'role': 'user'})
    write_json(USERS_FILE, users_list)

# ---------- Cafes helpers ----------
def load_cafes():
    data = read_json(CAFE_FILE, [])
    for i, c in enumerate(data, start=1):
        try:
            c['id'] = str(c.get('id', str(i)))
        except:
            c['id'] = str(i)
    c.setdefault('nama', '')
    c.setdefault('lokasi', '')
    c.setdefault('kategori', [])
    c.setdefault('menu', [])
    c.setdefault('photo', None)
    c.setdefault('latitude', None)
    c.setdefault('longitude', None)
    return data

def save_cafes(data):
    write_json(CAFE_FILE, data)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXT

def get_cafe(cafes, cafe_id):
    return next((c for c in cafes if str(c['id']) == str(cafe_id)), None)

def recommend(cafe, cafes, top_n=4):
    scores = []
    base_tags = set([t.lower() for t in cafe.get('kategori', [])])
    for c in cafes:
        if str(c['id']) == str(cafe['id']):
            continue
        score = 0
        if c.get('lokasi') == cafe.get('lokasi'):
            score += 2
        score += len(base_tags & set([t.lower() for t in c.get('kategori',[])]))
        scores.append((score, c))
    scores.sort(key=lambda x: x[0], reverse=True)
    return [c for s,c in scores[:top_n]]

# ---------- Routes ----------

@app.route('/')
def root():
    if 'username' not in session:
        return redirect(url_for('login'))
    if session.get('role') == 'admin':
        return redirect(url_for('admin_page'))
    return redirect(url_for('home'))

@app.route('/home')
def home():
    cafes = load_cafes()
    q = request.args.get('q', '').strip().lower()
    lokasi = request.args.get('lokasi', '').strip()
    kategori_raw = request.args.getlist('kategori')
    kategori = [k.lower() for k in kategori_raw]

    filtered = []
    for c in cafes:
        ok = True
        if q:
            hay = " ".join([
                str(c.get('nama','')).lower(),
                str(c.get('lokasi','')).lower(),
                " ".join([k.lower() for k in c.get('kategori',[])]),
                " ".join([m.get('nama','').lower() for m in c.get('menu',[])])
            ])
            if q not in hay:
                ok = False
        if lokasi and c.get('lokasi') != lokasi:
            ok = False
        if kategori:
            cats = [k.lower() for k in c.get('kategori',[])]
            if not any(k in cats for k in kategori):
                ok = False
        if ok:
            filtered.append(c)
    favorites = session.get('favorites', [])
    return render_template('index.html', cafes=filtered, q=q, lokasi=lokasi, kategori=','.join(kategori_raw), favorites=favorites)

@app.route('/cafe/<cafe_id>', methods=['GET', 'POST'])
def cafe_detail(cafe_id):
    cafes = load_cafes()
    cafe = get_cafe(cafes, cafe_id)
    if not cafe:
        flash('Cafe tidak ditemukan', 'danger')
        return redirect(url_for('home'))
    recs = recommend(cafe, cafes)
    favs = session.get('favorites', [])
    reviews = get_reviews_for_cafe(cafe_id)
    avg_rating = None
    if reviews:
        avg_rating = round(sum([r.get('rating',0) for r in reviews])/len(reviews), 2)

    if request.method == 'POST':
        if 'username' not in session:
            flash('Login untuk memberikan review', 'warning')
            return redirect(url_for('login'))
        user = session['username']
        rating = int(request.form.get('rating', 0))
        text = request.form.get('review', '').strip()
        if rating < 1 or rating > 5:
            flash('Rating harus 1-5', 'warning')
            return redirect(url_for('cafe_detail', cafe_id=cafe_id))
        if not text:
            flash('Review tidak boleh kosong', 'warning')
            return redirect(url_for('cafe_detail', cafe_id=cafe_id))
        reviews = load_reviews()
        reviews.append({
            'cafe_id': cafe_id,
            'user': user,
            'rating': rating,
            'text': text,
            'timestamp': datetime.now().isoformat()
        })
        save_reviews(reviews)
        flash('Review berhasil ditambahkan', 'success')
        return redirect(url_for('cafe_detail', cafe_id=cafe_id))

    return render_template('detail.html', cafe=cafe, recs=recs, favorites=favs, reviews=reviews, avg_rating=avg_rating)

@app.route('/favorite/toggle/<cafe_id>', methods=['POST'])
def toggle_favorite(cafe_id):
    if 'favorites' not in session:
        session['favorites'] = []
    favs = session['favorites']
    if cafe_id in favs:
        favs.remove(cafe_id)
        flash('Dihapus dari favorit', 'info')
    else:
        favs.append(cafe_id)
        flash('Ditambahkan ke favorit', 'success')
    session['favorites'] = favs
    return redirect(request.referrer or url_for('home'))

# ---------- Auth ----------
@app.route('/login', methods=['GET','POST'])
def login():
    auth = load_auth()
    if request.method == 'POST':
        uname = request.form.get('username','').strip()
        pw = request.form.get('password','').strip()
        user = auth.get(uname)
        if user:
            stored = user.get('password','')
            if stored.startswith('pbkdf2:') or stored.startswith('sha256:'):
                ok = check_password_hash(stored, pw)
            else:
                ok = (stored == pw)
            if ok:
                session['username'] = uname
                session['role'] = user.get('role','user')
                flash('Berhasil login', 'success')
                if session['role'] == 'admin':
                    return redirect(url_for('admin_page'))
                return redirect(url_for('home'))
        flash('Username atau password salah', 'danger')
    return render_template('login.html')

@app.route('/register', methods=['GET','POST'])
def register():
    error = None
    if request.method == 'POST':
        uname = request.form.get('username','').strip()
        pw = request.form.get('password','').strip()
        pw2 = request.form.get('password2','').strip()
        if not uname or not pw:
            error = 'Username / password tidak boleh kosong'
        elif pw != pw2:
            error = 'Password dan konfirmasi tidak sama'
        else:
            auth = load_auth()
            if uname in auth:
                error = 'Username sudah terdaftar'
            else:
                save_new_user(uname, pw)
                flash('Berhasil register. Silakan login.', 'success')
                return redirect(url_for('login'))
        if error:
            flash(error, 'warning')
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Anda sudah logout', 'info')
    return redirect(url_for('login'))

# ---------- Admin ----------
def admin_required():
    if session.get('role') != 'admin':
        flash('Hanya admin yang boleh mengakses halaman ini', 'danger')
        return False
    return True

@app.route('/admin', methods=['GET','POST'])
def admin_page():
    if not admin_required():
        return redirect(url_for('login'))

    cafes = load_cafes()
    print("DEBUG admin cafes:", cafes)

    if request.method == 'POST':
        name = request.form.get('name','').strip()
        lokasi = request.form.get('lokasi','').strip()
        kategori_raw = request.form.get('kategori','').strip()
        kategori = [k.strip() for k in kategori_raw.split(',') if k.strip()]

        menu_names = request.form.getlist('menu_name[]')
        menu_prices = request.form.getlist('menu_price[]')
        menu = []
        for n,p in zip(menu_names, menu_prices):
            n = n.strip()
            try:
                pval = int(p)
            except:
                try:
                    pval = int(float(p))
                except:
                    pval = 0
            if n:
                menu.append({'nama': n, 'harga': pval})

        filename = None
        file = request.files.get('photo')
        if file and file.filename != '':
            if allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            else:
                flash('Tipe file tidak diizinkan (jpg/png/gif)', 'warning')

        new_id = str(max([int(c['id']) for c in cafes], default=0) + 1)
        cafes.append({
            'id': new_id,
            'nama': name,
            'lokasi': lokasi,
            'kategori': kategori,
            'menu': menu,
            'photo': filename
        })
        save_cafes(cafes)
        flash('Cafe berhasil ditambahkan', 'success')
        return redirect(url_for('admin_page'))

    return render_template('admin.html', cafes=cafes)

@app.route('/update/<cafe_id>', methods=['GET','POST'])
def update_cafe(cafe_id):
    if not admin_required():
        return redirect(url_for('login'))
    cafes = load_cafes()
    cafe = get_cafe(cafes, cafe_id)
    if not cafe:
        flash('Cafe tidak ditemukan', 'danger')
        return redirect(url_for('admin_page'))

    if request.method == 'POST':
        cafe['nama'] = request.form.get('name','').strip()
        cafe['lokasi'] = request.form.get('lokasi','').strip()
        kategori_raw = request.form.get('kategori','').strip()
        cafe['kategori'] = [k.strip() for k in kategori_raw.split(',') if k.strip()]

        menu_names = request.form.getlist('menu_name[]')
        menu_prices = request.form.getlist('menu_price[]')
        menu = []
        for n,p in zip(menu_names, menu_prices):
            n = n.strip()
            try:
                pval = int(p)
            except:
                try:
                    pval = int(float(p))
                except:
                    pval = 0
            if n:
                menu.append({'nama': n, 'harga': pval})
        if menu:
            cafe['menu'] = menu

        # Maps coordinates
        lat = request.form.get('latitude', '').strip()
        lon = request.form.get('longitude', '').strip()
        cafe['latitude'] = float(lat) if lat else None
        cafe['longitude'] = float(lon) if lon else None

        file = request.files.get('photo')
        if file and file.filename != '':
            if allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                cafe['photo'] = filename
            else:
                flash('Tipe file tidak diizinkan (jpg/png/gif)', 'warning')

        save_cafes(cafes)
        flash('Cafe berhasil diupdate', 'success')
        return redirect(url_for('admin_page'))

    return render_template('update_cafe.html', cafe=cafe)

@app.route('/delete/<cafe_id>', methods=['POST'])
def delete_cafe(cafe_id):
    if not admin_required():
        return redirect(url_for('login'))
    cafes = load_cafes()
    cafes = [c for c in cafes if str(c['id']) != str(cafe_id)]
    for i,c in enumerate(cafes, start=1):
        c['id'] = str(i)
    save_cafes(cafes)
    flash('Cafe berhasil dihapus', 'info')
    return redirect(url_for('admin_page'))

# optional: API
@app.route('/api/cafes')
def api_cafes():
    return jsonify(load_cafes())

if __name__ == '__main__':
    read_json(CAFE_FILE, [])
    read_json(USERS_FILE, [])
    read_json(ADMIN_FILE, [])
    app.run(debug=True)