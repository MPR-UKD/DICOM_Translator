import os
import shutil
from pydicom import dcmread
from pydicom.errors import InvalidDicomError
from .utils_DICOM import rename_dicom_file


def dir_make(dir_path: str) -> None:
    """
    create directory if not exist

    :param dir_path: string - path of directory
    """
    try:
        os.mkdir(dir_path)
    except FileExistsError:
        pass


def move_dicom_file(input_tuple: tuple[str, str, str]) -> int:
    """
    move/ copy extracted dicom files to renamed file_name

    :param input_tuple: (file, target_dir, mode = ["COPY", "MOVE"])

    :return: int - 1 = dicom_file, 2 = non dicom_file
    """
    file, target_dir, mode = input_tuple
    try:
        ds = dcmread(file)
    except InvalidDicomError:
        return 0
    patient_name = str(ds.PatientName).replace("^^^", "").replace("^", "_") if 'PatientName' in ds \
        else "UnknownName"
    if patient_name == "UnknownName":
        return 0

    patient_id = ds.PatientID if 'PatientID' in ds else 'NA'
    new_file_name = rename_dicom_file(ds)
    date = ds.StudyDate if 'StudyDate' in ds else '0000000'
    time_point = ds.StudyTime if 'StudyTime' in ds else '0000000.0'
    time_point = time_point.split('.')[0][:4]
    date = date + '_' + time_point

    new_path = os.path.join(target_dir, patient_name + '_' + patient_id)
    dir_make(new_path)
    new_path = os.path.join(new_path, date)
    dir_make(new_path)
    new_file_name = new_file_name.replace('<', '').replace('>', '')
    dir_make(os.path.join(new_path, os.path.dirname(new_file_name)))
    if mode == 'COPY':
        shutil.copy2(file, os.path.join(new_path, new_file_name))
    else:
        try:
            os.rename(file, os.path.join(new_path, new_file_name))
        except FileExistsError:
            pass
    return 1
