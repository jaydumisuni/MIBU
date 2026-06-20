# Qt6 Helper Build Notes

The current Qt6 helper is a visual and workflow shell. It is intentionally small and centered, matching the approved mockup direction.

## Local run

```powershell
cd MIBU
python -m venv .venv
.\.venv\Scripts\activate
pip install -r pc-helper\qt6\requirements.txt
python pc-helper\qt6\mibu_pc_helper_ui.py
```

## Later packaging direction

When the UI and actions are complete, package the helper with your PC builder or PyInstaller/Nuitka.

The final installer should include:

- the Qt6 helper executable
- platform-tools/ADB or a check that ADB already exists
- MIBU.apk build output
- a short local guide

## Window rule

Keep it compact. Do not turn it into a giant full-screen control panel.
