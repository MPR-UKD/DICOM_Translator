#!/bin/bash

# PyInstaller for onefile
pyinstaller --onefile --windowed --collect-submodules=pydicom --icon=icon.ico --add-data="./icon.ico;." --noconsole DicomTranslator.py --noconfirm

# PyInstaller for onedir
pyinstaller --onedir --windowed --collect-submodules=pydicom --icon=icon.ico --add-data="./icon.ico;." --noconsole DicomTranslator.py --noconfirm
