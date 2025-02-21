import os
import sys
import time
import shutil
import multiprocessing
import concurrent.futures
from pathlib import Path

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

from utilities.loading import list_all_files
from utilities.saving import move_dicom_file, write_dicom_files_to_zip
from go_nifti.src.GoNifti import convert


def run_translation(
    path: str,
    mode: str,
    cpus: int,
    create_nii: bool = False,
    nii_mode: str = "save_in_separate_dir",
    nii_change: str = "Unchanged",
    compress: bool = True,
    update_progress=None,
    direct_zip: bool = False,
    zip_file_path: str = None
) -> None:
    """
    Main function for translation.
    If direct_zip is True, valid DICOM files are written directly to a ZIP archive.
    Otherwise, files are processed by copying/moving them into a target directory.
    """
    if direct_zip:
        if create_nii:
            # Nifti conversion is not supported in direct ZIP mode.
            create_nii = False
        t1 = time.time()
        # Delegate ZIP processing to the separated module.
        text = write_dicom_files_to_zip(path, cpus, update_progress, zip_file_path)
        t2 = time.time()
        text += f"\nTotal duration: {round(t2 - t1, 2)} s"
    else:
        target_path = f"{path}_translated"
        os.makedirs(target_path, exist_ok=True)
        t1 = time.time()
        files = list_all_files(path, target_path, mode)
        t2 = time.time()
        results = []
        total_files = len(files)
        # Use ProcessPoolExecutor for parallel file processing.
        with concurrent.futures.ProcessPoolExecutor(max_workers=cpus) as executor:
            futures = {executor.submit(move_dicom_file, file_tuple): file_tuple for file_tuple in files}
            for i, future in enumerate(concurrent.futures.as_completed(futures), start=1):
                try:
                    result = future.result()
                    results.append(result)
                except Exception:
                    results.append(0)
                if update_progress:
                    update_progress(int(i / total_files * 100))
        if mode.upper() == "MOVE":
            # Cleanup: remove original directory if in MOVE mode.
            shutil.rmtree(path, ignore_errors=True)
            shutil.move(target_path, path)
            # Handle potential nested directories.
            dirs = [d for d in os.listdir(path) if os.path.isdir(os.path.join(path, d))]
            if len(dirs) == 1:
                shutil.move(os.path.join(path, dirs[0]),
                            os.path.join(os.path.dirname(path), os.path.basename(dirs[0])))
            shutil.rmtree(path, ignore_errors=True)
            target_path = path
        t3 = time.time()
        summary = (
            f"Translation completed\n"
            f"---------------------------------------\n"
            f"Scan duration: {round(t2 - t1, 2)} s\n"
            f"Total files: {total_files}\n"
            f"    DICOM files: {results.count(1)}\n"
            f"    Non-DICOM files: {results.count(0)}\n"
            f"File processing duration: {round(t3 - t2, 2)} s"
        )
        if create_nii:
            nii_dtype = None if nii_change == "Unchanged" else nii_change
            t3a = time.time()
            convert(
                root_folder=Path(target_path),
                mode=nii_mode,
                out_dtype=nii_dtype,
                n_processes=cpus,
                compress=compress,
            )
            t4 = time.time()
            summary += f"\nNifti generation duration: {round(t4 - t3a, 2)} s"
        text = summary

    # Show summary to the user.
    msg_box = QMessageBox()
    msg_box.setWindowTitle("Completed")
    msg_box.setText(text)
    msg_box.setIcon(QMessageBox.Icon.Information)
    msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
    msg_box.exec()


class FileDialogDemo(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Dicom Translator")
        self.settings = QSettings("DicomTranslator", "DicomTranslator")
        layout = QVBoxLayout()

        # Row 1: Directory selection
        layout1 = QHBoxLayout()
        self.path_textbox = QLineEdit()
        load_button = QPushButton("Load Path")
        load_button.clicked.connect(self.load_path)
        layout1.addWidget(self.path_textbox)
        layout1.addWidget(load_button)
        layout.addLayout(layout1)

        # Row 2: Options
        layout2 = QHBoxLayout()
        self.copy_button = QCheckBox("COPY mode")
        self.copy_button.setChecked(True)

        self.nii_button = QCheckBox("Create Nifti")
        self.nii_button.setChecked(False)

        # Checkbox for direct ZIP mode.
        self.zip_checkbox = QCheckBox("Direct ZIP")
        self.zip_checkbox.setChecked(False)

        self.mode_combo = QComboBox()
        self.mode_combo.setVisible(False)
        self.mode_combo.addItems(["save_in_separate_dir", "save_in_folder", "save_in_exam_date"])

        self.compress_combo = QComboBox()
        self.compress_combo.setVisible(False)
        self.compress_combo.addItems([".nii.gz", ".nii"])

        self.mode_change_combo = QComboBox()
        self.mode_change_combo.setVisible(False)
        self.mode_change_combo.addItems(["Unchanged", "int32", "float32", "float64"])

        def toggle_nii_options(checked: bool):
            self.mode_combo.setVisible(checked)
            self.mode_change_combo.setVisible(checked)
            self.compress_combo.setVisible(checked)

        self.nii_button.clicked.connect(toggle_nii_options)

        cores_label = QLabel("Number of CPU cores:")
        self.cores = QSpinBox()
        self.cores.setMinimum(1)
        self.cores.setMaximum(multiprocessing.cpu_count())
        self.cores.setValue(min(4, multiprocessing.cpu_count()))

        run_button = QPushButton("Start Translation")
        run_button.clicked.connect(self.run)

        layout2.addWidget(self.copy_button)
        layout2.addWidget(self.nii_button)
        layout2.addWidget(self.zip_checkbox)
        layout2.addWidget(self.mode_combo)
        layout2.addWidget(self.mode_change_combo)
        layout2.addWidget(self.compress_combo)
        layout2.addWidget(cores_label)
        layout2.addWidget(self.cores)
        layout2.addWidget(run_button)
        layout.addLayout(layout2)

        # Row 3: Author information
        author_label = QLabel(
            "Author: Karl Ludger Radke (Version 1.4)\n"
            "Last update: 21 Feb 2025\n"
            "ludger.radke@med.uni-duesseldorf.de"
        )
        layout.addWidget(author_label)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(100)
        self.progress_bar.setVisible(False)
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
        layout.addWidget(self.progress_bar)
        self.setLayout(layout)
        self.resize(1200, 100)

    def update_progress(self, value: int):
        self.progress_bar.setValue(value)
        QApplication.processEvents()

    def run(self):
        path = self.path_textbox.text().strip()
        if not path:
            QMessageBox.warning(self, "Warning", "Please select a valid directory.")
            return
        cores = self.cores.value()
        mode = "COPY" if self.copy_button.isChecked() else "MOVE"
        self.progress_bar.setVisible(True)
        run_translation(
            path,
            mode,
            cores,
            create_nii=self.nii_button.isChecked(),
            nii_mode=self.mode_combo.currentText(),
            nii_change=self.mode_change_combo.currentText(),
            compress=self.compress_combo.currentText() == ".nii.gz",
            update_progress=self.update_progress,
            direct_zip=self.zip_checkbox.isChecked()
        )

    def load_path(self):
        self.progress_bar.setVisible(False)
        selected_path = QFileDialog.getExistingDirectory(
            self, "Select Directory", self.settings.value("lastPath", "")
        )
        if not selected_path:
            response = QMessageBox.question(
                self,
                "Message",
                "No directory was selected.\nWould you like to close the application?"
            )
            if response == QMessageBox.StandardButton.Yes:
                sys.exit(0)
            return
        self.settings.setValue("lastPath", str(Path(selected_path).parent))
        self.path_textbox.setText(selected_path)


if __name__ == "__main__":
    multiprocessing.freeze_support()
    multiprocessing.set_start_method("spawn")
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    demo = FileDialogDemo()
    demo.show()
    sys.exit(app.exec())
