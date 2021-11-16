import os


def find_file(file_to_find):
    if not file_to_find or len(file_to_find) == 0:
        return []
    os.chdir('..')
    if os.path.exists(file_to_find):
        return [os.getcwd() + '/' + file_to_find]
    directories = [[os.getcwd() + '/' + name, False] for name in os.listdir(".") if os.path.isdir(name)]
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
    return list(set(files))
