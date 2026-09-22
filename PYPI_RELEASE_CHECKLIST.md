# Checklist di pre-pubblicazione su PyPI — `python-tls-client`

Nome scelto: **`python-tls-client`** (verificato libero su PyPI il 2026-09-22, `GET /pypi/python-tls-client/json` → 404).

Questo documento elenca tutti i problemi riscontrati nell'analisi del repo e le patch
puntuali da applicare prima di poter fare `python -m build && twine upload` per la
prima release. Ogni sezione è indipendente e applicabile singolarmente.

---

## 1. [BLOCCANTE] Nome pacchetto — rinominare `tls_client` → `python-tls-client`

**Problema**: `__title__` in `tls_client/__version__.py` è `"tls_client"`, nome già
occupato su PyPI dal progetto originale (Florian Zager). Va cambiato il nome di
distribuzione. Il nome dell'**import** (`import tls_client`) può restare invariato —
è normale che un pacchetto PyPI abbia un nome di distribuzione diverso dal nome del
modulo importabile (es. `pip install python-tls-client` → `import tls_client`).

**Patch** — `tls_client/__version__.py`:

```diff
 __title__ = "tls_client"
-__description__ = "Advanced Python HTTP Client."
+__description__ = "Advanced Python HTTP Client (fork with binary-response fix and certificate pinning)."
 __version__ = "1.0.2"
-__author__ = "Florian Zager"
+__author__ = "Emanuele Scarlata"
 __license__ = "MIT"
```

`__title__` va lasciato `tls_client` (è il nome del modulo Python, non deve cambiare)
ma il nome del *pacchetto di distribuzione* si imposta separatamente in `setup.py`
(vedi sezione 3) — non deriva da `about["__title__"]` una volta convertito a
`pyproject.toml`.

**Nota sulla licenza**: il progetto originale è MIT, quindi il fork con nome diverso
è legittimo. In `LICENSE` va mantenuto il copyright originale e aggiunta una riga per
le modifiche, non sostituito:

```diff
 MIT License

 Copyright (c) 2022 Florian Zager
+Copyright (c) 2026 Emanuele Scarlata (modifications)

 Permission is hereby granted, free of charge, to any person obtaining a copy
```

---

## 2. [BLOCCANTE] Manca `pyproject.toml`

**Problema**: solo `setup.py` legacy, nessun `pyproject.toml`/build-backend
dichiarato. `pip install` funziona ancora ma è lo standard PEP 517/518 atteso oggi,
ed è il file che dichiara il nome `python-tls-client`.

**Patch** — nuovo file `pyproject.toml`:

```toml
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "python-tls-client"
dynamic = ["version"]
description = "Advanced Python HTTP Client with TLS fingerprint spoofing (fork with binary-response fix and certificate pinning)"
readme = "README.md"
license = { text = "MIT" }
authors = [
    { name = "Emanuele Scarlata" }
]
requires-python = ">=3.8"
dependencies = [
    "typing-extensions",
]
classifiers = [
    "Environment :: Web Environment",
    "Intended Audience :: Developers",
    "Natural Language :: English",
    "Operating System :: Unix",
    "Operating System :: MacOS :: MacOS X",
    "Operating System :: Microsoft :: Windows",
    "Programming Language :: Python",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.8",
    "Programming Language :: Python :: 3.9",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Programming Language :: Python :: 3 :: Only",
    "Topic :: Internet :: WWW/HTTP",
    "Topic :: Software Development :: Libraries",
]

[project.urls]
Homepage = "https://github.com/Fenix46/Python-Tls-Client"
Source = "https://github.com/Fenix46/Python-Tls-Client"
Original = "https://github.com/FlorianREGAZ/Python-Tls-Client"

[tool.setuptools]
packages = ["tls_client", "tls_client.dependencies"]
include-package-data = true

[tool.setuptools.dynamic]
version = { attr = "tls_client.__version__.__version__" }

[tool.setuptools.package-data]
"tls_client.dependencies" = ["*"]
```

`setup.py` può restare come shim minimo per compatibilità con tool che ancora lo
invocano direttamente:

```python
from setuptools import setup
setup()
```

(tutta la configurazione ora vive in `pyproject.toml`; il vecchio `setup.py` con
`glob`/`exec` sul file di versione viene rimosso).

---

## 3. [CONSIGLIATO] `MANIFEST.in` mancante

**Problema**: senza `MANIFEST.in`, l'sdist (`.tar.gz`) generato da `python -m build`
rischia di non includere i binari in `tls_client/dependencies/` — funzionano nel
wheel grazie a `package-data`, ma l'sdist è più fragile e va garantito esplicitamente.

**Patch** — nuovo file `MANIFEST.in`:

```
include README.md
include LICENSE
include requirements.txt
recursive-include tls_client/dependencies *
```

---

## 4. [CONSIGLIATO] README non indica che è un fork

**Problema**: chi trova il pacchetto su PyPI con un nome diverso dall'originale deve
capire subito che relazione c'è con `tls-client` di Florian Zager — sia per
attribuzione MIT sia per chiarezza (evita che chi cerca l'originale si confonda, ed
evita ambiguità su dove aprire issue).

**Patch** — aggiungere in cima a `README.md`, subito dopo il titolo:

```diff
 # Python-TLS-Client
+
+> **Nota:** questo è un fork di [Python-Tls-Client](https://github.com/FlorianREGAZ/Python-Tls-Client)
+> di Florian Zager, pubblicato su PyPI con nome diverso (`python-tls-client`) perché
+> il nome originale `tls-client` è già occupato dal progetto upstream.
+> Il modulo importabile resta invariato: `import tls_client`.
+>
+> Modifiche rispetto all'originale:
+> - Fix corruzione risposte binarie (protobuf, immagini, ...) — vedi Changelog 1.0.2
+> - Certificate pinning (vedi Changelog 1.0.1)
+
 Python-TLS-Client is an advanced HTTP library based on requests and tls-client.

 # Installation
 ```
-pip install tls-client
+pip install python-tls-client
 ```
```

---

## 5. [OPZIONALE] Pacchetto monolitico da ~90MB (tutti i binari per ogni piattaforma)

**Problema**: `tls_client/dependencies/` contiene 7 binari precompilati (Linux
x86/amd64/arm64, macOS x86/arm64, Windows 32/64) per un totale di circa 90MB, tutti
inclusi in ogni wheel indipendentemente dalla piattaforma di installazione. È lo
stesso approccio dell'originale, quindi non blocca la pubblicazione, ma è la causa
principale della dimensione anomala del pacchetto.

**Fix strutturale (rimandabile a una release successiva)**: generare wheel
platform-specific con tag (`manylinux`, `macosx`, `win`) che includono solo il
binario rilevante, tramite `cibuildwheel` o build a matrice in CI. Non necessario per
la prima release: PyPI accetta wheel "universali" grandi, semplicemente l'utente
scarica più dati del necessario. Da rivalutare se/quando emergono lamentele sulla
dimensione.

**Non serve una patch per questo ora** — lo segnalo solo perché è il problema più
visibile una volta pubblicato (`pip install python-tls-client` scaricherà ~90MB).

---

## 6. [OPZIONALE] Nessuna automazione di pubblicazione

**Problema**: nessun workflow CI per buildare/pubblicare su PyPI al momento di un
tag/release GitHub. Per la prima pubblicazione si fa a mano, ma se prevedi più
release conviene automatizzare.

**Patch** — nuovo file `.github/workflows/publish.yml`:

```yaml
name: Publish to PyPI

on:
  release:
    types: [published]

jobs:
  build-and-publish:
    runs-on: ubuntu-latest
    permissions:
      id-token: write
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install build
      - run: python -m build
      - uses: pypa/gh-action-pypi-publish@release/v1
```

Richiede di configurare **Trusted Publishing** su PyPI (associare il repo GitHub al
progetto `python-tls-client` nelle impostazioni PyPI) — niente token da gestire
manualmente. Da fare solo dopo la prima pubblicazione manuale, perché Trusted
Publishing richiede che il progetto esista già su PyPI (o si configuri in anticipo
come "pending publisher").

---

## Ordine di esecuzione consigliato per la prima release

1. Sezione 1 — rinominare, aggiornare `__version__.py` e `LICENSE`
2. Sezione 2 — aggiungere `pyproject.toml`, ridurre `setup.py` a shim
3. Sezione 3 — aggiungere `MANIFEST.in`
4. Sezione 4 — aggiornare `README.md`
5. Build locale di verifica:
   ```
   python -m build
   python -m twine check dist/*
   ```
6. Test di installazione in un venv pulito da sdist e da wheel prima di caricare
7. `twine upload dist/*` (o `--repository testpypi` prima, per una prova a secco)
8. Sezioni 5 e 6 restano opzionali/posticipabili a release successive
