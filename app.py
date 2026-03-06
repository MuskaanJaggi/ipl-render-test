import os
from datetime import datetime
from functools import wraps

from flask import Flask, jsonify, redirect, request, send_from_directory, session, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__, static_folder=None)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-secret-key-on-render")

raw_db_url = os.environ.get("DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'auction.db')}")
if raw_db_url.startswith("postgres://"):
    raw_db_url = raw_db_url.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = raw_db_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


class Player(db.Model):
    __tablename__ = "players"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    team = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(100), nullable=False)
    strike_rate = db.Column(db.Float, nullable=False)
    photo_url = db.Column(db.Text, nullable=True)

    bids = db.relationship("Bid", backref="player", lazy=True, cascade="all, delete-orphan")


class Bid(db.Model):
    __tablename__ = "bids"

    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey("players.id"), nullable=False)
    bidder_name = db.Column(db.String(120), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class AppUser(db.Model):
    __tablename__ = "app_users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


def login_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            if request.path.startswith("/api/"):
                return jsonify({"error": "Unauthorized"}), 401
            return redirect(url_for("login_page"))
        return view_func(*args, **kwargs)

    return wrapper


def bootstrap_default_user() -> None:
    username = os.environ.get("ADMIN_USERNAME", "admin")
    password = os.environ.get("ADMIN_PASSWORD", "admin123")

    existing_user = AppUser.query.filter(func.lower(AppUser.username) == username.lower()).first()
    if existing_user:
        return

    db.session.add(
        AppUser(username=username, password_hash=generate_password_hash(password))
    )
    db.session.commit()


def seed_players_if_empty() -> None:
    if Player.query.count() > 0:
        return

    demo_players = [
        {
            "name": "Virat Kohli",
            "team": "RCB",
            "role": "Batter",
            "strike_rate": 144.25,
            "photo_url": "https://images.unsplash.com/photo-1517466787929-bc90951d0974?auto=format&fit=crop&w=900&q=80",
        },
        {
            "name": "MS Dhoni",
            "team": "CSK",
            "role": "Wicketkeeper",
            "strike_rate": 135.60,
            "photo_url": "https://images.unsplash.com/photo-1547347298-4074fc3086f0?auto=format&fit=crop&w=900&q=80",
        },
        {
            "name": "Andre Russell",
            "team": "KKR",
            "role": "All-rounder",
            "strike_rate": 174.92,
            "photo_url": "https://images.unsplash.com/photo-1521412644187-c49fa049e84d?auto=format&fit=crop&w=900&q=80",
        },
        {
            "name": "Jasprit Bumrah",
            "team": "MI",
            "role": "Bowler",
            "strike_rate": 95.00,
            "photo_url": "https://images.unsplash.com/photo-1579952363873-27f3bade9f55?auto=format&fit=crop&w=900&q=80",
        },
        {
            "name": "KL Rahul",
            "team": "DC",
            "role": "Wicketkeeper",
            "strike_rate": 134.61,
            "photo_url": "https://images.unsplash.com/photo-1541252260730-0412e8e2108e?auto=format&fit=crop&w=900&q=80",
        },
        {
            "name": "Ruturaj Gaikwad",
            "team": "CSK",
            "role": "Batter",
            "strike_rate": 136.15,
            "photo_url": "https://images.unsplash.com/photo-1519766304817-4f37bda74a26?auto=format&fit=crop&w=900&q=80",
        },
        {
            "name": "Suryakumar Yadav",
            "team": "MI",
            "role": "Batter",
            "strike_rate": 171.55,
            "photo_url": "https://images.unsplash.com/photo-1505253758473-96b7015fcd40?auto=format&fit=crop&w=900&q=80",
        },
        {
            "name": "Ravindra Jadeja",
            "team": "CSK",
            "role": "All-rounder",
            "strike_rate": 131.42,
            "photo_url": "https://images.unsplash.com/photo-1508098682722-e99c643e7485?auto=format&fit=crop&w=900&q=80",
        },
    ]

    for item in demo_players:
        db.session.add(Player(**item))

    db.session.commit()


def current_highest_bid(player_id: int):
    return db.session.query(func.max(Bid.amount)).filter(Bid.player_id == player_id).scalar() or 0.0


@app.before_request
def ensure_tables_and_defaults():
    db.create_all()
    bootstrap_default_user()
    seed_players_if_empty()


@app.route("/")
def home():
    if session.get("user_id"):
        return send_from_directory(BASE_DIR, "app.html")
    return redirect(url_for("login_page"))


@app.route("/login", methods=["GET", "POST"])
def login_page():
    if request.method == "GET":
        if session.get("user_id"):
            return redirect(url_for("home"))
        return send_from_directory(BASE_DIR, "login.html")

    username = (request.form.get("username") or "").strip()
    password = request.form.get("password") or ""

    user = AppUser.query.filter(func.lower(AppUser.username) == username.lower()).first()
    if not user or not check_password_hash(user.password_hash, password):
        return redirect(url_for("login_page", error="invalid"))

    session["user_id"] = user.id
    session["username"] = user.username
    return redirect(url_for("home"))


@app.route("/logout", methods=["POST"])
@login_required
def logout():
    session.clear()
    return redirect(url_for("login_page"))


@app.route("/api/me")
@login_required
def api_me():
    return jsonify({"username": session.get("username")})


@app.route("/api/players")
@login_required
def get_players():
    search = (request.args.get("search") or "").strip().lower()
    team = (request.args.get("team") or "").strip()
    role = (request.args.get("role") or "").strip()
    sort = (request.args.get("sort") or "name_asc").strip()

    min_sr_raw = request.args.get("min_sr")
    max_sr_raw = request.args.get("max_sr")

    query = Player.query

    if search:
        query = query.filter(Player.name.ilike(f"%{search}%"))
    if team:
        query = query.filter(Player.team == team)
    if role:
        query = query.filter(Player.role == role)

    try:
        if min_sr_raw:
            query = query.filter(Player.strike_rate >= float(min_sr_raw))
        if max_sr_raw:
            query = query.filter(Player.strike_rate <= float(max_sr_raw))
    except ValueError:
        return jsonify({"error": "Strike rate filter must be numeric."}), 400

    if sort == "name_desc":
        query = query.order_by(Player.name.desc())
    elif sort == "sr_asc":
        query = query.order_by(Player.strike_rate.asc())
    elif sort == "sr_desc":
        query = query.order_by(Player.strike_rate.desc())
    else:
        query = query.order_by(Player.name.asc())

    players = query.all()
    payload = []
    for player in players:
        payload.append(
            {
                "id": player.id,
                "name": player.name,
                "team": player.team,
                "role": player.role,
                "strike_rate": player.strike_rate,
                "photo_url": player.photo_url,
                "current_highest_bid": current_highest_bid(player.id),
            }
        )

    teams = [row[0] for row in db.session.query(Player.team).distinct().order_by(Player.team).all()]
    roles = [row[0] for row in db.session.query(Player.role).distinct().order_by(Player.role).all()]

    return jsonify({"players": payload, "teams": teams, "roles": roles})


@app.route("/api/bid", methods=["POST"])
@login_required
def place_bid():
    data = request.get_json(silent=True) or {}

    player_id = data.get("player_id")
    amount = data.get("amount")

    if not player_id or amount is None:
        return jsonify({"error": "player_id and amount are required."}), 400

    try:
        amount = float(amount)
    except (TypeError, ValueError):
        return jsonify({"error": "Bid amount must be numeric."}), 400

    if amount <= 0:
        return jsonify({"error": "Bid amount must be greater than zero."}), 400

    player = Player.query.get(player_id)
    if not player:
        return jsonify({"error": "Player not found."}), 404

    highest_bid = current_highest_bid(player.id)
    if amount <= highest_bid:
        return jsonify(
            {"error": f"Bid must be higher than the current highest bid of ₹{highest_bid:,.0f}."}
        ), 400

    bid = Bid(
        player_id=player.id,
        bidder_name=session.get("username", "Unknown"),
        amount=amount,
    )
    db.session.add(bid)
    db.session.commit()

    return jsonify(
        {
            "message": f"Bid placed successfully for {player.name}.",
            "current_highest_bid": amount,
            "bidder_name": session.get("username"),
        }
    )


@app.route("/api/bids/<int:player_id>")
@login_required
def bid_history(player_id: int):
    player = Player.query.get(player_id)
    if not player:
        return jsonify({"error": "Player not found."}), 404

    bids = (
        Bid.query.filter_by(player_id=player_id)
        .order_by(Bid.amount.desc(), Bid.created_at.desc())
        .limit(10)
        .all()
    )

    return jsonify(
        {
            "player": player.name,
            "bids": [
                {
                    "bidder_name": bid.bidder_name,
                    "amount": bid.amount,
                    "created_at": bid.created_at.strftime("%Y-%m-%d %H:%M:%S UTC"),
                }
                for bid in bids
            ],
        }
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
