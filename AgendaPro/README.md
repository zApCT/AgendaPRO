# AgendaPro (MVP Desktop Web App)

Gestionale **semplice e moderno** per PMI/professionisti: *Agenda settimanale* + *Clienti (mini CRM)*.

## Funzionalità MVP
- Dashboard con indicatori rapidi.
- Agenda settimanale (vista desktop), creazione/modifica/cancellazione appuntamenti.
- Clienti: elenco, ricerca, dettaglio, modifica, cancellazione.
- Design pulito e moderno (desktop-first).
- Database locale **SQLite** (nessuna configurazione necessaria).
- Seed dati demo opzionale.

## Requisiti
- Python 3.10+
- `pip`

## Installazione (Windows/macOS/Linux)
```bash
cd AgendaPro
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
# source .venv/bin/activate

pip install -r requirements.txt
python app.py
```
Apri il browser su: **http://127.0.0.1:5000**

> Se vuoi attivare dati demo la prima volta, avvia con:
> ```bash
> SEED_DEMO=1 python app.py   # macOS/Linux
> ```
> oppure su Windows (PowerShell):
> ```powershell
> $env:SEED_DEMO=1; python app.py
> ```

## Struttura
```
AgendaPro/
  app.py
  models.py
  templates/
  static/
  requirements.txt
  README.md
```

## Note
- Questo è un MVP: codice semplice e lineare per velocità. In futuro si può separare blueprint, aggiungere test, auth, ruoli, promemoria email, pagamenti, ecc.
- Tutti i dati sono salvati in `agendapro.db` nella cartella del progetto.
