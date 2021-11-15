import os

file_to_find = 'file'
os.chdir('..')
# print(os.path.exists(file_to_find))
directories = [os.getcwd() + '/' + name for name in os.listdir(".") if os.path.isdir(name)
               and not name.startswith('.git') and name != '.idea']
fixed_directories = []
for directory in directories:
    fixed_directories.append([directory, False])
while True:
    all_visited = True
    for visited in fixed_directories:
        if not visited[1]:
            all_visited = False
    if all_visited:
        break
    for directory in fixed_directories:
        for name in os.listdir(directory[0]):
            path = directory[0] + '/' + name
            if os.path.isdir(path):
                fixed_directories.append([path, False])
                print(path)
        directory[1] = True
