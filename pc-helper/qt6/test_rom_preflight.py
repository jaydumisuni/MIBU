from pathlib import Path
import unittest
from unittest.mock import patch

from mibu_rom_preflight import SKY_GLOBAL_208,assess_rom_handoff,format_readiness

CN={"ro.product.device":"sky","ro.miui.region":"CN","ro.boot.flash.locked":"1",
    "ro.boot.verifiedbootstate":"green","ro.build.version.incremental":"OS2.0.204.0.VMWCNXM"}

class RomHandoffTests(unittest.TestCase):
    def test_missing_file_blocks(self):
        r=assess_rom_handoff(properties=CN,rom=Path("/nonexistent.zip"),serial="s")
        self.assertFalse(r["rom"]["verified"])
        self.assertFalse(r["readiness"]["installation_admitted"])

    def test_wrong_product_blocks(self):
        r=assess_rom_handoff(properties=dict(CN,**{"ro.product.device":"other"}),
                             rom=Path("/nonexistent.zip"),serial="s")
        self.assertFalse(r["readiness"]["target_matches"])

    def test_metadata_only_never_claims_integrity(self):
        r=assess_rom_handoff(properties=CN,rom=Path(SKY_GLOBAL_208["filename"]),
                             serial="s",verify_bytes=False)
        self.assertFalse(r["rom"]["verified"])

    def test_matching_archive_still_cannot_bypass_cn_lock(self):
        with patch("mibu_rom_preflight._md5_file",return_value=SKY_GLOBAL_208["official_md5"]), \
             patch("pathlib.Path.is_file",return_value=True), \
             patch("pathlib.Path.stat") as stat, \
             patch("zipfile.ZipFile") as archive:
            stat.return_value.st_size=SKY_GLOBAL_208["size"]
            archive.return_value.__enter__.return_value.infolist.return_value=[None]*7
            archive.return_value.__enter__.return_value.namelist.return_value=["payload.bin"]
            r=assess_rom_handoff(properties=CN,rom=Path(SKY_GLOBAL_208["filename"]),serial="s")
        self.assertTrue(r["rom"]["verified"])
        self.assertFalse(r["readiness"]["installation_admitted"])
        self.assertIn("2001",format_readiness(r))

    def test_unlocked_does_not_qualify_installer(self):
        r=assess_rom_handoff(properties=dict(CN,**{"ro.boot.flash.locked":"0"}),
                             rom=Path("/nonexistent.zip"),serial="s")
        self.assertFalse(r["readiness"]["physical_unlock_observed"])
        self.assertTrue(r["readiness"]["android_lock_reports_unlocked"])
        self.assertFalse(r["readiness"]["installer_qualified"])

    def test_physical_proof_requires_matching_serial_and_sky_product(self):
        unlocked_props=dict(CN,**{"ro.boot.flash.locked":"0"})
        base={"mode":"fastboot","verdict":"PASS","physical_unlock_proven":True,
              "serial":"s","observations":{"product":"sky","getvar_unlocked":"yes",
                                           "device_unlocked":"true"}}
        r=assess_rom_handoff(properties=unlocked_props,rom=Path("/nonexistent.zip"),
                             serial="s",sleeper_acceptance=base)
        self.assertTrue(r["readiness"]["physical_unlock_observed"])
        self.assertFalse(r["readiness"]["installation_admitted"])
        wrong=dict(base,serial="another")
        r2=assess_rom_handoff(properties=unlocked_props,rom=Path("/nonexistent.zip"),
                              serial="s",sleeper_acceptance=wrong)
        self.assertFalse(r2["readiness"]["physical_unlock_observed"])
        wrong_product=dict(base,observations=dict(base["observations"],product="other"))
        r3=assess_rom_handoff(properties=unlocked_props,rom=Path("/nonexistent.zip"),
                              serial="s",sleeper_acceptance=wrong_product)
        self.assertFalse(r3["readiness"]["physical_unlock_observed"])

    def test_stale_fastboot_pass_cannot_override_android_locked_state(self):
        proof={"mode":"fastboot","verdict":"PASS","physical_unlock_proven":True,
              "serial":"s","observations":{"product":"sky","getvar_unlocked":"yes",
                                           "device_unlocked":"true"}}
        r=assess_rom_handoff(properties=CN,rom=Path("/nonexistent.zip"),
                             serial="s",sleeper_acceptance=proof)
        self.assertFalse(r["readiness"]["physical_unlock_observed"])
        self.assertEqual(r["device"]["bootloader"],"locked")

    def test_bad_md5_blocks(self):
        with patch("mibu_rom_preflight._md5_file",return_value="0"*32), \
             patch("pathlib.Path.is_file",return_value=True), \
             patch("pathlib.Path.stat") as stat:
            stat.return_value.st_size=SKY_GLOBAL_208["size"]
            r=assess_rom_handoff(properties=CN,rom=Path(SKY_GLOBAL_208["filename"]),serial="s")
        self.assertFalse(r["rom"]["verified"])
        self.assertTrue(any("MD5" in x for x in r["reasons"]))

    def test_rom_format_never_claims_fastboot(self):
        r=assess_rom_handoff(properties=CN,rom=Path(SKY_GLOBAL_208["filename"]),serial="s")
        self.assertEqual(r["rom"]["format"],"full-recovery-ota")
        self.assertEqual(r["phone_writes"],0)

    def test_bridge_wires_to_existing_device_selection(self):
        source=(Path(__file__).parent/"mibu_sleeper.py").read_text()
        block=source.split("def rom_readiness_result(",1)[1].split("def _smart_play_descriptor(",1)[0]
        self.assertIn("check_device_ready()",block)
        self.assertIn("selected_adb_serial()",block)
        self.assertIn("assess_rom_handoff",block)
        self.assertNotIn("run_fastboot(",block)
        self.assertIn("inspect_physical_acceptance(",block)
        self.assertNotIn("erase",block)

    def test_ui_button_is_read_only_and_background(self):
        source=(Path(__file__).parent/"mibu_pc_helper_v3.py").read_text()
        self.assertIn('QPushButton("ROM Check")',source)
        self.assertIn('self.sleeper.rom_readiness_result(path)',source)
        self.assertIn('self.run_background(',source)

if __name__=="__main__":unittest.main()
