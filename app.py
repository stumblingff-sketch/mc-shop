import psutil
import json
import os
from flask import Flask, render_template, redirect, url_for, request, flash, jsonify, session
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from models import db, Rank, User, VoteLink
from mcrcon import MCRcon

app = Flask(__name__)

# --- CONFIGURATION ---
app.config['SECRET_KEY'] = 'secretkey123_change_this_later'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///shop.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# ==================================================
# 🛡️ SECURITY: ADMIN LIST
# REPLACE THESE EMAILS WITH YOUR OWN!
# ==================================================
ADMIN_EMAILS = [
    "your_email@gmail.com",  # <--- PUT YOUR LOGIN EMAIL HERE
    "rajveer5152@gmail.com"  # Example based on your screenshot
]

db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- CONFIG LOADER (Now sends Admin List to HTML) ---
@app.context_processor
def inject_config():
    base_dir = os.path.abspath(os.path.dirname(__file__))
    config_path = os.path.join(base_dir, 'config.json')
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
    except:
        config = {
            'server_name': 'Dora Bash',
            'logo_url': '',
            'hero_background': ''
        }
    
    # PASS THE ADMIN LIST TO ALL TEMPLATES
    return dict(config=config, admin_emails=ADMIN_EMAILS)

# --- ROUTES ---

@app.route('/')
def home():
    with app.app_context():
        db.create_all()
    featured = Rank.query.filter_by(category='rank').order_by(Rank.price.desc()).limit(3).all()
    recent_payments = []
    return render_template('index.html', featured=featured, recent=recent_payments)

@app.route('/shop')
def shop():
    ranks = Rank.query.filter_by(category='rank').all()
    coins = Rank.query.filter_by(category='coin').all()
    tags = Rank.query.filter_by(category='tag').all()
    return render_template('shop.html', ranks=ranks, coins=coins, tags=tags)

@app.route('/rules')
def rules():
    return render_template('rules.html')

@app.route('/vote')
def vote():
    links = VoteLink.query.all()
    return render_template('vote.html', links=links)

# --- CART ---
@app.route('/add_to_cart/<int:id>')
@login_required
def add_to_cart(id):
    item = Rank.query.get_or_404(id)
    cart = session.get('cart', [])
    cart.append(item.id)
    session['cart'] = cart
    flash(f'"{item.name}" added!', 'success')
    return redirect(url_for('shop'))

@app.route('/cart')
@login_required
def view_cart():
    cart_ids = session.get('cart', [])
    cart_items = Rank.query.filter(Rank.id.in_(cart_ids)).all()
    total = sum(item.price for item in cart_items)
    return render_template('cart.html', cart_items=cart_items, total=total)

@app.route('/remove_from_cart/<int:id>')
@login_required
def remove_from_cart(id):
    cart = session.get('cart', [])
    if id in cart:
        cart.remove(id)
        session['cart'] = cart
    return redirect(url_for('view_cart'))

@app.route('/clear_cart')
@login_required
def clear_cart():
    session['cart'] = []
    return redirect(url_for('view_cart'))

# --- AUTHENTICATION ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            login_user(user)
            # Redirect Admins to Dashboard, Users to Home
            if user.email in ADMIN_EMAILS: 
                return redirect(url_for('admin_panel'))
            return redirect(url_for('home'))
        else:
            flash('Invalid Username or Password', 'error')
    return render_template('auth.html', mode='login')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        username = request.form.get('username')
        ingame = request.form.get('ingame_name')
        password = request.form.get('password')

        if User.query.filter_by(email=email).first():
            flash('Email already exists.', 'error')
            return render_template('auth.html', mode='register')

        new_user = User(email=email, username=username, ingame_name=ingame, password=generate_password_hash(password))
        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)
        return redirect(url_for('home'))
    return render_template('auth.html', mode='register')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

# ==========================================
# 🛡️ SECURE ADMIN ROUTES
# ==========================================

@app.route('/admin', methods=['GET', 'POST'])
@login_required
def admin_panel():
    # SECURITY CHECK: Kick out if not admin
    if current_user.email not in ADMIN_EMAILS:
        return redirect(url_for('home'))

    if request.method == 'POST':
        form_type = request.form.get('form_type')
        if form_type == 'product':
            new_item = Rank(
                name=request.form.get('name'),
                price=float(request.form.get('price')),
                description=request.form.get('description'),
                image_url=request.form.get('image_url'),
                color_hex=request.form.get('color_hex'),
                category=request.form.get('category')
            )
            db.session.add(new_item)
            db.session.commit()
        elif form_type == 'vote':
            new_link = VoteLink(
                site_name=request.form.get('site_name'),
                link_url=request.form.get('link_url'),
                reward_desc=request.form.get('reward_desc')
            )
            db.session.add(new_link)
            db.session.commit()
        return redirect('/admin')

    try:
        cpu = psutil.cpu_percent()
        ram = psutil.virtual_memory().percent
    except:
        cpu = 0; ram = 0
    
    all_ranks = Rank.query.all()
    vote_links = VoteLink.query.all()
    return render_template('admin.html', cpu_usage=cpu, ram_usage=ram, ranks=all_ranks, vote_links=vote_links, total_items=len(all_ranks))

@app.route('/api/stats')
@login_required
def get_stats():
    if current_user.email not in ADMIN_EMAILS: return jsonify({'error': 'Unauthorized'}), 403
    return jsonify({'cpu': psutil.cpu_percent(interval=None), 'ram': psutil.virtual_memory().percent})

@app.route('/admin/delete_rank/<int:id>')
@login_required
def delete_rank(id):
    if current_user.email not in ADMIN_EMAILS: return redirect(url_for('home'))
    item = Rank.query.get_or_404(id)
    db.session.delete(item)
    db.session.commit()
    return redirect('/admin')

@app.route('/admin/delete_vote/<int:id>')
@login_required
def delete_vote(id):
    if current_user.email not in ADMIN_EMAILS: return redirect(url_for('home'))
    link = VoteLink.query.get_or_404(id)
    db.session.delete(link)
    db.session.commit()
    return redirect('/admin')

@app.route('/admin/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_rank(id):
    if current_user.email not in ADMIN_EMAILS: return redirect(url_for('home'))
    rank = Rank.query.get_or_404(id)
    if request.method == 'POST':
        rank.name = request.form['name']
        rank.price = float(request.form['price'])
        rank.description = request.form['description']
        rank.image_url = request.form['image_url']
        rank.color_hex = request.form['color_hex']
        rank.category = request.form.get('category', 'rank')
        db.session.commit()
        return redirect('/admin')
    return render_template('edit_rank.html', rank=rank)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='0.0.0.0', port=9745)
