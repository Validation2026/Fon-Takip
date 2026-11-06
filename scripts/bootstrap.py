"""Orijinal dosyayı korumalı parçalardan birebir geri kurar (stdlib)."""
from pathlib import Path
import hashlib

ROOT = Path(__file__).resolve().parent.parent
ARCHIVE = ROOT / "site-archive"
SOURCE = ROOT / "source" / "index.html"
PUBLIC = ROOT / "public" / "index.html"
EXPECTED = "dcf107747f7b28a9cbe14094349a1d484f11ff413c0242c037f549b4d2f468c8"
SIZE = 5156725

def build():
    parts = sorted(ARCHIVE.glob("*.txt"))
    if len(parts) != 26:
        raise RuntimeError("Eksik kaynak kodu parçaları, yayın durduruldu.")
    content = b"".join(p.read_bytes() for p in parts)
    sha = hashlib.sha256(content).hexdigest()
    if len(content) != SIZE or sha != EXPECTED:
        raise RuntimeError(f"Kaynak bütünlük hatası: {len(content)} byte; SHA256={sha}")
    SOURCE.parent.mkdir(parents=True, exist_ok=True)
    SOURCE.write_bytes(content)
    if not PUBLIC.exists():
        PUBLIC.parent.mkdir(parents=True, exist_ok=True)
        PUBLIC.write_bytes(content)
    print(f"Orijinal HTML doğrulandı: {len(content):,} bayt; SHA256={sha}")
    return content

if __name__ == "__main__":
    build()
