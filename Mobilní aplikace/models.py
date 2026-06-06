from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class Pozadavek(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    jmeno = db.Column(db.String(100), nullable=False)
    pozice = db.Column(db.String(50), nullable=False)  # MANAGER, PIT BOSS, KRUPIÉR
    datum = db.Column(db.Date, nullable=False)
    typ_pozadavku = db.Column(db.String(20), nullable=False)  # WDO, Dovolená, atd.
    poznamka = db.Column(db.Text, nullable=True)
    stav = db.Column(db.String, default='ceka')  # Zde nahrazujeme vyrizeno! Hodnoty: ceka, schvaleno, zamitnuto
    admin_poznamka = db.Column(db.String, nullable=True)  # Nové políčko pro důvod odmítnutívyrizeno = db.Column(db.Boolean, default=False)  # False = čeká, True = vyřízeno manažerem


class Uzivatel(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    uzivatelske_jmeno = db.Column(db.String(50), unique=True, nullable=False)
    heslo_hash = db.Column(db.String(255), nullable=False)
    
    # REÁLNÉ JMÉNO: Musí se přesně shodovat s textem v Google Tabulce!
    realne_jmeno = db.Column(db.String(100), nullable=False)
    
    # ROLE: MANAGER, PIT_BOSS, KRUPIÉR
    role = db.Column(db.String(20), nullable=False, default="KRUPIÉR")

    # Pomocné funkce pro bezpečné uložení hesla
    def nastav_heslo(self, heslo):
        self.heslo_hash = generate_password_hash(heslo)

    def zkontroluj_heslo(self, heslo):
        return check_password_hash(self.heslo_hash, heslo)