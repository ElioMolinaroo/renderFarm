import sys
from pathlib import Path
from re import findall
from subprocess import Popen, PIPE
from shutil import copyfile

FRAMES_PER_PACKET = 5
NODE_PS1_PATH = Path.cwd() / 'utilities' / 'node.ps1'
MACHINE_PS1_PATH = Path.cwd() / 'utilities' / 'machine.ps1'


# Used to override the contents of the old file with the updated version
def overrideWriteFile(new_data, file_path):
	with open(file_path, 'w') as file:
		file.write(new_data)
		file.close()
		

# Ping function to get elio-node status
def ping (host,ping_count):
    for ip in host:
        data = ""
        output= Popen(f'ping "{ip}" -n {ping_count}', stdout=PIPE, encoding="utf-8")

        for line in output.stdout:
            data = data + line
            ping_test = findall("TTL", data)

        if ping_test:
            return True
        else:
            return False


# Formats render commands with arguments to be written in batch file
def formatRenderCommand(scene_path: str, output_dir: str, job_name: str, camera: str, first_frame: int, last_frame: int):
    # Extract scene name from scene path
    scene_name = str(Path(scene_path).as_posix()).split('/')[-1]
    final_output_dir = Path(output_dir) / job_name

    # Generate final command
    render_command = f'render -r renderman -rd "{final_output_dir}" -t 0 -s {first_frame} -e {last_frame} -cam {camera} "{scene_name}"'

    return render_command


# Asks for a scene path and checks if it is located in the 3d3 folder on main machine
def scenePathChecker(scene_path: str):
    path_test = str(Path(scene_path).as_posix()).lower()
    if 'c:/3d3' not in path_test:
        print("The scene path you provided isn't located in the 3d3 folder...")
        sys.exit()
    else:
        return scene_path


# Asks user for a job name and scene path
def getUserOptions():
	# Check for the scene path
    scene_path = 'Gfs'
    while Path(scene_path).exists() is False:
        scene_path = input("Path to your scene (must be located in 3D3 folder): ")

    # Checks if the scene path is located in the right directory
    scene_path = scenePathChecker(scene_path)

    # Asks user for job name
    job_name = input("Enter a job name: ")
    if len(job_name) == 0:
         job_name = 'lambda_job'

    # Ask user for number of machines
    machine_count = ''
    correct_answers = ["1", "2"]
    while machine_count not in correct_answers:
        machine_count = input("Number of machines to render (1 or 2): ")
    
    # Ask user for first frame
    first_frame = 'temp'
    while first_frame.isdigit() is False:
        first_frame = input("First frame: ")
    first_frame = int(first_frame)

    # Ask user for last frame
    last_frame = 'temp'
    while last_frame.isdigit() is False:
        last_frame = input("Last frame: ")
    last_frame = int(last_frame)

    # Ask user the render camera they want to use
    cam_name = ''
    while len(cam_name) == 0:
        cam_name = input("Enter a camera name: ")

    return [job_name, machine_count, first_frame, last_frame, cam_name, scene_path]


# Separates the frames in packets
def packetsSplitter(first_frame: int, last_frame: int):
        # Frame count
        frame_count = last_frame - first_frame + 1

        # if last packet doesn't have a regular number of frames
        if frame_count % FRAMES_PER_PACKET != 0:
            full_packets_number = int(frame_count / FRAMES_PER_PACKET)
            last_packet_frames = frame_count % FRAMES_PER_PACKET
        # if last packet has a regular number of frames
        else:
            full_packets_number = int(frame_count / FRAMES_PER_PACKET)
            last_packet_frames = 0

        # init the packets variables
        packets_frames = []
        temp_first = first_frame-1
        temp_last = last_frame
        # Create a list of packet frames
        for i in range(full_packets_number):
             final_first = temp_first + 1
             final_last = temp_first + FRAMES_PER_PACKET
             packets_frames.append([final_first, final_last])
            # Offset the frames number to update the new iteration
             temp_first = final_last

        # Take care of last frames if they don't fit in the frames per packet
        if last_packet_frames != 0:
             ultimate_first = temp_first + 1
             ultimate_last = temp_first + last_packet_frames
             ultimate_packet = [ultimate_first, ultimate_last]
             packets_frames.append(ultimate_packet)
        
        return packets_frames


# Distributes packets by giving twice as many to the machine
def packetsDistribution(packets):
    packets_number = len(packets)
    
    # Generate node packets list
    node_packets = []
    for i in range(0, packets_number, 4):
            node_packets.append(packets[i])

    # Generate machine packets list
    machine_packets = []
    for packet in packets:
            if packet not in node_packets:
                machine_packets.append(packet)

    return node_packets, machine_packets


# Controller code for single farm ps1 code generation
def singleFarm(packets, job_name, scene_path, cam_name):
     # Create node job output directory
        final_output_dir = str(Path("C:\FARM_OUTPUT") / job_name).replace('C:\\', '//elio-node/')
        final_output_dir = Path(final_output_dir)
        final_output_dir.mkdir()
        
        # Generate a list of renderman commands
        rman_commands_list = []
        for packet in packets:
            current_command = formatRenderCommand(scene_path, "C:\FARM_OUTPUT", job_name, cam_name, packet[0], packet[1])
            rman_commands_list.append(current_command)

        # Generate powershell code
        final_rman_command = '; '.join(rman_commands_list)
        ps1_code = f'''{final_rman_command}
Write-Host "Batch render terminated successfully..."
pause'''

        # Write command to node file
        overrideWriteFile(ps1_code, NODE_PS1_PATH)


# Controller code for dual farm ps1 code generation
def dualFarm(packets, job_name, scene_path, cam_name):
     # Generate packets distribution
        node_packets, machine_packets = packetsDistribution(packets)

        # Create node job output directory
        node_output_dir = str(Path("C:\FARM_OUTPUT") / job_name).replace('C:\\', '//elio-node/')
        node_output_dir = Path(node_output_dir)
        node_output_dir.mkdir()
        # Create machine job output directory
        machine_output_dir = Path("C:\FARM_OUTPUT") / job_name
        machine_output_dir.mkdir()

        # Generate a list of renderman commands for machine
        machine_rman_commands_list = []
        for machine_packet in machine_packets:
            current_command = formatRenderCommand(scene_path, "C:\FARM_OUTPUT", job_name, cam_name, machine_packet[0], machine_packet[1])
            machine_rman_commands_list.append(current_command)
        # Generate powershell code for machine
        machine_final_rman_command = '; '.join(machine_rman_commands_list)
        machine_ps1_code = f'''{machine_final_rman_command}
Write-Host "Batch render terminated successfully..."
pause'''

        # Generate a list of renderman commands for node
        node_rman_commands_list = []
        for node_packet in node_packets:
            current_command = formatRenderCommand(scene_path, "C:\FARM_OUTPUT", job_name, cam_name, node_packet[0], node_packet[1])
            node_rman_commands_list.append(current_command)
        # Generate powershell code for node
        node_final_rman_command = '; '.join(node_rman_commands_list)
        node_ps1_code = f'''{node_final_rman_command}
Write-Host "Batch render terminated successfully..."
pause'''

        # Write command to machine file
        overrideWriteFile(machine_ps1_code, MACHINE_PS1_PATH)

        # Write command to node file
        overrideWriteFile(node_ps1_code, NODE_PS1_PATH)


# Controller function for the batch script writing
def main():
    print("Welcome to the farm!\n")
    # Check if node is running
    node_status = ping(["192.168.1.3"], 3)
    if node_status is False:
        print("The node isn't on the network, try to start it and try again...")
        sys.exit()
    else:
        print("Node is connected to the network, continuing...\n")

    # Get user options
    job_name, machine_count, first_frame, last_frame, cam_name, scene_path = getUserOptions()

    # Copy scene path to database
    current_scene_db_path = Path.cwd() / 'db' / 'current_scene_path.txt'
    overrideWriteFile(str(Path(scene_path).as_posix()), current_scene_db_path)
    # Copy job's name to database
    job_name_db_path = Path.cwd() / 'db' / 'job_name.txt'
    overrideWriteFile(job_name, job_name_db_path)

    # Create packets
    packets = packetsSplitter(first_frame, last_frame)

    # Check for potential packet distribution
    if machine_count == "1":
        # Generate the ps1 scripts in the utilities folder
        singleFarm(packets, job_name, scene_path, cam_name)
        
        # Copy ps1 file to scene directory
        node_scene_dir = Path(scene_path).parent / 'node.ps1'
        copyfile(NODE_PS1_PATH, node_scene_dir)

    # Packet distribution if rendering on 2 machines
    elif machine_count == "2":
        # Generate the ps1 scripts in the utilities folder
        dualFarm(packets, job_name, scene_path, cam_name)

        # Copy ps1 files to scene directory
        node_scene_dir = Path(scene_path).parent / 'node.ps1'
        copyfile(NODE_PS1_PATH, node_scene_dir)
        machine_scene_dir = Path(scene_path).parent / 'machine.ps1'
        copyfile(MACHINE_PS1_PATH, machine_scene_dir)
	

if __name__ == "__main__":
     main()
