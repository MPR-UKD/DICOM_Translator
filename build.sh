#!/bin/bash

# PyInstaller for onefile
pyinstaller --onefile --windowed --collect-submodules=pydicom --icon=assets/icon.ico --add-data="assets/icon.ico;." --noconsole DicomTranslator.py --noconfirm

# PyInstaller for onedir
pyinstaller --onedir --windowed --collect-submodules=pydicom --icon=assets/icon.ico --add-data="assets/icon.ico;." --noconsole DicomTranslator.py --noconfirm
