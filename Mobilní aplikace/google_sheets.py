import gspread
from gspread.utils import rowcol_to_a1
import os
import json
from google.oauth2.service_account import Credentials
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CREDENTIALS_PATH = os.path.join(BASE_DIR, "credentials.json")

# 🟢 TOTO VLOŽTE SEM (Globální připojení k Google Sheets)
scopes = ["https://www.googleapis.com/auth/drive", "https://www.googleapis.com/auth/spreadsheets"]
google_credentials_json = os.environ.get("GOOGLE_CREDENTIALS_JSON")
if google_credentials_json:
    creds = Credentials.from_service_account_info(json.loads(google_credentials_json), scopes=scopes)
else:
    creds = Credentials.from_service_account_file(CREDENTIALS_PATH, scopes=scopes)
client = gspread.authorize(creds)

def nacist_smeny_pro_uzivatele(realne_jmeno_uzivatele, nazev_mesice, rok=2026):
    
    # 2. Otevření tabulky a konkrétního listu
    try:
        sheet = client.open("Směny 2026").worksheet(nazev_mesice)
    except gspread.exceptions.WorksheetNotFound:
        return []

    vsechna_data = sheet.get_all_values()
    
    # NOVÉ: Načteme všechny poznámky (komentáře) z listu najednou
    try:
        vsechny_poznamky = sheet.get_all_notes()
    except Exception:
        vsechny_poznamky = {}
    
    # 3. Najdeme základní řádky s dny a názvy dnů
    radek_s_dny = vsechna_data[3] 
    radek_nazvy_dnu = vsechna_data[2]
    
    # 4. Příprava pro všechny potřebné řádky
    radek_zamestnance = None
    radek_index = None            # <--- NOVÉ: sem si uložíme reálné číslo řádku v Excelu (1-based)
    radek_mozna_dovolena = None
    radek_bude_potreba = None    
    radek_wdo_pocet = None       
    
    # NOVÉ: Použijeme enumerate(vsechna_data), abychom znali index řádku (od 0)
    for idx, radek in enumerate(vsechna_data):
        if not radek:
            continue
        prvni_bunka = radek[0].strip()
        
        # Hledáme zaměstnance
        if prvni_bunka == realne_jmeno_uzivatele.strip():
            radek_zamestnance = radek
            radek_index = idx + 1  # <--- NOVÉ: uložení čísla řádku pro Google Sheets (Sheets číslují od 1)
        # Hledáme kapacitu dovolených
        elif "možná dovolená" in prvni_bunka.lower():
            radek_mozna_dovolena = radek
        # Hledáme řádek "Bude potřeba"
        elif "bude potřeba" in prvni_bunka.lower():
            radek_bude_potreba = radek
        # Hledáme řádek "WDO počet"
        elif "wdo počet" in prvni_bunka.lower() or "wdo pocet" in prvni_bunka.lower():
            radek_wdo_pocet = radek
            
    if not radek_zamestnance or not radek_index:
        return []

    # 5. Spárujeme dny se směnami a WDO statusy
    smeny_list = []
    
    for col_idx in range(1, len(radek_s_dny)):
        den_str = radek_s_dny[col_idx].strip()
        
        if not den_str or not den_str.isdigit():
            continue
            
        kod_smeny = radek_zamestnance[col_idx].strip()
        
        if not kod_smeny:
            kod_smeny = "Předpoklad směny"
            
        # Načtení kapacity dovolené
        kapacita_dovolenych = "0"
        if radek_mozna_dovolena and col_idx < len(radek_mozna_dovolena):
            kapacita_dovolenych = radek_mozna_dovolena[col_idx].strip() or "0"
            
        # Načtení WDO informací z tabulky pro konkrétní den
        wdo_potreba_val = radek_bude_potreba[col_idx].strip() if radek_bude_potreba and col_idx < len(radek_bude_potreba) else ""
        wdo_pocet_val = radek_wdo_pocet[col_idx].strip() if radek_wdo_pocet and col_idx < len(radek_wdo_pocet) else "0"
        
        # NOVÉ: Určíme přesné souřadnice buňky v Google Sheets
        sloupec_idx = col_idx + 1  # +1 protože Google Sheets sloupce číslují od 1 (A=1, B=2...)
        bunka_a1 = rowcol_to_a1(radek_index, sloupec_idx)
        
        # NOVÉ: Vytáhneme komentář pro tuto konkrétní buňku z načteného balíku poznámek
        komentar_z_bunky = vsechny_poznamky.get(bunka_a1, "")
        
        # Vytvoření data
        den = int(den_str)
        mesice_map = {
            "LEDEN": 1, "ÚNOR": 2, "BŘEZEN": 3, "DUBEN": 4, "KVĚTEN": 5, "ČERVEN": 6,
            "ČERVENEC": 7, "SRPEN": 8, "ZÁŘÍ": 9, "ŘÍJEN": 10, "LISTOPAD": 11, "PROSINEC": 12
        }
        mesic_cislo = mesice_map.get(nazev_mesice.upper(), 1)
        datum_obj = datetime(rok, mesic_cislo, den)
        
        den_v_tydnu_cz = radek_nazvy_dnu[col_idx].strip() if col_idx < len(radek_nazvy_dnu) else ""
        
        # Uložíme všechna data do seznamu
        smeny_list.append({
            "datum": datum_obj.strftime("%Y-%m-%d"),
            "den_v_tydnu": den_v_tydnu_cz,
            "den": den,
            "smena": kod_smeny,
            "mozna_dovolena": kapacita_dovolenych,
            "wdo_potreba": wdo_potreba_val,  
            "wdo_pocet": wdo_pocet_val,
            "radek": radek_index,          # <--- NOVÉ: pošle se do HTML šablony
            "sloupec": sloupec_idx,        # <--- NOVÉ: pošle se do HTML šablony
            "komentar": komentar_z_bunky   # <--- NOVÉ: pošle se do HTML šablony
        })
        
    return smeny_list
