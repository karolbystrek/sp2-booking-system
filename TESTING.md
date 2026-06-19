# Uruchamianie testów

## Instalacja

```bash
python -m venv .venv
```

Windows:

```powershell
.venv\Scripts\python -m pip install -r requirements.txt
```

Linux/macOS:

```bash
.venv/bin/python -m pip install -r requirements.txt
```

## Pełny zestaw z coverage

```bash
python -m pytest --cov=src --cov-report=term-missing --cov-report=xml
```

Każdy test otrzymuje osobną bazę SQLite w katalogu tymczasowym. Testy nie korzystają z repozytoryjnego pliku bazy i nie pozostawiają danych pomiędzy przypadkami.

## Znane defekty

Dwa testy są oznaczone jako `xfail(strict=True)`. Szczegóły i powiązanie z Gold Architecture znajdują się w `RAPORT_TESTOW.md`.

