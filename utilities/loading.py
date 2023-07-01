import os


def list_all_files(path: str, target_dir: str = None, mode: str = None) -> list[tuple]:
    """
    Lists all files in a directory.

    Args:
        path: path of directory
        target_dir: path of target directory (optional)
        mode: mode = [COPY or MOVE] (optional)

    Returns:
        list: list of all files
    """

    path_to_files = []
    for root, dirs, files in os.walk(path):
        for file in files:
            path_to_files.append((os.path.join(root, file), target_dir, mode))
    return path_to_files

def read_last_line(file_path):
    with open(file_path, 'r') as file:
        line = [_ for _ in  file.readlines()]
        try:
            return line[-1].split(r'\n,')[-1]
        except IndexError:
            return ""