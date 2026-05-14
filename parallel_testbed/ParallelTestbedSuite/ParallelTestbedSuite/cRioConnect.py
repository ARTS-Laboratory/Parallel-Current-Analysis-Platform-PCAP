import paramiko
import time
import os
import re
# Remote server configuration
REMOTE_HOST = "169.254.94.201"
USERNAME = 'admin'
PASSWORD = ''

# Remote and local root directories
REMOTE_ROOT = "/media/mmcblk0p1"
LOCAL_ROOT = "C:/Users/malichi/Desktop/ParallelTestbedSuite"

# Polling interval in seconds
POLL_INTERVAL = 10


def extract_cycle_number(filename):
    """Extract the first integer found in the filename as the cycle number.
    If no match is found, return the previously extracted cycle number."""
    match = re.search(r"Cycle\s*(\d+)", filename)
    if match:
        cycle_number = int(match.group(1))
        extract_cycle_number.previous = cycle_number  # store for future use
        return cycle_number
    else:
        return getattr(extract_cycle_number, 'previous', None)


def get_remote_files(sftp, folder):
    """Return a dictionary of files in the remote folder with their modification times."""
    files = {}
    try:
        for attr in sftp.listdir_attr(folder):
            files[attr.filename] = attr.st_mtime
    except IOError:
        pass  # Folder might not exist yet
    return files

def download_file_with_header(sftp, remote_file_path, local_file_path, test_folder, source_type, cycle_number): 
    """Download a file and add a header indicating its test folder, source type, and cycle number.""" 
    os.makedirs(os.path.dirname(local_file_path), exist_ok=True) 
    sftp.get(remote_file_path, local_file_path) 
    print(f"Downloaded: {remote_file_path} -> {local_file_path} (Cycle {cycle_number}) (Source {source_type})")

    header_columns = [
        "Timestamp", "Current", "Voltage", "Current_1", "Current_2", "Current_3",
        "Strain_1", "Strain_2", "Strain_3", "Temp_1", "Temp_2", "Temp_3", "Temp",
        "Voltage_1", "Voltage_2", "Voltage_3", f"Cycle_{cycle_number}"
    ]
    header_line = "\t".join(header_columns) + "\n"

    with open(local_file_path, 'r+') as f:
        content = f.read()
        f.seek(0, 0)
        f.write(header_line + content)

def get_test_folders(sftp):
    """Return a list of test folders under REMOTE_ROOT."""
    test_folders = []
    for attr in sftp.listdir_attr(REMOTE_ROOT):
        if attr.filename.startswith("test") and attr.st_mode & 0o040000:  # Directory check
            test_folders.append(attr.filename)
    return test_folders

def monitor_and_transfer():
    """Monitor all test folders and sync charge/discharge files to matching local folders."""
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(REMOTE_HOST, username=USERNAME, password=PASSWORD)
    sftp = ssh.open_sftp()

    files_last_seen = {}

    try:
        while True:
            test_folders = get_test_folders(sftp)

            for test_folder in test_folders:
                for subfolder in ["charge", "discharge"]:
                    remote_folder = f"{REMOTE_ROOT}/{test_folder}/{subfolder}"
                    current_files = get_remote_files(sftp, remote_folder)

                    for filename, mod_time in current_files.items():
                        remote_path = f"{remote_folder}/{filename}"
                        local_folder = os.path.join(LOCAL_ROOT, test_folder)
                        local_path = os.path.join(local_folder, filename)

                        file_key = f"{test_folder}/{subfolder}/{filename}"
                        if file_key not in files_last_seen:
                            print(f"New file detected: {file_key}")
                            cycle_number = extract_cycle_number(filename) 
                            download_file_with_header(sftp, remote_path, local_path, test_folder, 
                                                      subfolder, cycle_number)
                        elif files_last_seen[file_key] != mod_time:
                            print(f"Updated file detected: {file_key}")
                            cycle_number = extract_cycle_number(filename) 
                            download_file_with_header(sftp, remote_path, local_path, test_folder, 
                                                      subfolder, cycle_number)

                        files_last_seen[file_key] = mod_time

            time.sleep(POLL_INTERVAL)

    finally:
        sftp.close()
        ssh.close()

if __name__ == "__main__":
    monitor_and_transfer()
