from pathlib import Path
import zipfile
import shutil
import json
import uuid
import xml.etree.ElementTree as ET

BASE_DIR = Path(__file__).parent

DOCX_FILE = BASE_DIR / "information.docx"

EXPORT_DIR = BASE_DIR / "export"
UNPACK_DIR = EXPORT_DIR / "_unpacked"
MEDIA_DIR = EXPORT_DIR / "media"

EXPORT_DIR.mkdir(exist_ok=True)

def run():

    if UNPACK_DIR.exists():
        shutil.rmtree(UNPACK_DIR)

    with zipfile.ZipFile(DOCX_FILE, "r") as z:
        z.extractall(UNPACK_DIR)

    media_src = UNPACK_DIR / "word" / "media"

    if MEDIA_DIR.exists():
        shutil.rmtree(MEDIA_DIR)

    if media_src.exists():
        shutil.copytree(media_src, MEDIA_DIR)

    ns = {
        "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    }

    xml_file = UNPACK_DIR / "word" / "document.xml"

    tree = ET.parse(xml_file)
    root = tree.getroot()

    rows = []

    for idx, p in enumerate(
        root.findall(".//w:p", ns),
        start=1
    ):

        text_parts = []

        for t in p.findall(".//w:t", ns):
            if t.text:
                text_parts.append(t.text)

        text = "".join(text_parts).strip()

        if not text:
            continue

        rows.append({
            "id": f"paragraph_{idx:06d}",
            "uuid": str(uuid.uuid4()),
            "text": text
        })

    with open(
        EXPORT_DIR / "text.json",
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            rows,
            f,
            ensure_ascii=False,
            indent=2
        )
        
            

    print("DOCX extracted")


if __name__ == "__main__":
    run()