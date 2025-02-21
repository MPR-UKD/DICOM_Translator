import ctypes
import glob
import multiprocessing
import os
import shutil
import sys
import tempfile
import threading
import time
import zipfile
from multiprocessing import Pool, cpu_count, freeze_support
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from PyQt6.QtCore import QSettings
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
    QProgressBar,
    QMessageBox,
)
from go_nifti.src.GoNifti import convert
from tqdm import tqdm

from utilities.loading import list_all_files, read_last_line
from utilities.saving import dir_make, move_dicom_file

# Import for DICOM handling
from pydicom import dcmread
from pydicom.errors import InvalidDicomError

from utilities.utils_DICOM import rename_dicom_file


def run_translation(
    path: str,
    mode: str,
    cpus: int,
    create_nii: bool = False,
    nii_mode: str = "save_in_separate_dir",
    nii_change: str = "Unchanged",
    compress: bool = True,
    update_progress=None,
    direct_zip: bool = False,         # New flag: write directly to ZIP
    zip_file_path: str = None         # Optional ZIP file output path
) -> None:
    """
    Main function of translation.
    If direct_zip is True, DICOM files are written directly to a ZIP archive.
    Otherwise, files are processed as before.
    """
    if direct_zip:
        if create_nii:
            # Nifti conversion is not supported in direct ZIP mode.
            create_nii = False

        if zip_file_path is None:
            zip_file_path = path + "_translated.zip"

        t1 = time.time()
        # List all files; target dir is not needed for ZIP mode.
        files = list_all_files(path, None, mode)
        results = []
        # Create a lock for thread-safe access to the ZIP file.
        zip_lock = threading.Lock()
        with zipfile.ZipFile(zip_file_path, "w", compression=zipfile.ZIP_DEFLATED) as zipf:
            def write_to_zip(input_tuple: (str, str, str)) -> int:
                """
                Reads a file from the tuple, checks if it is a valid DICOM,
                then writes it directly into the ZIP file with the proper archive name.
                Returns 1 for a valid DICOM, 0 otherwise.
                """
                file, _, _ = input_tuple  # Unpack tuple to get the file path
                try:
                    ds = dcmread(file)
                except InvalidDicomError:
                    return 0
                patient_name = (
                    str(ds.PatientName).replace("^^^", "").replace("^", "_").replace("\x1f", "")
                    if "PatientName" in ds
                    else "UnknownName"
                )
                if patient_name == "UnknownName":
                    return 0

                patient_id = ds.PatientID.replace(":", "_") if "PatientID" in ds else "NA"
                new_file_name = rename_dicom_file(ds)
                date = ds.StudyDate if "StudyDate" in ds else "0000000"
                time_point = ds.StudyTime if "StudyTime" in ds else "0000000.0"
                time_point = time_point.split(".")[0][:4]
                date = date + "_" + time_point
                # Build archive name to mimic folder structure in ZIP
                arcname = os.path.join(
                    patient_name + "_" + patient_id,
                    date,
                    new_file_name.replace("<", "").replace(">", "")
                )
                # Use lock to ensure thread-safe write to the ZIP file.
                with zip_lock:
                    zipf.write(file, arcname=arcname)
                return 1

            # Use a ThreadPoolExecutor to write files concurrently.
            with ThreadPoolExecutor(max_workers=cpus) as executor:
                futures = {executor.submit(write_to_zip, file): file for file in files}
                for i, future in enumerate(as_completed(futures)):
                    res = future.result()
                    results.append(res)
                    if update_progress:
                        progress = int((i + 1) / len(files) * 100)
                        update_progress(progress)
        t2 = time.time()
        text = (
            f"Translation to ZIP completed \n"
            f"---------------------------------------------------------\n"
            f"Scan duration: {round((t2 - t1) * 100) / 100} s\n"
            f"Number of detected files: {len(files)} \n"
            f"     DICOM files: {results.count(1)}\n"
            f"     Non-DICOM files: {results.count(0)}"
        )
    else:
        target_path = path + "_translated"
        dir_make(target_path)
        t1 = time.time()
        files = list_all_files(path, target_path, mode)
        t2 = time.time()
        DEBUG = False
        if DEBUG:
            results = []
            for i, file in enumerate(files):
                move_dicom_file(file)
                progress = int((i + 1) / len(files) * 100)
                if update_progress:
                    update_progress(progress)
        else:
            output_path = Path(tempfile.gettempdir()) / "dicom_translator.txt"
            with open(output_path, "w") as file:
                pass

            def check_progress():
                while True:
                    last_line = read_last_line(output_path)
                    if "%" in last_line:
                        progress = int(last_line.split("%")[0].split("\r")[-1])
                        update_progress(progress)
                        if progress == 100:
                            break
                    time.sleep(0.1)

            progress_checker = threading.Thread(target=check_progress, daemon=True)
            progress_checker.start()

            with open(output_path, "w+") as file:
                with Pool(cpus) as p:
                    results = [
                        _
                        for _ in tqdm(
                            p.imap_unordered(move_dicom_file, files),
                            total=len(files),
                            file=file,
                        )
                    ]
        if mode == "MOVE":
            shutil.rmtree(path)
            shutil.move(target_path, path)
            dirs = glob.glob((path + os.sep + "*"))
            if len(dirs) == 1:
                shutil.move(
                    dirs[0], os.path.dirname(path) + os.sep + os.path.basename(dirs[0])
                )
            shutil.rmtree(path)
            target_path = path

        t3 = time.time()
        if create_nii:
            nii_change = None if nii_change == "Unchanged" else nii_change
            convert(
                root_folder=Path(target_path),
                mode=nii_mode,
                out_dtype=nii_change,
                n_processes=cpus,
                compress=compress,
            )
            t4 = time.time()
            text = (
                f"Translation and Nifti generation completed \n"
                f"---------------------------------------------------------\n"
                f"Scan duration: {round((t2 - t1) * 100) / 100} s\n"
                f"Number of detected files: {len(files)} \n"
                f"     DICOM files: {results.count(1)}\n"
                f"     Non-DICOM files: {results.count(0)}\n"
                f"Duration to {mode.lower()} all DICOM files: {round((t3 - t2) * 100) / 100} s \n"
                f"Duration to generate and save Nifti files: {round((t4 - t3) * 100) / 100} s "
            )
        else:
            text = (
                f"Translation completed \n"
                f"---------------------------------------------------------\n"
                f"Scan duration: {round((t2 - t1) * 100) / 100} s\n"
                f"Number of detected files: {len(files)} \n"
                f"     DICOM files: {results.count(1)}\n"
                f"     Non-DICOM files: {results.count(0)}\n"
                f"Duration to {mode.lower()} all DICOM files: {round((t3 - t2) * 100) / 100} s"
            )
    msg_box = QMessageBox()
    msg_box.setWindowTitle("Completed")
    msg_box.setText(text)
    msg_box.setIcon(QMessageBox.Icon.Information)
    msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
    msg_box.exec()


class FileDialogDemo(QWidget):
    def __init__(self, parent=None):
        super(FileDialogDemo, self).__init__(parent)
        layout = QVBoxLayout()
        self.setWindowTitle("Dicom Translator")
        self.settings = QSettings("DicomTranslator", "DicomTranslator")

        # ROW 1: Directory path selection
        layout1 = QHBoxLayout()
        self.path_textbox = QLineEdit()
        load_button = QPushButton("Load Path")
        load_button.clicked.connect(self.load_path)
        layout1.addWidget(self.path_textbox)
        layout1.addWidget(load_button)
        layout.addLayout(layout1)

        # ROW 2: Options
        layout2 = QHBoxLayout()
        self.copy_button = QCheckBox("COPY mode")
        self.copy_button.setChecked(True)

        self.nii_button = QCheckBox("Create Nifti")
        self.nii_button.setChecked(False)

        # New checkbox for direct ZIP mode.
        self.zip_checkbox = QCheckBox("Direct ZIP")
        self.zip_checkbox.setChecked(False)

        self.mode_combo = QComboBox()
        self.mode_combo.setVisible(False)
        self.mode_combo.addItems(
            ["save_in_separate_dir", "save_in_folder", "save_in_exam_date"]
        )

        self.compress_combo = QComboBox()
        self.compress_combo.setVisible(False)
        self.compress_combo.addItems([".nii.gz", ".nii"])

        def change_combo(checked: bool):
            self.mode_combo.setVisible(checked)
            self.mode_change_combo.setVisible(checked)
            self.compress_combo.setVisible(checked)

        self.mode_change_combo = QComboBox()
        self.mode_change_combo.setVisible(False)
        self.mode_change_combo.addItems(["Unchanged", "int32", "float32", "float64"])

        self.nii_button.clicked.connect(change_combo)
        text = QLabel("\t Number of CPU cores being used:")
        self.cores = QSpinBox()
        self.cores.setMaximum(cpu_count())
        self.cores.setMinimum(1)
        self.cores.setValue(min(4, cpu_count()))

        run = QPushButton("Start Translation")
        run.clicked.connect(self.run)
        layout2.addWidget(self.copy_button)
        layout2.addWidget(self.nii_button)
        layout2.addWidget(self.zip_checkbox)
        layout2.addWidget(self.mode_combo)
        layout2.addWidget(self.mode_change_combo)
        layout2.addWidget(self.compress_combo)
        layout2.addWidget(text)
        layout2.addWidget(self.cores)
        layout2.addWidget(run)
        layout.addLayout(layout2)

        # ROW 3: Author info
        author = QLabel(
            "Author: Karl Ludger Radke (Version 1.3) \n"
            "Last update: 14 March 2024 \n"
            "ludger.radke@med.uni-duesseldorf.de"
        )
        layout.addWidget(author)

        # Progress bar
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setStyleSheet(
            """
            QProgressBar {
                border: 2px solid grey;
                border-radius: 5px;
                text-align: center;
                color: white;
            }
            QProgressBar::chunk {
                background-color: green;
            }
            """
        )
        self.progress_bar.setMaximum(100)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        self.setLayout(layout)
        self.resize(1200, 100)
        self.show()

    def update_progress(self, value):
        self.progress_bar.setValue(value)
        QApplication.processEvents()

    def run(self):
        path = self.path_textbox.text()
        cores = self.cores.value()
        if self.copy_button.isChecked():
            mode = "COPY"
        else:
            mode = "MOVE"
        self.progress_bar.setVisible(True)
        run_translation(
            path,
            mode,
            cores,
            self.nii_button.isChecked(),
            self.mode_combo.currentText(),
            self.mode_change_combo.currentText(),
            self.compress_combo.currentText() == ".nii.gz",
            self.update_progress,
            direct_zip=self.zip_checkbox.isChecked()  # Pass new flag
        )

    def load_path(self):
        self.progress_bar.setVisible(False)
        while True:
            path = QFileDialog.getExistingDirectory(
                self, "Select Directory", self.settings.value("lastPath", "")
            )
            if path == "":
                response = QMessageBox.question(
                    self,
                    "Message",
                    "No directory was selected. \nWould you like to close the application?"
                )
                if response == QMessageBox.StandardButton.Yes:
                    sys.exit(0)
                elif response == QMessageBox.StandardButton.No:
                    return None
            self.settings.setValue("lastPath", Path(path).parent.as_posix())
            self.path_textbox.setText(path)
            break


if __name__ == "__main__":
    freeze_support()
    multiprocessing.set_start_method("spawn")
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    ex = FileDialogDemo()
    ex.show()
    sys.exit(app.exec())
