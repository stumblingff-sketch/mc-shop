from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy()

# --- PRODUCT MODEL (Ranks, Coins, Tags) ---
class Rank(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(255))
    image_url = db.Column(db.String(200), default="")
    color_hex = db.Column(db.String(10), default="#00bfff")
    # NEW: Category to sort items (rank, coin, tag)
    category = db.Column(db.String(50), default='rank') 

# --- VOTE LINK MODEL (New) ---
class VoteLink(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    site_name = db.Column(db.String(100), nullable=False)
    link_url = db.Column(db.String(500), nullable=False)
    reward_desc = db.Column(db.String(200), default="Vote Key")

# --- USER MODEL ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    username = db.Column(db.String(150), unique=True, nullable=False)
    ingame_name = db.Column(db.String(150), nullable=False)
    password = db.Column(db.String(200), nullable=False)