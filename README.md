# Fuel Blending Optimization Package (v1.3.1)

Questo pacchetto fornisce strumenti per l'ottimizzazione della miscelazione di carburanti, l'analisi economica e la gestione dei dati.

## Struttura del Progetto

Il codice sorgente si trova nella directory `fuel_blending/fuel_blending/`. La directory `tests/` (ora parte del pacchetto `fuel_blending`) contiene i test unitari e di integrazione.

```
fuel_blending/
├── fuel_blending/    # Codice sorgente del pacchetto
│   ├── analysis/
│   ├── blending/
│   ├── commands/
│   ├── config/
│   ├── integrations/
│   ├── loaders/
│   ├── models/
│   ├── optimization/
│   ├── tests/        # Test (ora parte del pacchetto)
│   ├── utils/
│   ├── cli.py
│   └── app.py
├── docs/             # Documentazione aggiuntiva
├── scripts/          # Script di utilità
├── config_examples/  # Esempi di file di configurazione
├── data_examples/    # Esempi di file di dati
├── fuel_blending_guide/ # Guida utente completa
├── pyproject.toml    # Metadati e dipendenze del progetto
├── requirements.txt  # Dipendenze (potrebbe essere ridondante con pyproject.toml)
└── run_tests.sh      # Script per eseguire i test
```

## Installazione

Per installare il pacchetto e le sue dipendenze, si consiglia di creare un ambiente virtuale:

```bash
python3 -m venv venv
source venv/bin/activate  # Su Linux/macOS
# venv\Scripts\activate  # Su Windows
```

Installare il pacchetto in modalità "editable" (consigliato per lo sviluppo e l'esecuzione dei test):

```bash
pip install -e .
```

Per installare anche le dipendenze opzionali (es. per Google Drive o sviluppo):

```bash
pip install -e ".[google_drive,dev]"
```

## Esecuzione dei Test

Assicurarsi di aver installato le dipendenze di sviluppo (`dev`) e il pacchetto in modalità editable (`pip install -e .[dev]`).

Il modo più semplice per eseguire i test è utilizzare lo script fornito dalla directory principale del progetto (`/home/ubuntu/fuel_blending`):

```bash
./run_tests.sh
```

Alternativamente, è possibile eseguire `pytest` come modulo Python dalla directory principale del progetto:

```bash
python3 -m pytest
```

Questo comando scoprirà ed eseguirà automaticamente tutti i test nella directory `fuel_blending/fuel_blending/tests/`.

**Nota:** Al momento (v1.3.1), alcuni test potrebbero fallire a causa di importazioni mancanti nel codice sorgente (`is_linear_property`, `AuthenticationError`, `PROPERTY_T10`). La struttura di esecuzione dei test è stata corretta.

## Utilizzo

Il pacchetto può essere utilizzato tramite l'interfaccia a riga di comando (CLI). Eseguire `fuel-blending --help` per vedere i comandi disponibili e le opzioni.

Consultare la guida completa in `fuel_blending_guide/complete_guide.md` per istruzioni dettagliate sull'utilizzo.


