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

    # ----------------------------
    # unpack
    # ----------------------------

    if UNPACK_DIR.exists():
        shutil.rmtree(UNPACK_DIR)

    with zipfile.ZipFile(DOCX_FILE, "r") as z:
        z.extractall(UNPACK_DIR)

    # ----------------------------
    # media
    # ----------------------------

    media_src = UNPACK_DIR / "word" / "media"

    if MEDIA_DIR.exists():
        shutil.rmtree(MEDIA_DIR)

    if media_src.exists():
        shutil.copytree(media_src, MEDIA_DIR)

    # ----------------------------
    # namespaces
    # ----------------------------

    ns = {
        "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    }

    # ----------------------------
    # image relationships
    # ----------------------------

    image_map = {}

    rels_file = (
        UNPACK_DIR
        / "word"
        / "_rels"
        / "document.xml.rels"
    )

    if rels_file.exists():

        rels_tree = ET.parse(rels_file)
        rels_root = rels_tree.getroot()

        for rel in rels_root:

            rid = rel.attrib.get("Id")
            target = rel.attrib.get("Target")

            if not rid or not target:
                continue

            if "media/" in target:
                image_map[rid] = Path(target).name

    # ----------------------------
    # document.xml
    # ----------------------------

    xml_file = UNPACK_DIR / "word" / "document.xml"

    tree = ET.parse(xml_file)
    root = tree.getroot()

    body = root.find(
        "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}body"
    )

    rows = []

    counter = 0

    if body is None:
        raise Exception("body not found")

    # ----------------------------
    # iterate document order
    # ----------------------------

    for elem in body:

        tag = elem.tag.split("}")[-1]

        if tag != "p":
            continue

        counter += 1

        # ------------------------
        # text
        # ------------------------

        text_parts = []

        for t in elem.findall(
            ".//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t"
        ):
            if t.text:
                text_parts.append(t.text)

        text = "".join(text_parts).strip()

        if text:

            rows.append({
                "type": "text",
                "id": f"paragraph_{counter:06d}",
                "uuid": str(uuid.uuid4()),
                "text": text
            })

        # ------------------------
        # images
        # ------------------------

        for blip in elem.findall(
            ".//{http://schemas.openxmlformats.org/drawingml/2006/main}blip"
        ):

            rid = blip.attrib.get(
                "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed"
            )

            if not rid:
                continue

            image_name = image_map.get(rid)

            if not image_name:
                continue

            rows.append({
                "type": "image",
                "id": f"image_{counter:06d}",
                "image": image_name
            })

    # ----------------------------
    # save
    # ----------------------------

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

    print()
    print(f"Elements: {len(rows)}")
    print(f"Images found: {len([x for x in rows if x['type'] == 'image'])}")
    print("DOCX extracted")


if __name__ == "__main__":
    run()