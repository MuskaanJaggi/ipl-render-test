# IPL Auction App

A simple Flask + PostgreSQL auction app for IPL players.

## Features
- View player cards with photo, team, role, strike rate, and current highest bid
- Filter by player name, team, role, and strike rate range
- Bid validation so every new bid must be greater than the current highest bid
- PostgreSQL-ready for Render deployment

## Local setup
1. Create a virtual environment
2. Install dependencies: `pip install -r requirements.txt`
3. Set `DATABASE_URL` in your environment or let the app use local SQLite for testing
4. Run: `python app.py`

## Render setup
- Create a Render Postgres database
- Add its `DATABASE_URL` to your web service environment variables
- Deploy the app using the included `Procfile`
