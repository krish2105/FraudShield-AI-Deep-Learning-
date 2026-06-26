"""
download_paysim.py
==================
Fetch the REAL PaySim dataset and install it at data/paysim.csv.

The real PaySim file (~6.3M rows, ~470 MB) lives on Kaggle and requires your
own Kaggle API credentials — it cannot be redistributed in this repo. This
script automates the download once your credentials are in place.

Setup (one time)
----------------
1. pip install kaggle
2. Create an API token: kaggle.com -> Account -> "Create New API Token".
   This downloads kaggle.json.
3. Place it at ~/.kaggle/kaggle.json  and  chmod 600 ~/.kaggle/kaggle.json

Then run
--------
    python src/download_paysim.py

If credentials are missing, this prints clear instructions and exits without
error so the rest of the project keeps working on synthetic data.
"""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

try:
    from . import config
    from .utils import log
except ImportError:  # pragma: no cover
    sys.path.append(str(Path(__file__).resolve().parents[1]))
    from src import config
    from src.utils import log

KAGGLE_DATASET = "ealaxi/paysim1"          # the canonical PaySim mirror
KAGGLE_CSV_NAME = "PS_20174392719_1491204439457_log.csv"


def _have_credentials() -> bool:
    if os.environ.get("KAGGLE_USERNAME") and os.environ.get("KAGGLE_KEY"):
        return True
    return (Path.home() / ".kaggle" / "kaggle.json").exists()


def _instructions() -> None:
    print(
        "\n"
        "  Real PaySim download needs Kaggle credentials (not found).\n"
        "  ----------------------------------------------------------\n"
        "  1. pip install kaggle\n"
        "  2. kaggle.com -> Account -> 'Create New API Token' (downloads kaggle.json)\n"
        "  3. mkdir -p ~/.kaggle && mv ~/Downloads/kaggle.json ~/.kaggle/\n"
        "     chmod 600 ~/.kaggle/kaggle.json\n"
        "  4. python src/download_paysim.py\n\n"
        "  No credentials? Generate a large synthetic dataset instead:\n"
        "     python src/make_large_dataset.py\n"
    )


def main() -> int:
    config.ensure_dirs()
    if config.REAL_DATA_PATH.exists() and config.REAL_DATA_PATH.stat().st_size > 5_000_000:
        log(f"Real PaySim already present at {config.REAL_DATA_PATH} "
            f"({config.REAL_DATA_PATH.stat().st_size/1e6:.0f} MB). Nothing to do.")
        return 0

    if not _have_credentials():
        _instructions()
        return 0

    try:
        from kaggle.api.kaggle_api_extended import KaggleApi
    except Exception:
        print("  The 'kaggle' package is not installed.  ->  pip install kaggle")
        _instructions()
        return 0

    api = KaggleApi()
    api.authenticate()
    log(f"Downloading {KAGGLE_DATASET} from Kaggle (this is large)…")
    api.dataset_download_files(KAGGLE_DATASET, path=str(config.DATA_DIR), unzip=True)

    extracted = config.DATA_DIR / KAGGLE_CSV_NAME
    if extracted.exists():
        shutil.move(str(extracted), str(config.REAL_DATA_PATH))
    if config.REAL_DATA_PATH.exists():
        log(f"Installed real PaySim -> {config.REAL_DATA_PATH}. Now run: python src/train_all.py")
        return 0

    print("  Download finished but the expected CSV was not found; check data/.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
