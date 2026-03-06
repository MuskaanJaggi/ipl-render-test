import csv
import os
import sys
from pathlib import Path

from flask import Flask
from flask_sqlalchemy import SQLAlchemy

BASE_DIR = Path(__file__).resolve().parent

app = Flask(__name__)
raw_db_url = os.environ.get("DATABASE_URL", f"sqlite:///{BASE_DIR / 'auction.db'}")
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


def import_players(csv_path: str) -> None:
    with app.app_context():
        db.create_all()

        with open(csv_path, newline="", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            count = 0
            for row in reader:
                name = (row.get("name") or "").strip()
                team = (row.get("team") or "").strip()
                role = (row.get("role") or "").strip()
                strike_rate = row.get("strike_rate")
                photo_url = (row.get("photo_url") or "").strip()

                if not name or not team or not role or not strike_rate:
                    continue

                existing = Player.query.filter_by(name=name, team=team).first()
                if existing:
                    existing.role = role
                    existing.strike_rate = float(strike_rate)
                    existing.photo_url = photo_url
                else:
                    db.session.add(
                        Player(
                            name=name,
                            team=team,
                            role=role,
                            strike_rate=float(strike_rate),
                            photo_url=photo_url,
                        )
                    )
                count += 1

            db.session.commit()
            print(f"Imported or updated {count} player rows.")


if __name__ == "__main__":
    csv_file = sys.argv[1] if len(sys.argv) > 1 else str(BASE_DIR / "players.csv")
    import_players(csv_file)
