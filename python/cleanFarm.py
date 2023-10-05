from pathlib import Path
from shutil import copyfile, rmtree
from os import remove, path, listdir


# Used to read the contents of a file
def readFile(file_path):
    with open(file_path, 'r') as file:
        data = file.read()
        file.close()    
    return data


# Used to erase a file's content
def emptyFile(file_path):
    with open(file_path, 'w') as file:
        file.close()


# Main controller function
def main():
    # Get the scene dir and job's name from the database into variables
    scene_db_path = Path.cwd() / 'db' / 'current_scene_path.txt'
    current_scene_dir = readFile(scene_db_path)
    job_name_path = Path.cwd() / 'db' / 'job_name.txt'
    job_name = readFile(job_name_path)

    # Empty these files
    emptyFile(scene_db_path)
    emptyFile(job_name_path)

    # Delete the ps1 files from the directory
    dir_path = Path(current_scene_dir).parent
    try:
        remove(dir_path / 'node.ps1')
        remove(dir_path / 'machine.ps1')
    except:
        pass

    # Copy the rendered files from node farm output to machine farm output
    node_output_path = Path('//elio-node/farm_output') / job_name
    machine_output_path = Path('C:/farm_output') / job_name
    for filename in listdir(node_output_path):
        file = path.join(node_output_path, filename)
        # checking if it is a file
        if path.isfile(file):
            dest_path = machine_output_path / filename
            copyfile(file, dest_path)

    # Delete farm output folder if the files have successfully been copied
    rmtree(node_output_path)


if __name__ == '__main__':
    main()
