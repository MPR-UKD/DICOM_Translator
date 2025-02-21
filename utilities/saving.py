import shutil

import os
import time
import threading
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from pydicom import dcmread
from pydicom.errors import InvalidDicomError
from utilities.loading import list_all_files
from utilities.utils_DICOM import rename_dicom_file



def dir_make(dir_path: str) -> None:
    """
    Create directory if it does not exist.

    Args:
        dir_path (str): path of directory
    """
    try:
        os.mkdir(dir_path)
    except FileExistsError:
        pass


def move_dicom_file(input_tuple: (str, str, str)) -> int:
    """
    Move or copy extracted DICOM files to renamed file_name.

    Args:
        input_tuple (tuple): (file, target_dir, mode = ["COPY", "MOVE"])

    Returns:
        int: 1 if DICOM file, 0 if non-DICOM file
    """

    file, target_dir, mode = input_tuple
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

    patient_id = ds.PatientID.replace(':', '_') if "PatientID" in ds else "NA"
    new_file_name = rename_dicom_file(ds)
    date = ds.StudyDate if "StudyDate" in ds else "0000000"
    time_point = ds.StudyTime if "StudyTime" in ds else "0000000.0"
    time_point = time_point.split(".")[0][:4]
    date = date + "_" + time_point

    new_path = os.path.join(target_dir, patient_name + "_" + patient_id)
    dir_make(new_path)
    new_path = os.path.join(new_path, date)
    dir_make(new_path)
    new_file_name = new_file_name.replace("<", "").replace(">", "")
    dir_make(os.path.join(new_path, os.path.dirname(new_file_name)))
    if mode == "COPY":
        shutil.copy2(file, os.path.join(new_path, new_file_name))
    else:
        try:
            os.rename(file, os.path.join(new_path, new_file_name))
        except FileExistsError:
            pass
    return 1

def write_dicom_files_to_zip(
    source_path: str,
    cpus: int,
    update_progress=None,
    zip_file_path: str = None
) -> str:
    """
    Write valid DICOM files directly to a ZIP archive concurrently.

    Args:
        source_path (str): Source directory path.
        cpus (int): Number of threads to use.
        update_progress (callable, optional): Callback to update progress.
        zip_file_path (str, optional): Output ZIP file path.

    Returns:
        str: Summary of the ZIP operation.
    """
    if zip_file_path is None:
        zip_file_path = f"{source_path}_translated.zip"

    # List all files; target_dir and mode are not needed in ZIP mode.
    files = list_all_files(source_path, None, None)
    total_files = len(files)
    results = []
    zip_lock = threading.Lock()
    t_start = time.time()

    with zipfile.ZipFile(zip_file_path, "w", compression=zipfile.ZIP_DEFLATED) as zipf:
        def process_file(file_tuple: tuple) -> int:
            file_path = file_tuple[0]
            try:
                ds = dcmread(file_path)
            except InvalidDicomError:
                return 0
            patient_name = getattr(ds, "PatientName", "UnknownName")
            if patient_name == "UnknownName":
                return 0
            # Clean up the patient name.
            patient_name = str(patient_name).replace("^^^", "").replace("^", "_").replace("\x1f", "")
            patient_id = getattr(ds, "PatientID", "NA").replace(":", "_")
            new_file_name = rename_dicom_file(ds)
            date = getattr(ds, "StudyDate", "0000000")
            time_point = str(getattr(ds, "StudyTime", "0000000.0")).split(".")[0][:4]
            date_time = f"{date}_{time_point}"
            # Construct archive name mimicking a folder structure.
            arcname = os.path.join(
                f"{patient_name}_{patient_id}",
                date_time,
                new_file_name.replace("<", "").replace(">", "")
            )
            with zip_lock:
                zipf.write(file_path, arcname=arcname)
            return 1

        with ThreadPoolExecutor(max_workers=cpus) as executor:
            futures = {executor.submit(process_file, file_tuple): file_tuple for file_tuple in files}
            for i, future in enumerate(as_completed(futures), start=1):
                try:
                    result = future.result()
                    results.append(result)
                except Exception:
                    results.append(0)
                if update_progress:
                    update_progress(int(i / total_files * 100))

    t_end = time.time()
    summary = (
        f"Translation to ZIP completed\n"
        f"---------------------------------------\n"
        f"Total files processed: {total_files}\n"
        f"    DICOM files: {results.count(1)}\n"
        f"    Non-DICOM files: {results.count(0)}\n"
        f"Duration: {round(t_end - t_start, 2)} s\n"
        f"Output ZIP: {Path(zip_file_path).resolve()}"
    )
    return summary
