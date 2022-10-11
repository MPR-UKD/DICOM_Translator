import unittest
from DicomTranslator import run_translation

if __name__ == '__main__':
    run_translation('test_data\DICOM', 'MOVE', 12)
