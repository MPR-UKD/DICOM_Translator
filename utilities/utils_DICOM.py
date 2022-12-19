import os
import re

from pydicom import Dataset


def extract_series(ds: Dataset) -> str:
    """
    Extract the series description and UID from a pydicom dataset.

    Args:
        ds (Dataset): pydicom dataset

    Returns:
        str: SeriesDescription + '_' + SeriesInstanceUID
    """

    SeriesDescription = (
        re.sub(":", "", ds.SeriesDescription)
        if "SeriesDescription" in ds
        else "NoSeriesDescription"
    )
    SeriesInstanceUID = (
        ds.SeriesInstanceUID.split(".0.0", 1)[0][-5:]
        if "SeriesInstanceUID" in ds
        else "0042"
    )
    SeriesDescription = (
        SeriesDescription.replace(" ", "")
        .replace("d.v.", "")
        .replace(".", "")
        .replace("/", "")
    )
    return str(SeriesDescription + "_" + SeriesInstanceUID)


def rename_dicom_file(ds: Dataset) -> str:
    """
    Rename a DICOM file.

    Args:
        ds (Dataset): pydicom dataset

    Returns:
        str: path string - dir_name\file_name
    """

    InstanceNumber = ds.InstanceNumber if "InstanceNumber" in ds else 0
    Series = ds.SeriesNumber if "SeriesNumber" in ds else 0

    if InstanceNumber is None:
        SL = "0"
    elif InstanceNumber < 10:
        SL = "0000" + str(InstanceNumber)
    elif InstanceNumber < 100:
        SL = "000" + str(InstanceNumber)
    elif InstanceNumber < 1000:
        SL = "00" + str(InstanceNumber)
    elif InstanceNumber < 10000:
        SL = "0" + str(InstanceNumber)
    else:
        SL = str(InstanceNumber)

    return os.path.join(
        str(Series) + "_" + extract_series(ds),
        extract_series(ds) + "_dyn_" + SL + ".dcm",
    )
