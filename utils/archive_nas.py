import subprocess
from pathlib import Path
import shutil
import os
import time
import pwd

# =========================
# CONFIGURATION NAS
# =========================

NAS_SHARE = "//HAL_NAS/commun/PROJETS/PROJETS_INTERNES/11_ETUVE/7-Exports"
MOUNT_POINT = "/mnt/nas"

USERNAME = "etuve"
PASSWORD = "Halcyon2026!"

NAS_DIR = Path(MOUNT_POINT)

# Get user/group IDs
try:
    USER_ID = pwd.getpwnam(USERNAME).pw_uid
    GROUP_ID = pwd.getpwnam(USERNAME).pw_gid
except KeyError:
    USER_ID = 1000
    GROUP_ID = 1000

# =========================
# MONTAGE CIFS
# =========================

def mount_nas():
    """
    Monte le partage réseau CIFS avec permissions d'accès correctes.
    """

    os.makedirs(MOUNT_POINT, exist_ok=True)

    # Vérifie si déjà monté
    result = subprocess.run(
        ["mountpoint", "-q", MOUNT_POINT]
    )

    if result.returncode == 0:
        # Vérifie l'accessibilité
        if is_nas_accessible():
            return True
        else:
            # Démonte et remonte si non accessible
            subprocess.run(["sudo", "umount", MOUNT_POINT], capture_output=True)

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
            f"uid={USER_ID},"
            f"gid={GROUP_ID},"
            "iocharset=utf8,"
            "file_mode=0777,"
            "dir_mode=0777,"
            "noperm"
        )
    ]

    try:
        subprocess.run(mount_cmd, check=True)
        print("NAS monté avec succès")
        time.sleep(1)  # Attendre que le montage soit stabilisé
        return True

    except subprocess.CalledProcessError as e:
        print(f"Erreur montage NAS : {e}")
        return False


def is_nas_accessible():
    """
    Vérifie si le NAS est accessible en écriture.
    """
    try:
        test_file = NAS_DIR / ".access_test"
        test_file.touch()
        test_file.unlink()
        return True
    except Exception as e:
        print(f"NAS non accessible : {e}")
        return False


# =========================
# ARCHIVAGE FICHIERS
# =========================

def archive_images(csv_path, png_path, max_retries=3):
    """
    Archive un fichier CSV et une image PNG sur le NAS avec retry logic et fallback.

    Parameters
    ----------
    csv_path : str or Path
        Chemin du fichier CSV.

    png_path : str or Path
        Chemin du fichier PNG.
        
    max_retries : int
        Nombre de tentatives en cas d'erreur.
    """

    files_to_archive = [
        Path(csv_path),
        Path(png_path)
    ]

    for file_path in files_to_archive:

        if not file_path.exists():
            print(f"Fichier introuvable : {file_path}")
            continue

        # Utilise le nom original du fichier
        destination = NAS_DIR / file_path.name
        
        success = False
        
        for attempt in range(max_retries):
            try:
                # Montage du NAS avant chaque tentative
                if not mount_nas():
                    raise RuntimeError("Impossible de monter le NAS")
                
                # Ajuste les permissions du fichier avant la copie
                os.chmod(file_path, 0o666)
                
                # Copie le fichier
                shutil.copy2(file_path, destination)
                
                # Verifie que la copie a reussi
                if destination.exists():
                    print(f"✓ Fichier archive : {destination}")
                    success = True
                    break
                    
            except (PermissionError, OSError) as e:
                print(f"⚠ Tentative {attempt + 1}/{max_retries} - Erreur copie {file_path.name} : {e}")
                
                # Fallback : essayer avec sudo + cp
                if attempt < max_retries - 1:
                    try:
                        print(f"  → Tentative fallback avec sudo...")
                        subprocess.run(
                            ["sudo", "cp", str(file_path), str(destination)],
                            check=True,
                            capture_output=True
                        )
                        # Ajuster les droits sur le fichier destination
                        subprocess.run(
                            ["sudo", "chmod", "666", str(destination)],
                            capture_output=True
                        )
                        if destination.exists():
                            print(f"  ✓ Fichier copie via sudo : {destination}")
                            success = True
                            break
                    except Exception as e2:
                        print(f"  ✗ Fallback echoue : {e2}")
                        time.sleep(1)
                        continue
                else:
                    time.sleep(1)
                    
            except Exception as e:
                print(f"⚠ Tentative {attempt + 1}/{max_retries} - Erreur copie {file_path.name} : {e}")
                time.sleep(1)
                continue
        
        if not success:
            print(f"✗ Erreur archivage {file_path.name} apres {max_retries} tentatives")
            return False

    return True