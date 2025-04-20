# reference/generate_tree.py
import os

def generate_folder_tree(start_path, output_path, exclude_dirs=None):
    """
    Generates a text file representing the folder tree structure.

    Args:
        start_path (str): The root directory from which to generate the tree.
        output_path (str): The full path (including filename) where the
                           tree structure text file will be saved.
        exclude_dirs (list, optional): A list of directory names to exclude
                                      from the tree. Defaults to None.
    """
    if exclude_dirs is None:
        exclude_dirs = []

    # Use 'utf-8' encoding for wider character support
    with open(output_path, 'w', encoding='utf-8') as f:
        # os.walk generates the file names in a directory tree
        for root, dirs, files in os.walk(start_path, topdown=True):
            # --- Exclusion Logic ---
            # Modify dirs in-place to prevent os.walk from descending into them
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            # -----------------------

            # Calculate the level of depth relative to start_path for indentation
            # Add 1 to handle the root level correctly if start_path itself is listed
            level = root.replace(start_path, '').count(os.sep)
            if root == start_path:
                 level = 0 # Ensure root is not indented

            indent = ' ' * 4 * (level)

            # Write the directory name relative to start_path
            # Handle the root directory name specifically
            if root == start_path:
                 f.write(f'{os.path.basename(start_path)}/\n')
            else:
                 f.write(f'{indent}{os.path.basename(root)}/\n')

            # Indent for files within the directory
            subindent = ' ' * 4 * (level + 1)
            # List files in the current directory
            for file in files:
                f.write(f'{subindent}{file}\n')

    print(f"Folder tree (excluding {exclude_dirs}) saved to: {output_path}")

if __name__ == "__main__":
    # Get the directory where the script itself is located (reference/)
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Get the parent directory of the script's location (project root)
    project_root_dir = os.path.dirname(script_dir)

    # Define the name for the output file
    output_filename = "folder_tree.txt"

    # Construct the full path for the output file within the reference/ folder
    output_file_path = os.path.join(script_dir, output_filename)

    # Define directories to exclude
    folders_to_exclude = ["__pycache__", ".git", ".idea", ".vscode", "venv"]

    # Generate the tree starting from the project root directory
    # and save the output in the reference/ folder
    generate_folder_tree(
        start_path=project_root_dir,
        output_path=output_file_path,
        exclude_dirs=folders_to_exclude
    )