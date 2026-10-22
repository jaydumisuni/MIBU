"""Read-only exact-ROM integrity and handoff evaluation for MIBU."""
from __future__ import annotations
import hashlib
from pathlib import Path
import zipfile

SKY_GLOBAL_208 = {
    "filename": "sky_global-ota_full-OS2.0.208.0.VMWMIXM-user-15.0-34d74acb5e.zip",
    "product": "sky", "build": "OS2.0.208.0.VMWMIXM",
    "format": "full-recovery-ota",
    "size": 4_983_468_594,
    "official_md5": "34d74acb5e4400a531a962adf7409f39",
}

def _md5_file(path: Path) -> str:
    h=hashlib.md5(usedforsecurity=False)
    with path.open("rb") as f:
        for buf in iter(lambda:f.read(4*1024*1024),b""):
            h.update(buf)
    return h.hexdigest()

def assess_rom_handoff(*, properties:dict[str,str], rom:Path, serial:str, verify_bytes:bool=True,
                       sleeper_acceptance:dict|None=None)->dict:
    spec=SKY_GLOBAL_208
    issues=[]
    product=properties.get("ro.product.device","").strip()
    region=properties.get("ro.miui.region","").strip().upper()
    build=properties.get("ro.build.version.incremental","").strip()
    lock=properties.get("ro.boot.flash.locked","").strip()
    verified_boot=properties.get("ro.boot.verifiedbootstate","").strip()
    size=rom.stat().st_size if rom.is_file() else None
    known=rom.name==spec["filename"]
    digest=None
    structure=False
    if not known:issues.append("The selected file is not the verified sky Global recovery OTA.")
    if size!=spec["size"]:issues.append("ROM size is missing or incorrect.")
    if known and size==spec["size"] and verify_bytes:
        digest=_md5_file(rom)
        if digest.lower()!=spec["official_md5"]:
            issues.append("ROM MD5 does not match Xiaomi's published package.")
        else:
            try:
                with zipfile.ZipFile(rom) as archive:
                    structure=len(archive.infolist())==7 and "payload.bin" in archive.namelist()
            except (OSError,zipfile.BadZipFile,zipfile.LargeZipFile):
                pass
            if not structure:issues.append("ZIP central directory/payload invalid.")
    if not verify_bytes:issues.append("Metadata-only inspection does not validate ROM bytes.")
    if product!="sky":issues.append("The connected handset does not match the sky firmware target.")
    proof = sleeper_acceptance if isinstance(sleeper_acceptance, dict) else {}
    observed = proof.get("observations", {})
    if not isinstance(observed, dict): observed = {}
    # Android property readback is supporting evidence, never physical PASS.
    unlocked = bool(
        lock == "0" and
        proof.get("serial") == serial and
        proof.get("mode") == "fastboot" and
        proof.get("verdict") == "PASS" and
        proof.get("physical_unlock_proven") is True and
        observed.get("product") == product == "sky" and
        observed.get("getvar_unlocked") == "yes" and
        observed.get("device_unlocked") == "true"
    )
    if not unlocked:issues.append("Physical Fastboot bootloader unlock proof is missing or inconsistent.")
    if region=="CN":issues.append("Stock updater rejected the China-to-Global transition with code 2001.")
    elif not region:issues.append("Phone region is unknown.")
    if verified_boot not in ("green","orange"):issues.append("Verified-boot state is unknown.")
    good_rom=bool(known and size==spec["size"] and digest==spec["official_md5"] and structure)

    # No code here can flash, reboot, install, erase or grant install authority.
    return {
      "schema":"ttg.mibu.rom-handoff-readonly.v1",
      "serial":serial,
      "device":{"product":product,"region":region or "unknown","build":build or "unknown",
                "bootloader":"unlocked" if unlocked else "locked" if lock=="1" else "android-reports-unlocked-unverified" if lock=="0" else "unknown",
                "verified_boot":verified_boot or "unknown"},
      "rom":{"path":str(rom),"filename":rom.name,"size":size,
             "format":spec["format"] if known else "unknown",
             "target_build":spec["build"] if known else None,
             "expected_md5":spec["official_md5"] if known else None,
             "observed_md5":digest,"verified":good_rom,"metadata_only":not verify_bytes},
      "readiness":{"target_matches":product=="sky","rom_verified":good_rom,
                   "physical_unlock_observed":unlocked,"android_lock_reports_unlocked":lock=="0",
                   "sleeper_acceptance":proof.get("verdict", "not-collected"),"installer_qualified":False,
                   "installation_admitted":False},
      "reasons":issues,
      "next_step":("Select and verify a compatible sky Fastboot ROM and qualified installer."
                   if unlocked else "Establish independent authorized bootloader-unlocked proof."),
      "phone_writes":0,
    }

def format_readiness(report:dict)->str:
    d=report["device"];p=report["rom"];q=report["readiness"]
    return "\n".join([
      "ROM handoff: read-only; no installation performed.",
      f"Device: {d['product']} {d['build']} / {d['region']} / bootloader {d['bootloader']}",
      f"ROM: {p['filename']} ({p['format']})",
      f"ROM integrity: {'verified' if q['rom_verified'] else 'unverified'}",
      "Install authorization: NOT QUALIFIED",
      *(f"- {why}" for why in report["reasons"]),
      f"Next: {report['next_step']}",
    ])
