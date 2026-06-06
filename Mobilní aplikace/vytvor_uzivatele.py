from app import app, db, Uzivatel

with app.app_context():
    # Vytvoření tabulek, pokud neexistují
    db.create_all()

    # Seznam zaměstnanců (Uživatelské jméno, Reálné jméno do Excelu, Role)
    zamestnanci = [
        ("martin", "Martin Sedlář", "MANAGER"),
        ("mirek", "Mirek Štuk", "MANAGER"),
        ("michal", "Michal Pekhart", "PIT BOSS"),
        ("marek", "Marek Adamec", "KRUPIÉR"),
        ("michal", "Michal Jarošek", "KRUPIÉR"),
        ("tomas", "Tomáš Kliment", "KRUPIÉR"),
        ("jana", "Jana Valehrachová", "KRUPIÉR"),
        ("david", "David Škrob", "KRUPIÉR"),
        ("valerie", "Valerie Volková", "KRUPIÉR"),
        ("nikol", "Nikol Stávková", "KRUPIÉR"),
        ("lukas", "Lukáš Dudek", "KRUPIÉR"),
        ("erik", "Erik Hübner", "KRUPIÉR"),
        ("nikola", "Nikola Heroschová", "KRUPIÉR")
    ]

    for uziv_jmeno, real_jmeno, role in zamestnanci:
        # Zkontrolujeme, zda uživatel už neexistuje
        existuje = Uzivatel.query.filter_by(uzivatelske_jmeno=uziv_jmeno).first()
        if not existuje:
            novy = Uzivatel(uzivatelske_jmeno=uziv_jmeno, realne_jmeno=real_jmeno, role=role)
            novy.nastav_heslo("Casino2026") # Výchozí startovní heslo pro všechny
            db.session.add(novy)
            print(f"Uživatel {uziv_jmeno} byl vytvořen s výchozím heslem.")

    db.session.commit()
    print("Všichni uživatelé byli úspěšně uloženi do databáze!")