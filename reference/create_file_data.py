# reference/create_file_data.py
import os

def write_py_files_to_txt(scan_path, output_path, exclude_files=None, exclude_dirs=None):
    """
    Scans a directory for .py files, combines their content into a single text file,
    excluding specified files and directories.

    Args:
        scan_path (str): The root directory to start scanning for .py files.
        output_path (str): The full path (including filename) to save the combined content.
        exclude_files (list, optional): A list of filenames to exclude. Defaults to None.
        exclude_dirs (list, optional): A list of directory names to exclude. Defaults to None.
    """
    if exclude_files is None:
        exclude_files = []
    if exclude_dirs is None:
        exclude_dirs = []

    # Ensure the output file itself is excluded if it's within the scan path
    output_filename = os.path.basename(output_path)
    if output_filename not in exclude_files:
        exclude_files.append(output_filename)

    print(f"Scanning for .py files in: {scan_path}")
    print(f"Excluding directories: {exclude_dirs}")
    print(f"Excluding files: {exclude_files}")

    # Use 'utf-8' encoding for reading and writing
    with open(output_path, 'w', encoding='utf-8') as output_file:
        # Traverse the scan path
        for root, dirs, files in os.walk(scan_path, topdown=True):
            # --- Directory Exclusion Logic ---
            # Modify dirs in-place to prevent os.walk from descending into them
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            # ---------------------------------

            for file in files:
                # --- File Exclusion Logic ---
                if file.endswith('.py') and file not in exclude_files:
                    file_path = os.path.join(root, file)
                    relative_path = os.path.relpath(file_path, scan_path) # Get path relative to scan root

                    # Write a comment header with the relative file path
                    output_file.write(f'# Contents of {relative_path.replace(os.sep, "/")}\n') # Use forward slashes for consistency

                    try:
                        # Read the .py file content
                        with open(file_path, 'r', encoding='utf-8') as py_file:
                            content = py_file.read()
                            output_file.write(content + '\n\n') # Add content and two newlines
                    except Exception as e:
                        output_file.write(f"# ERROR reading file {relative_path}: {e}\n\n")
                        print(f"⚠️ Error reading file {file_path}: {e}")

    print(f"\n✅ Contents of .py files written to: {output_path}")

if __name__ == "__main__":
    # Directory where this script is located (reference/)
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Project root directory (parent of reference/)
    project_root_dir = os.path.dirname(script_dir)

    # Define the output filename and full path (within reference/)
    output_filename = 'combined_files.txt'
    output_file_path = os.path.join(script_dir, output_filename)

    # Define files and directories to exclude
    files_to_exclude = [
        'create_file_data.py', # Exclude this script itself
        'generate_tree.py',    # Exclude the tree generator script
        # output_filename is added automatically within the function
    ]
    dirs_to_exclude = [
        '__pycache__',
        '.venv', # Common virtual environment folder name
        'venv',  # Another common name
        '.git',  # Exclude git directory
        # Add any other specific directory names you want to exclude
    ]

    # Call the function to perform the scan and write the output
    write_py_files_to_txt(
        scan_path=project_root_dir,
        output_path=output_file_path,
        exclude_files=files_to_exclude,
        exclude_dirs=dirs_to_exclude
    )