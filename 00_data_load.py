import logging
import requests
import zipfile
from pathlib import Path

# === CONFIGURATION ===
WEB_URL = "https://www.cms.gov/Research-Statistics-Data-and-Systems/Downloadable-Public-Use-Files/SynPUFs/Downloads/"
FILES = {
    "benefit": "DE1_0_2009_Beneficiary_Summary_File_Sample_20.zip",
    "claim": "DE1_0_2008_to_2010_Outpatient_Claims_Sample_20.zip",
}

# === SETUP LOGGING ===
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)

# === SETUP PATHS ===
base_dir = Path.cwd()
data_dir = base_dir / "data"
data_dir.mkdir(parents=True, exist_ok=True)


def download_file(file_name: str, save_path: Path):
    url = WEB_URL + file_name
    logging.info(f"Downloading: {url}")

    try:
        response = requests.get(url)
        response.raise_for_status()
        with open(save_path, "wb") as f:
            f.write(response.content)
        logging.info(f"Saved to: {save_path}")
    except requests.RequestException as e:
        logging.error(f"Failed to download {url}: {e}")
        raise


def extract_zip(zip_path: Path, extract_to: Path):
    logging.info(f"Extracting: {zip_path}")
    try:
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(extract_to)
        logging.info(f"Extracted to: {extract_to}")
    except zipfile.BadZipFile as e:
        logging.error(f"Failed to extract {zip_path}: {e}")
        raise


# === PROCESS FILES ===
for label, filename in FILES.items():
    zip_loc = data_dir / f"{label}.zip"
    download_file(filename, zip_loc)
    extract_zip(zip_loc, data_dir)
