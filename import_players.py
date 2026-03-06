import csv
import os
import sys
from app import app, db, Player


def import_players(csv_path: str) -> None:
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f'CSV file not found: {csv_path}')

    inserted = 0
    updated = 0

    with app.app_context():
        db.create_all()

        with open(csv_path, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            required_columns = {'name', 'team', 'role', 'strike_rate', 'photo_url'}
            missing = required_columns - set(reader.fieldnames or [])
            if missing:
                raise ValueError(f'Missing required columns: {", ".join(sorted(missing))}')

            for row in reader:
                name = row['name'].strip()
                team = row['team'].strip()
                role = row['role'].strip()
                strike_rate = float(row['strike_rate'])
                photo_url = row['photo_url'].strip()

                player = Player.query.filter_by(name=name, team=team).first()
                if player:
                    player.role = role
                    player.strike_rate = strike_rate
                    player.photo_url = photo_url
                    updated += 1
                else:
                    db.session.add(Player(
                        name=name,
                        team=team,
                        role=role,
                        strike_rate=strike_rate,
                        photo_url=photo_url,
                    ))
                    inserted += 1

        db.session.commit()
        print(f'Import complete. Inserted: {inserted}, Updated: {updated}')


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: python import_players.py players.csv')
        sys.exit(1)

    import_players(sys.argv[1])
