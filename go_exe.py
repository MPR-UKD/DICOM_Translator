import os
import shutil

# python go_exe.py
if os.path.exists(r"./build"):
    shutil.rmtree(r"./build")
if os.path.exists(r"./dist"):
    shutil.rmtree(r"./dist")
os.system(
    "pyinstaller --collect-submodules=pydicom --icon=icon.ico DicomTranslator.py --onedir"
)
os.system(
    "pyinstaller --collect-submodules=pydicom --icon=icon.ico DicomTranslator.py --onefile"
)
