# init_db.py
from app import app
from models import db, Uzivatel
import os

with app.app_context():
    # 1. Vytvoříme prázdné tabulky v databázi podle models.py
    print("DB PATH:", os.path.abspath("databaze.db"))
    db.create_all()
    print("Datatabázové tabulky byly úspěšně vytvořeny.")

    # 2. Vytvoříme účet pro Manažera (pokud ještě neexistuje)
    if not Uzivatel.query.filter_by(uzivatelske_jmeno='admin').first():
        manager = Uzivatel(
            uzivatelske_jmeno='admin',
            realne_jmeno='Martin Sedlář',  # Musí sedět s Google Tabulkou
            role='MANAGER'
        )
        manager.nastav_heslo('admin123')
        db.session.add(manager)
        print("Uživatel 'admin' vytvořen.")

    # 3. Vytvoříme účet pro Krupiéra (pokud ještě neexistuje)
    if not Uzivatel.query.filter_by(uzivatelske_jmeno='nikola').first():
        krupier = Uzivatel(
            uzivatelske_jmeno='nikola',
            realne_jmeno='Nikola Heroschová',  # Musí sedět s Google Tabulkou
            role='KRUPIÉR'
        )
        krupier.nastav_heslo('nikola123')
        db.session.add(krupier)
        print("Uživatel 'nikola' vytvořen.")

    # 4. Uložíme změny do souboru databáze
    db.session.commit()
    print("✨ Vše je připraveno k použití!")