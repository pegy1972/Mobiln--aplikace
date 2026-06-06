from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from datetime import date, datetime
import gspread
from gspread.utils import rowcol_to_a1
from google.oauth2.service_account import Credentials
import os
import time  
import calendar


# IMPORT VAŠÍ FUNKCE
from models import db, Uzivatel, Pozadavek
from google_sheets import nacist_smeny_pro_uzivatele, client

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_PATH = os.path.join(BASE_DIR, 'databaze.db')


app = Flask(__name__)
database_url = os.environ.get('DATABASE_URL', f'sqlite:///{DATABASE_PATH}')
if database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)

app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-me')
app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# Inicializace Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login' # Kam přesměrovat uživatele, pokud není přihlášen

# Funkce, která podle ID najde uživatele v databázi (vyžaduje Flask-Login)
@login_manager.user_loader
def load_user(user_id):
    return Uzivatel.query.get(int(user_id))

# --- ROUTY PRO PŘIHLÁŠENÍ A ODHLÁŠENÍ ---

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        jmeno = request.form.get('username')
        heslo = request.form.get('password')
        
        uzivatel = Uzivatel.query.filter_by(uzivatelske_jmeno=jmeno).first()
        
        if uzivatel and uzivatel.zkontroluj_heslo(heslo):
            login_user(uzivatel)
            flash('Úspěšně přihlášen!', 'success')
            
            # 🟢 TADY JE TA ZMĚNA: Smazali jsme podmínku pro managera.
            # Teď úplně všichni (vy i krupiéři) jdou na stejnou adresu: /muj-kalendar
            return redirect(url_for('muj_kalendar'))
            
        flash('Nesprávné jméno nebo heslo.', 'danger')
        
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Byl jsi odhlášen.', 'info')
    return redirect(url_for('login'))

@app.route('/zmena-hesla', methods=['GET', 'POST'])
@login_required
def zmena_hesla():
    if request.method == 'POST':
        stare_heslo = request.form.get('stare_heslo')
        nove_heslo = request.form.get('nove_heslo')
        potvrzeni_hesla = request.form.get('potvrzeni_heslo')

        # 1. Kontrola, zda zadal správně současné heslo
        if not current_user.zkontroluj_heslo(stare_heslo):
            flash('Nesprávné současné heslo!', 'danger')
            return redirect(url_for('zmena_hesla'))

        # 2. Kontrola, zda se nová hesla shodují
        if nove_heslo != potvrzeni_hesla:
            flash('Nová hesla se neshodují!', 'danger')
            return redirect(url_for('zmena_hesla'))
        
        # 3. Kontrola délky hesla (např. minimálně 6 znaků)
        if len(nove_heslo) < 6:
            flash('Nové heslo musí mít alespoň 6 znaků.', 'danger')
            return redirect(url_for('zmena_hesla'))

        # 4. Uložení nového zašifrovaného hesla
        current_user.nastav_heslo(nove_heslo)
        db.session.commit()

        flash('Heslo bylo úspěšně změněno!', 'success')
        return redirect(url_for('muj_kalendar'))

    return render_template('zmena_hesla.html')


@app.route('/muj-kalendar')
@login_required
def muj_kalendar():
    # 1. Definujeme seznam všech dostupných měsíců (musí sedět s názvy listů v Excelu)
    seznam_mesicu = [
        "LEDEN", "ÚNOR", "BŘEZEN", "DUBEN", "KVĚTEN", "ČERVEN", 
        "ČERVENEC", "SRPEN", "ZÁŘÍ", "ŘÍJEN", "LISTOPAD", "PROSINEC"
    ]
    
    # Pomocný slovník pro určení aktuálního měsíce podle reálného času
    mapovani_mesicu = {
        1: "LEDEN", 2: "ÚNOR", 3: "BŘEZEN", 4: "DUBEN", 5: "KVĚTEN", 6: "ČERVEN",
        7: "ČERVENEC", 8: "SRPEN", 9: "ZÁŘÍ", 10: "ŘÍJEN", 11: "LISTOPAD", 12: "PROSINEC"
    }
    # Převodník názvu měsíce na číslo (pokud v proměnné 'mesic' máte text, např. 'ČERVEN')
    nazvy_mesicu_map = {
        'LEDEN': 1, 'ÚNOR': 2, 'BŘEZEN': 3, 'DUBEN': 4, 'KVĚTEN': 5, 'ČERVEN': 6,
        'ČERVENEC': 7, 'SRPEN': 8, 'ZÁŘÍ': 9, 'ŘÍJEN': 10, 'LISTOPAD': 11, 'PROSINEC': 12
    }

    # Zjistíme aktuální měsíc jako výchozí
    aktualni_mesic_id = date.today().month
    vychozi_mesic = mapovani_mesicu.get(aktualni_mesic_id, "LEDEN")
    
    # 2. POKUD uživatel kliknul na jiný měsíc, vezmeme ho z URL adresy (?mesic=ČERVEN)
    vybrany_mesic = request.args.get('mesic', vychozi_mesic)

     # Zjistíme číslo měsíce (pokud proměnná 'mesic' obsahuje už číslo 1-12, dosadíte přímo ji)
    cislo_mesice = nazvy_mesicu_map.get(vybrany_mesic.upper(), 1)
    
    # calendar.monthrange(rok, mesic)[1] nám vrátí přesný počet dní (např. pro červen vrátí 30, pro únor 28)
    skutecny_pocet_dni = calendar.monthrange(2026, cislo_mesice)[1]
    
    # 3. Načteme směny z Google Sheets pro vybraný měsíc
    osobni_smeny = nacist_smeny_pro_uzivatele(current_user.realne_jmeno, vybrany_mesic)

    osobni_smeny = osobni_smeny[:skutecny_pocet_dni]  # Ořízneme seznam směn na skutečný počet dní v měsíci
    
    # 4. Načteme z databáze všechny požadavky tohoto konkrétního zaměstnance
    # Seřadíme je od nejnovějších
    moje_historie_pozadavků = Pozadavek.query.filter_by(jmeno=current_user.realne_jmeno).order_by(Pozadavek.datum.desc()).all()

    dnes = date.today()  # Pro porovnávání datumu směny s dneškem (pro zobrazení pouze budoucích požadavků)

    # Převedeme číslo měsíce na velká písmena, aby to přesně sedělo s vaším selectem
    seznam_mesicu = ['LEDEN', 'ÚNOR', 'BŘEZEN', 'DUBEN', 'KVĚTEN', 'ČERVEN', 'ČERVENEC', 'SRPEN', 'ZÁŘÍ', 'ŘÍJEN', 'LISTOPAD', 'PROSINEC']
    dnes_mesic_text = seznam_mesicu[dnes.month - 1]
    

    # 🟢 PROPOJENÍ: Pokud je to manager, načteme aktivní čekající požadavky stejně jako v adminu
    ostatni_pozadavky = []
    if current_user.role == 'PIT BOSS':
        ostatni_pozadavky = Pozadavek.query.filter_by(stav='ceka').order_by(Pozadavek.datum.asc()).all()

    # 🟢 NOVÉ PROMĚNNÉ PRO DNEŠNÍ PŘEHLED CHODU KASINA
    v_praci_dnes = []
    na_dovolene_dnes = []
    ostatni_pozadavky = []

    if current_user.role == 'MANAGER' or current_user.role == 'PIT BOSS':
        # 1. Načtení čekajících požadavků (to už máme z minula)
        ostatni_pozadavky = Pozadavek.query.filter_by(stav='ceka').order_by(Pozadavek.datum.asc()).all()

    # 2. 🟢 NOVINKA: Načtení dnešní docházky všech zaměstnanců z Excelu
        try:
            sheet = client.open("Směny 2026").worksheet(dnes_mesic_text)
            vsechna_data = sheet.get_all_values() # Načte celou tabulku naráz
            
            # Jméno je v 1. sloupci (index 0). 
            # Den 1 je ve 2. sloupci (index 1), takže dnešní den odpovídá přesně svému číslu indexu!
            index_dne = dnes.day

            # Projdeme řádky od druhého řádku dál (vynecháme záhlaví s čísly dní)
            for radek in vsechna_data[1:]:
                if not radek or not radek[0].strip():
                    continue # Přeskočit prázdné řádky
                
                jmeno_zamestnance = radek[0]

                # 🟢 TOHLE JE TA PODMÍNKA: Pokud se jméno na řádku shoduje s vaším reálným jménem, 
                # příkaz 'continue' tento řádek úplně přeskočí a jde se na dalšího člověka.
                if jmeno_zamestnance == current_user.realne_jmeno:
                    continue
                
                # Pojistka, pokud by řádek neměl dostatek sloupců
                kod_dnes = radek[index_dne].strip() if len(radek) > index_dne else ""

                # Rozřazení podle vašich zkratek
                if kod_dnes in ['N', 'O', 'Nc', 'oNc', 'wdo', 'WDO', 'wd1', 'wd2', 'wd3', 'wd4', 'wd5']:
                    v_praci_dnes.append({'jmeno': jmeno_zamestnance, 'kod': kod_dnes})
                elif kod_dnes in ['H', 'H/N', 'N/H', 'S']:
                    na_dovolene_dnes.append({'jmeno': jmeno_zamestnance, 'kod': kod_dnes})
                    
        except Exception as e:
            print(f"Chyba při načítání dnešního přehledu: {e}")

    # --- KONEC ROZŠÍŘENÍ ---


    # Všechna data pošleme do HTML šablony
    return render_template(
        'kalendar.html', 
        smeny=osobni_smeny, 
        mesic=vybrany_mesic, 
        mesice=seznam_mesicu,             # Seznam pro dropdown
        pozadavky=moje_historie_pozadavků, # Historie s rozlišením schváleno/neobsazeno
        dnes_den=dnes.day,        # např. 2
        dnes_mesic_jmeno=dnes_mesic_text,    # např. "ČERVEN" (pro zobrazení v dropdownu a pro porovnávání s vybraným měsícem)
        ostatni_pozadavky=ostatni_pozadavky,  # 🟢 Pro manažera: seznam všech čekajících požadavků ostatních zaměstnanců
        v_praci_dnes=v_praci_dnes,  # 🟢 Dnešní přehled: zaměstnanci v práci
        na_dovolene_dnes=na_dovolene_dnes   # 🟢 Dnešní přehled: zaměstnanci na dovolené
    )


@app.route('/novy-pozadavek', methods=['POST'])
@login_required
def novy_pozadavek():
    r_raw = request.form.get('radek')
    s_raw = request.form.get('sloupec')
    nazev_mesice = request.form.get('mesic')
    text_komentare = request.form.get('poznamka')
    datum_smeny_str = request.form.get('datum')
    typ_pozadavku = request.form.get('typ_pozadavku')
    
 
    if not r_raw or not s_raw or r_raw == "" or s_raw == "":
        flash("Chyba: Nepodařilo se určit souřadnice buňky (řádek nebo sloupec je prázdný).", "danger")
        return redirect(url_for('muj_kalendar'))
 
    radek = int(r_raw)
    sloupec = int(s_raw)
    poznamka = request.form.get('poznamka')

    # 🟢 POJIŠTĚNÍ: Pokud je poznamka None, uděláme z ní prázdný řetězec ""
    if not poznamka:
        poznamka = ""

    # Případně můžete poznámku pro Excel poskládat tak, aby tam admin 
    # viděl typ požadavku, i když zaměstnanec nic nenapsal:
    text_do_excelu = f"{typ_pozadavku} - {poznamka}".strip(" - ")
    
    # Pojistka: Odstraníme případné nechtěné mezery okolo názvu měsíce
    if nazev_mesice:
            nazev_mesice = nazev_mesice.strip()
    
    # 🟢 OŠETŘENÍ CHYBY: Zkusíme otevřít list, a pokud neexistuje, vypíšeme chybu na webu
    try:
        sheet = client.open("Směny 2026").worksheet(nazev_mesice)
    except gspread.exceptions.WorksheetNotFound:
        # Tímto zjistíme, co přesně se HTML snaží Pythonu vnutit za název
        flash(f"Chyba: V Google tabulce neexistuje záložka s názvem '{nazev_mesice}'. Zkontrolujte velká/malá písmena a diakritiku.", "danger")
        return redirect(url_for('muj_kalendar'))
    
    # Pokud list existuje, pokračujeme zápisem poznámky
    bunka_a1 = rowcol_to_a1(radek, sloupec)
    sheet.insert_note(bunka_a1, text_do_excelu)

    # --- 2. 🟢 NOVÉ: ZÁPIS DO DATABÁZE (pro Admina a Historii) ---
    try:
        # Převedeme textové datum na čistý objekt typu 'date' (vyžadováno db.Date)
        if datum_smeny_str:
            datum_pro_db = datetime.strptime(datum_smeny_str, "%Y-%m-%d").date()
        else:
            datum_pro_db = date.today()

        # Vytvoření záznamu přesně podle sloupců vaší třídy Pozadavek
        novy_pozadavek_db = Pozadavek(
            jmeno=current_user.realne_jmeno,
            pozice=current_user.role,       # <--- Bere pozici přihlášeného (KRUPIÉR, PIT BOSS...)
            datum=datum_pro_db,               # <--- Čisté datum dne, ke kterému se požadavek váže
            typ_pozadavku=typ_pozadavku,       # <--- WDO / Dovolená / Volno
            poznamka=text_komentare,           # <--- Textová poznámka (může být i prázdná)
            stav='ceka'            # <--- Výchozí stav: Čeká na manažera
        )
        
        db.session.add(novy_pozadavek_db)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        flash(f"Poznámka do Excelu zapsána, ale nepodařilo se uložit do DB: {e}", "warning")
        return redirect(url_for('muj_kalendar', mesic=nazev_mesice))
    
    flash("Váš požadavek byl úspěšně zapsán.", "success")
    return redirect(url_for('muj_kalendar'))

# app.py
@app.route('/admin/pozadavky')
@login_required
def admin_pozadavky():
    # BEZPEČNOST: Do adminu pustíme jen uživatele, který má v databázi roli MANAGER
    if current_user.role != 'PIT BOSS':
        flash('Sem nemáš přístup! Tato sekce je pouze pro manažery.', 'danger')
        return redirect(url_for('muj_kalendar'))
    
    # Načteme z databáze všechny požadavky, které mají vyrizeno = False
    # Seřadíme je podle data od nejbližšího
    aktivni_pozadavky = Pozadavek.query.filter_by(stav='ceka').order_by(Pozadavek.datum.asc()).all()
    
    # Teď už data správně předáme do HTML šablony
    return render_template('admin.html', pozadavky=aktivni_pozadavky)


@app.route('/admin-vyridit-pozadavek', methods=['POST'])
@login_required
def admin_vyridit_pozadavek():
    if current_user.role != 'PIT BOSS':
        return "Přístup odepřen. Nejste manažer.", 403
    
    pozadavek_id = request.form.get('pozadavek_id')
    akce = request.form.get('akce')
    admin_poznamka = request.form.get('admin_poznamka', '').strip()
 
    # 1. Načteme požadavek z DB
    pozadavek = Pozadavek.query.get(pozadavek_id)
    if not pozadavek:
        flash("Požadavek nebyl nalezen.", "danger")
        return redirect('/admin/pozadavky') # <--- upravte případně podle vaší admin url
    
    # 2. 🟢 SPOLEČNÁ ČÁST: Vyhledání buňky v Google Tabulce
    # Potřebujeme ji pro schválení (zápis směny) i pro odmítnutí (smazání indikačního růžku/poznámky)
    seznam_mesicu = ['LEDEN', 'ÚNOR', 'BŘEZEN', 'DUBEN', 'KVĚTEN', 'ČERVEN', 'ČERVENEC', 'SRPEN', 'ZÁŘÍ', 'ŘÍJEN', 'LISTOPAD', 'PROSINEC']
    nazev_mesice = seznam_mesicu[pozadavek.datum.month - 1]
 
    try:
        sheet = client.open("Směny 2026").worksheet(nazev_mesice)
        
        # Automatické vyhledání řádku podle jména zaměstnance v 1. sloupci
        jmena_v_tabulce = sheet.col_values(1)
        radek = jmena_v_tabulce.index(pozadavek.jmeno) + 1
        
        # Automatické určení sloupce (den + 1)
        sloupec = pozadavek.datum.day + 1
        
        # Definice buňky v A1 formátu (např. "B5")
        bunka_a1 = rowcol_to_a1(radek, sloupec)
        
    except gspread.exceptions.WorksheetNotFound:
        flash(f"Chyba: V Excelu neexistuje list {nazev_mesice}.", "danger")
        return redirect('muj_kalendar')  # <--- Zde můžete upravit, kam chcete uživatele poslat v případě chyby
    except ValueError:
        flash(f"Chyba: Zaměstnanec '{pozadavek.jmeno}' nebyl v listu {nazev_mesice} nalezen.", "danger")
        return redirect('muj_kalendar')  # <--- Zde můžete upravit, kam chcete uživatele poslat v případě chyby

    # Nyní máme bezpečně připravený 'sheet' i 'bunka_a1' pro obě varianty!

    # 3. 🟢 ROZCESTNÍK PODLE STISKNUTÉHO TLAČÍTKA
    if akce == 'schvalit':
        pozadavek.stav = 'schvaleno'  # Malými písmeny, aby to odpovídalo podmínce v kalendáři
        pozadavek.admin_poznamka = None  # Při schválení poznámku nepotřebujeme
 
        # Převodník textu na zkratky do tabulky
        převodník_zkratek = {
            'Dovolená': 'H',
            'WDO': 'wdo',
            'Volno': 'V',     
            'Jiné': 'X'       
        }
        zkratka_do_tabulky = převodník_zkratek.get(pozadavek.typ_pozadavku, pozadavek.typ_pozadavku)
        
        # Zápis zkratky do Excelu
        time.sleep(1.5)  # Ochrana proti API limitům (chyba 10054)
        sheet.update_acell(bunka_a1, zkratka_do_tabulky)
        
        # Odstranění původní poznámky (růžku), kterou tam zaměstnanec vytvořil
        time.sleep(1.5)
        sheet.insert_note(bunka_a1, "") 
        
        flash(f"Požadavek uživatele {pozadavek.jmeno} byl schválen a zapsán jako '{zkratka_do_tabulky}'.", "success")
        
    elif akce == 'odmitnout':
        pozadavek.stav = 'zamitnuto'  # Malými písmeny pro shodu s kalendar.html
        pozadavek.admin_poznamka = admin_poznamka  # 👈 ZDE ukládáme důvod odmítnutí do DB
        
        # Při odmítnutí pouze smažeme indikační růžek (poznámku) z buňky, směnu neměníme
        time.sleep(1.5)
        sheet.insert_note(bunka_a1, "")
        
        flash(f"Požadavek uživatele {pozadavek.jmeno} byl zamítnut.", "warning")
 
    # 4. Uložení změn do databáze a přesměrování zpět na admin panel
    db.session.commit()
    return redirect('muj_kalendar')  # <--- Zde doplňte přesnou URL vašeho admin panelu

if __name__ == '__main__':
    # host='0.0.0.0' říká: "poslouchej na všech síťových kartách"
    app.run(host='0.0.0.0', debug=True, port=5000)
