# Nasazeni aplikace

Tahle Flask aplikace muze bezet na hostingu, takze ji nemusis mit spustenou ze sveho PC. Nejjednodussi volby jsou Render, Railway nebo Fly.io.

## Co je potreba

1. Nahrat projekt do GitHub repozitare.
2. Na hostingu vytvorit novou webovou sluzbu z GitHub repozitare.
3. Nastavit build/install prikaz:

```bash
pip install -r requirements.txt
```

4. Nastavit start prikaz:

```bash
gunicorn app:app
```

5. Nastavit promenne prostredi:

```text
SECRET_KEY=dlouhy-nahodny-tajny-text
GOOGLE_CREDENTIALS_JSON=obsah-souboru-credentials.json-na-jednom-radku
```

Volitelne:

```text
DATABASE_URL=postgresql://...
```

Bez `DATABASE_URL` aplikace pouzije lokalni SQLite soubor `databaze.db`. To staci pro test, ale pro trvaly provoz na hostingu je lepsi PostgreSQL databaze, protoze nektere hostingy mazou lokalni soubory pri restartu nebo deployi.

## Prechod ze SQLite na PostgreSQL

PostgreSQL neni soubor jako `databaze.db`. Je to databazova sluzba. Hosting ti po vytvoreni PostgreSQL databaze da adresu ve formatu:

```text
postgresql://uzivatel:heslo@server:5432/nazev_databaze
```

Tuhle hodnotu vloz na hostingu do promenne prostredi:

```text
DATABASE_URL=postgresql://...
```

Pokud chces prenest data ze stavajiciho souboru `databaze.db`, spust migracni skript:

```bash
python migrate_sqlite_to_postgres.py --database-url "postgresql://uzivatel:heslo@server:5432/nazev_databaze"
```

Skript vytvori tabulky v PostgreSQL a prenese tabulky `uzivatel` a `pozadavek`.

## Dulezite

Soubor `credentials.json` nikdy neposilej verejne do GitHubu. Je v `.gitignore`; na hostingu se jeho obsah vklada do promenne `GOOGLE_CREDENTIALS_JSON`.

Po nasazeni dostanes verejnou URL adresu, napr. `https://tvoje-aplikace.onrender.com`, kterou otevres z mobilu odkudkoliv.
