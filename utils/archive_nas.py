import subprocess
from pathlib import Path
import shutil
from datetime import datetime
import os

# =========================
# CONFIGURATION NAS
# =========================

NAS_SHARE = "//HAL_NAS/commun/PROJETS/PROJETS_INTERNES/11_ETUVE/EXPORT"
MOUNT_POINT = "/mnt/etuve_export"

USERNAME = "thomas.grosset"
PASSWORD = "Halcyon20220201"

NAS_DIR = Path(MOUNT_POINT)

# =========================
# MONTAGE CIFS
# =========================

def mount_nas():
    """
    Monte le partage r�seau CIFS.
    """

    os.makedirs(MOUNT_POINT, exist_ok=True)

    # V�rifie si d�j� mont�
    result = subprocess.run(
        ["mountpoint", "-q", MOUNT_POINT]
    )

    if result.returncode == 0:
        return True

    mount_cmd = [
        "sudo",
        "mount",
        "-t",
        "cifs",
        NAS_SHARE,
        MOUNT_POINT,
        "-o",
        (
            f"username={USERNAME},"
            f"password={PASSWORD},"
            "iocharset=utf8,"
            "file_mode=0777,"
            "dir_mode=0777"
        )
    ]

    try:
        subprocess.run(mount_cmd, check=True)
        print("NAS mont� avec succ�s")
        return True

    except subprocess.CalledProcessError as e:
        print(f"Erreur montage NAS : {e}")
        return False


# =========================
# ARCHIVAGE FICHIERS
# =========================

def archive_images(csv_path, png_path):
    """
    Archive un fichier CSV et une image PNG sur le NAS.

    Parameters
    ----------
    csv_path : str or Path
        Chemin du fichier CSV.

    png_path : str or Path
        Chemin du fichier PNG.
    """

    if not mount_nas():
        return False

    files_to_archive = [
        Path(csv_path),
        Path(png_path)
    ]

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    for file_path in files_to_archive:

        if not file_path.exists():
            print(f"Fichier introuvable : {file_path}")
            continue

        # Nouveau nom avec horodatage
        new_name = f"{file_path.stem}_{timestamp}{file_path.suffix}"

        destination = NAS_DIR / new_name

        try:
            shutil.copy2(file_path, destination)
            print(f"Fichier archiv� : {destination}")

        except Exception as e:
            print(f"Erreur copie {file_path.name} : {e}")
            return False

    return True