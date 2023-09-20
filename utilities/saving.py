import os
import shutil

from pydicom import dcmread
from pydicom.errors import InvalidDicomError

from .utils_DICOM import rename_dicom_file


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
