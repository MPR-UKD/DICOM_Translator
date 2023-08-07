import ctypes
import glob
import os
import shutil
import sys
import tempfile
import threading
import time
from multiprocessing import Pool, cpu_count, freeze_support
import multiprocessing
from pathlib import Path

import win32con
import win32ui
from go_nifti.src.GoNifti import convert
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
)
from tqdm import tqdm

from utilities.loading import list_all_files, read_last_line
from utilities.saving import dir_make, move_dicom_file


def run_translation(
    path: str,
    mode: str,
    cpus: int,
    create_nii: bool = False,
    nii_mode: str = "save_in_separate_dir",
    nii_change: str = "Unchanged",
    compress: bool = True,
    update_progress=None,
) -> None:
    """
    main function of translation
    """
    target_path = path + "_translated"
    dir_make(target_path)
    t1 = time.time()
    files = list_all_files(path, target_path, mode)
    # print(f"{len(files)} files found")
    t2 = time.time()
    # print(f"Start: {mode} files to {target_path}")
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
            f"Translation amd Nifti generation completed \n"
            f"---------------------------------------------------------\n"
            f"Scan duration: {round((t2 - t1) * 100) / 100} s\n"
            f"Number of detected files: {len(files)} \n"
            f"     dicom files: {results.count(1)}\n"
            f"     non dicom files: {results.count(0)}\n"
            f"Duration to {mode.lower()} all dicom files: {round((t3 - t2) * 100) / 100} s \n"
            f"Duration to generate and save nifti files: {round((t4 - t3) * 100) / 100} s "
        )
    else:
        text = (
            f"Translation completed \n"
            f"---------------------------------------------------------\n"
            f"Scan duration: {round((t2 - t1) * 100) / 100} s\n"
            f"Number of detected files: {len(files)} \n"
            f"     dicom files: {results.count(1)}\n"
            f"     non dicom files: {results.count(0)}\n"
            f"Duration to {mode.lower()} all dicom files: {round((t3 - t2) * 100) / 100} s"
        )
    ctypes.windll.user32.MessageBoxW(
        0,
        text,
        "Completed",
        1,
    )


class FileDialogDemo(QWidget):
    def __init__(self, parent=None):
        super(FileDialogDemo, self).__init__(parent)
        layout = QVBoxLayout()
        self.setWindowTitle("Dicom Translator")
        self.settings = QSettings("DicomTranslator", "DicomTranslator")

        # ROW 1
        layout1 = QHBoxLayout()
        self.path_textbox = QLineEdit()
        load_button = QPushButton()
        load_button.setText("Load Path")
        load_button.clicked.connect(self.load_path)
        layout1.addWidget(self.path_textbox)
        layout1.addWidget(load_button)
        layout.addLayout(layout1)

        # ROW 2
        layout2 = QHBoxLayout()
        self.copy_button = QCheckBox()
        self.copy_button.setText("COPY mode")
        self.copy_button.setChecked(True)

        self.nii_button = QCheckBox()
        self.nii_button.setText("Create Nifti")
        self.nii_button.setChecked(False)

        self.mode_combo = QComboBox()
        self.mode_combo.setVisible(False)
        self.mode_combo.addItems(
            ["save_in_separate_dir", "save_in_folder", "save_in_exam_date"]
        )

        self.compress_combo = QComboBox()
        self.compress_combo.setVisible(False)
        self.compress_combo.addItems([".nii.gz", ".nii"])

        def change_combo(bool):
            self.mode_combo.setVisible(bool)
            self.mode_change_combo.setVisible(bool)
            self.compress_combo.setVisible(bool)

        self.mode_change_combo = QComboBox()
        self.mode_change_combo.setVisible(False)
        self.mode_change_combo.addItems(["Unchanged", "int32", "float32", "float64"])

        self.nii_button.clicked.connect(change_combo)
        text = QLabel()
        text.setText("\t Number of CPU cores being used:")
        self.cores = QSpinBox()
        self.cores.setMaximum(cpu_count())
        self.cores.setMinimum(1)
        self.cores.setValue(min(4, cpu_count()))

        run = QPushButton()
        run.setText("Start Translation")
        run.clicked.connect(self.run)
        layout2.addWidget(self.copy_button)
        layout2.addWidget(self.nii_button)
        layout2.addWidget(self.mode_combo)
        layout2.addWidget(self.mode_change_combo)
        layout2.addWidget(self.compress_combo)
        layout2.addWidget(text)
        layout2.addWidget(self.cores)
        layout2.addWidget(run)
        layout.addLayout(layout2)

        # ROW 3
        author = QLabel()
        author.setText(
            "Author: Karl Ludger Radke (Version 1.0) \n"
            "last update: 01/07/2023 \n"
            "ludger.radke@med.uni-duesseldorf.de"
        )
        layout.addWidget(author)

        # Create a QProgressBar instance
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
        # Set its maximum value
        self.progress_bar.setMaximum(100)
        # Hide it initially
        self.progress_bar.setVisible(False)
        # Add the progress bar to the layout
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
        )

    def load_path(self):
        self.progress_bar.setVisible(False)
        while True:
            path = QFileDialog.getExistingDirectory(
                self, "Select Directory", self.settings.value("lastPath", "")
            )
            if path == "":
                response = win32ui.MessageBox(
                    "No directory was selected. \n"
                    "Would you like to close the application?",
                    "Message",
                    win32con.MB_YESNO,
                )
                if response == win32con.IDYES:
                    sys.exit(0)
                elif response == win32con.IDNO:
                    continue
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
