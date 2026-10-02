from __future__ import annotations

import time
import unittest
import uuid

from PySide6.QtCore import QCoreApplication

from mibu_single_instance import SingleInstanceGate


class SingleInstanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QCoreApplication.instance() or QCoreApplication([])

    def test_second_instance_activates_existing_owner(self) -> None:
        name = "MIBU-test-" + uuid.uuid4().hex
        first = SingleInstanceGate(name)
        second = SingleInstanceGate(name)
        activated: list[bool] = []
        first.activate_requested.connect(lambda: activated.append(True))
        try:
            self.assertTrue(first.acquire())
            self.assertFalse(second.acquire())
            deadline = time.monotonic() + 1.0
            while not activated and time.monotonic() < deadline:
                self.app.processEvents()
                time.sleep(0.01)
            self.assertEqual([True], activated)
        finally:
            second.close()
            first.close()


if __name__ == "__main__":
    unittest.main()
