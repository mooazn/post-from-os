import os

# this method finds a specified file (if it exists) in the parent directory of the current directory.
# Basically, it only goes one level up and attempts to find the file.


def find(file_to_find):
    home_dir = os.getcwd()
    if not file_to_find or len(file_to_find) == 0:
        return None
    if os.path.exists(file_to_find):
        return file_to_find
    os.chdir('..')
    if os.path.exists(file_to_find):
        os.chdir(home_dir)
        return os.getcwd() + '/' + file_to_find
    directories = [[os.getcwd() + '/' + name, False] for name in os.listdir('.') if os.path.isdir(name)]
    files = []
    while True:
        all_visited = True
        for visited in directories:
            if not visited[1]:
                all_visited = False
                break
        if all_visited:
            break
        for directory in directories:
            for name in os.listdir(directory[0]):
                cur_path = directory[0] + '/' + name
                path_to_file = directory[0] + '/' + file_to_find
                if os.path.exists(path_to_file):
                    files.append(path_to_file)
                if os.path.isdir(cur_path):
                    directories.append([cur_path, False])
            directory[1] = True
    result = list(set(files))
    if len(result) > 1:
        print('More than 1 file returned. Narrow down your search. Files returned:', result)
        os.chdir(home_dir)
        return None
    os.chdir(home_dir)
    return None if len(result) == 0 else result[0]
