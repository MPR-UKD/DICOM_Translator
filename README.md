# DICOM Translator
This Python script is used to move or copy DICOM files from one directory to another, saving each file in a new directory with the patient, exam date and sequence name and Dicom image number.

![plot](assets/show.gif)

**For example**, a file named **"IM-0001-0001.dcm"** could be renamed **"John_Doe/20221008_1019/CT_Scan/CT_San_dym_00001.dcm"** if the patient's name is "John Doe", the exam date is 10/08/2022 at 10:19 AM, and the sequence name is "CT_scan".

## Required libraries and Python version
- **Python:** 3.10+
- PyQt6
- tqdm
- pydicom
- ctypes

```basch
pip install -r requirements.txt
```

## Usage (with Python)
1. Start the script and select the path where the DICOM files are located.

```basch
python DICOMTranslator.py
```

2. Select whether the files should be copied or moved.
3. Select the number of CPU cores to be used for the operation.
4. Click Start Translation to start the operation.

When the process is complete, a message is displayed indicating the duration and the number of files recognized.

## Usage

### Windows:

#### Executable (`.exe`):

1. You can download the DICOMTranslator for Windows using the following links:
   - [Standalone Executable](/dist/DicomTranslator.exe)
   - [Directory Version](/dist/DICOMTranslator.zip)

   **Note**: The application can also be installed in the traditional manner. Simply run the [InstallerSetup](/Output/DicomTranslatorSetup.exe) from the `Output` directory and it will add **DicomTranslator** to your list of programs. If you wish to uninstall it later, you can do so like any other software.

2. If you're using the Directory Version (`one_dir_exe`), extract the contents of the zip file.
3. Launch the application by double-clicking on `DicomTranslator.exe`.
4. Choose if you want the files to be copied or moved.
5. Specify the number of CPU cores to utilize for the operation.
6. Click "Start Translation" to begin the process.

### macOS:

#### Executable (`.app`):

1. For macOS users, download the DICOMTranslator from the following link:
   - [Mac Version](/dist/DicomTranslator_mac.zip)

2. Extract the `.zip` file to get the `.app` application.
3. Open the application by double-clicking on `DicomTranslator.app`.
4. Choose if you want the files to be copied or moved.
5. Specify the number of CPU cores to utilize for the operation.
6. Click "Start Translation" to begin the process.

---

For both Windows and macOS:

Once the process concludes, a message will pop up indicating the duration taken and the number of files processed.

## Notes
Non-DICOM files are not moved or copied.
When working in "MOVE" mode, the original directory is deleted after the operation is completed.
When working in "COPY" mode, the original directory is retained.

## License
[GNU General Public License 3](https://www.gnu.org/licenses/gpl-3.0.html)

The GNU General Public License is a free, copyleft license for software and other kinds of works.

### Git hocks
Install "pre-commit"
```bash
pip install pre-commit
```

then run:
```bash
pre-commit install
```
# Support

If you really like this repository and find it useful, please consider (★) starring it, so that it can reach a broader audience of like-minded people.
