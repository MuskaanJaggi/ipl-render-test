import os
from decimal import Decimal, InvalidOperation
from flask import Flask, jsonify, request, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__, static_folder='static')

raw_db_url = os.getenv('DATABASE_URL', f"sqlite:///{os.path.join(BASE_DIR, 'auction.db')}")
if raw_db_url.startswith('postgres://'):
    raw_db_url = raw_db_url.replace('postgres://', 'postgresql://', 1)

app.config['SQLALCHEMY_DATABASE_URI'] = raw_db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_pre_ping': True,
}

db = SQLAlchemy(app)


class Player(db.Model):
    __tablename__ = 'players'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, index=True)
    team = db.Column(db.String(80), nullable=False, index=True)
    role = db.Column(db.String(50), nullable=False)
    strike_rate = db.Column(db.Float, nullable=False)
    photo_url = db.Column(db.Text, nullable=False)

    bids = db.relationship('Bid', backref='player', lazy=True, cascade='all, delete-orphan')


class Bid(db.Model):
    __tablename__ = 'bids'

    id = db.Column(db.Integer, primary_key=True)
    player_id = db.Column(db.Integer, db.ForeignKey('players.id'), nullable=False, index=True)
    bidder_name = db.Column(db.String(120), nullable=False, default='Anonymous')
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), nullable=False)


SAMPLE_PLAYERS = [
    {
        'name': 'Virat Kohli',
        'team': 'RCB',
        'role': 'Batter',
        'strike_rate': 138.15,
        'photo_url': 'https://images.unsplash.com/photo-1546519638-68e109498ffc?auto=format&fit=crop&w=800&q=80',
    },
    {
        'name': 'Rohit Sharma',
        'team': 'MI',
        'role': 'Batter',
        'strike_rate': 131.14,
        'photo_url': 'https://images.unsplash.com/photo-1517466787929-bc90951d0974?auto=format&fit=crop&w=800&q=80',
    },
    {
        'name': 'Jasprit Bumrah',
        'team': 'MI',
        'role': 'Bowler',
        'strike_rate': 95.00,
        'photo_url': 'https://images.unsplash.com/photo-1531415074968-036ba1b575da?auto=format&fit=crop&w=800&q=80',
    },
    {
        'name': 'MS Dhoni',
        'team': 'CSK',
        'role': 'Wicketkeeper',
        'strike_rate': 135.60,
        'photo_url': 'https://images.unsplash.com/photo-1574629810360-7efbbe195018?auto=format&fit=crop&w=800&q=80',
    },
    {
        'name': 'Andre Russell',
        'team': 'KKR',
        'role': 'All-rounder',
        'strike_rate': 174.92,
        'photo_url': 'https://images.unsplash.com/photo-1517927033932-b3d18e61fb3a?auto=format&fit=crop&w=800&q=80',
    },
    {
        'name': 'Rashid Khan',
        'team': 'GT',
        'role': 'Bowler',
        'strike_rate': 162.40,
        'photo_url': 'https://images.unsplash.com/photo-1521412644187-c49fa049e84d?auto=format&fit=crop&w=800&q=80',
    },
    {
        'name': 'KL Rahul',
        'team': 'DC',
        'role': 'Wicketkeeper',
        'strike_rate': 134.61,
        'photo_url': 'https://images.unsplash.com/photo-1518604666860-9ed391f76460?auto=format&fit=crop&w=800&q=80',
    },
    {
        'name': 'Ruturaj Gaikwad',
        'team': 'CSK',
        'role': 'Batter',
        'strike_rate': 136.02,
        'photo_url': 'https://images.unsplash.com/photo-1508341591423-4347099e1f19?auto=format&fit=crop&w=800&q=80',
    },
]


def seed_players_if_empty() -> None:
    if Player.query.count() > 0:
        return

    for player_data in SAMPLE_PLAYERS:
        db.session.add(Player(**player_data))
    db.session.commit()


with app.app_context():
    db.create_all()
    seed_players_if_empty()


@app.route('/')
def index():
    return send_from_directory(BASE_DIR, 'app.html')


@app.route('/health')
def health():
    return jsonify({'status': 'ok'})


@app.route('/api/filters')
def filters():
    teams = [row[0] for row in db.session.query(Player.team).distinct().order_by(Player.team).all()]
    roles = [row[0] for row in db.session.query(Player.role).distinct().order_by(Player.role).all()]
    return jsonify({'teams': teams, 'roles': roles})


@app.route('/api/players')
def get_players():
    search = request.args.get('search', '').strip()
    team = request.args.get('team', '').strip()
    role = request.args.get('role', '').strip()
    sort = request.args.get('sort', 'name_asc').strip()

    min_sr = request.args.get('min_sr', '').strip()
    max_sr = request.args.get('max_sr', '').strip()

    query = Player.query

    if search:
        query = query.filter(Player.name.ilike(f'%{search}%'))
    if team:
        query = query.filter(Player.team == team)
    if role:
        query = query.filter(Player.role == role)
    if min_sr:
        try:
            query = query.filter(Player.strike_rate >= float(min_sr))
        except ValueError:
            pass
    if max_sr:
        try:
            query = query.filter(Player.strike_rate <= float(max_sr))
        except ValueError:
            pass

    if sort == 'sr_desc':
        query = query.order_by(Player.strike_rate.desc(), Player.name.asc())
    elif sort == 'sr_asc':
        query = query.order_by(Player.strike_rate.asc(), Player.name.asc())
    else:
        query = query.order_by(Player.name.asc())

    players = query.all()

    result = []
    for player in players:
        highest_bid = db.session.query(func.max(Bid.amount)).filter(Bid.player_id == player.id).scalar()
        result.append({
            'id': player.id,
            'name': player.name,
            'team': player.team,
            'role': player.role,
            'strike_rate': player.strike_rate,
            'photo_url': player.photo_url,
            'highest_bid': float(highest_bid) if highest_bid is not None else 0.0,
        })

    return jsonify(result)


@app.route('/api/bid/<int:player_id>', methods=['POST'])
def place_bid(player_id: int):
    player = Player.query.get_or_404(player_id)
    data = request.get_json(silent=True) or {}

    bidder_name = str(data.get('bidder_name', 'Anonymous')).strip() or 'Anonymous'
    bid_raw = str(data.get('amount', '')).strip()

    try:
        amount = Decimal(bid_raw)
    except (InvalidOperation, TypeError):
        return jsonify({'error': 'Please enter a valid bid amount.'}), 400

    if amount <= 0:
        return jsonify({'error': 'Bid amount must be greater than 0.'}), 400

    current_highest_bid = db.session.query(func.max(Bid.amount)).filter(Bid.player_id == player.id).scalar() or Decimal('0')

    if amount <= current_highest_bid:
        return jsonify({
            'error': f'Bid must be higher than the current highest bid of ₹{current_highest_bid:,.2f} for {player.name}.'
        }), 400

    bid = Bid(player_id=player.id, bidder_name=bidder_name, amount=amount)
    db.session.add(bid)
    db.session.commit()

    return jsonify({
        'message': f'Bid placed successfully for {player.name}.',
        'highest_bid': float(amount),
    }), 201


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)), debug=True)
