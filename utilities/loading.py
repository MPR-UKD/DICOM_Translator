import os


def list_all_files(path: str, target_dir: str = None, mode: str = None):
    """
    Lists all files in a directory

    :param path: path of directory
    :param target_dir: path of target directory - is added here to improve multiprocessing
    :param mode: mode = [COPY or MOVE] - is added here to improve multiprocessing

    :return: list - with all files
    """

    path_to_files = []
    for root, dirs, files in os.walk(path):
        for file in files:
            path_to_files.append((os.path.join(root, file), target_dir, mode))
    return path_to_files
