from __future__ import annotations

import hashlib
import re
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASELINE_DIR = ROOT / "resources" / "expected ui" / "android"
SHEET = BASELINE_DIR / "approved_android_ui_baseline_sheet.svg"
MANIFEST = BASELINE_DIR / "README.md"

EXPECTED_LABELS = (
    "Welcome / entry",
    "Dashboard / status",
    "Dashboard / waiting",
    "Step-by-step guide",
    "Approved MIBU logo",
)
EXPECTED_SOURCE_HASHES = (
    "eddd106925e8305f2d5488d980c6934fffd6b29e7445d9741f4a90cc913c3e94",
    "53eba33bda7b491f098ebe1f7b99ca7d2701000b488ed3a8c1bed41badf1203c",
    "0375aec08e26d73bd9cc8d920a998c196fdd6ffe3ccec7f89015d9e7ef8028bf",
    "c7babc28a23ecbacbcd775752fd3eef465abfda9a85402613c4fc50445595528",
    "ab22eb530c56edbb5525ba874bac95c1bddfd83f6d76c2ebf102bfac273364c3",
)
MIN_EMBEDDED_IMAGE_BYTES = 2_000


def fail(message: str) -> None:
    raise RuntimeError(f"Android expected-UI baseline invalid: {message}")


def validate_sheet() -> str:
    if not SHEET.is_file() or SHEET.stat().st_size <= 0:
        fail(f"missing or empty sheet: {SHEET}")
    try:
        root = ET.parse(SHEET).getroot()
    except ET.ParseError as exc:
        fail(f"sheet is not valid SVG/XML: {exc}")

    if root.attrib.get("width") != "720" or root.attrib.get("height") != "560":
        fail(f"unexpected sheet canvas: {root.attrib}")

    text = SHEET.read_text(encoding="utf-8")
    for label in EXPECTED_LABELS:
        if label not in text:
            fail(f"missing approved state label: {label}")

    images = [elem for elem in root.iter() if elem.tag.rsplit("}", 1)[-1] == "image"]
    if len(images) != len(EXPECTED_LABELS):
        fail(f"expected {len(EXPECTED_LABELS)} embedded approved images, found {len(images)}")

    for index, image in enumerate(images, start=1):
        href = image.attrib.get("href") or image.attrib.get("{http://www.w3.org/1999/xlink}href") or ""
        match = re.fullmatch(r"data:image/(?:webp|png|jpeg);base64,([A-Za-z0-9+/=]+)", href)
        if not match:
            fail(f"embedded image {index} is not a self-contained image data URI")
        import base64

        try:
            raw = base64.b64decode(match.group(1), validate=True)
        except Exception as exc:
            fail(f"embedded image {index} has invalid Base64: {exc}")
        if len(raw) < MIN_EMBEDDED_IMAGE_BYTES:
            fail(f"embedded image {index} is suspiciously small ({len(raw)} bytes)")

    return hashlib.sha256(SHEET.read_bytes()).hexdigest()


def validate_manifest(sheet_sha256: str) -> None:
    if not MANIFEST.is_file() or MANIFEST.stat().st_size <= 0:
        fail(f"missing or empty manifest: {MANIFEST}")
    text = MANIFEST.read_text(encoding="utf-8")
    if "approved_android_ui_baseline_sheet.svg" not in text:
        fail("manifest does not name the canonical baseline sheet")
    for label in EXPECTED_LABELS:
        if label not in text:
            fail(f"manifest is missing approved state: {label}")
    for source_hash in EXPECTED_SOURCE_HASHES:
        if source_hash not in text:
            fail(f"manifest is missing recovered-source SHA-256: {source_hash}")
    if "redrawn from memory" not in text:
        fail("manifest does not preserve the source-recovery boundary")
    print(f"Android expected-UI baseline sheet SHA-256: {sheet_sha256}")


def main() -> int:
    sheet_sha256 = validate_sheet()
    validate_manifest(sheet_sha256)
    print("Android expected-UI baseline validated: five recovered approved states are present and self-contained.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
