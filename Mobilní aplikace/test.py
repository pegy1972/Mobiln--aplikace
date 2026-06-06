from app import app
from models import db
from sqlalchemy import inspect

with app.app_context():
    insp = inspect(db.engine)
    print("Tabulky:", insp.get_table_names())

