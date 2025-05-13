# filepath: scripts/add_filespaths.py
import os

def add_relative_path_comment(root_dir, comment_prefix="#"):
    """
    Add the relative file path as a comment at the top of each file in the directory.
    """
    for subdir, _, files in os.walk(root_dir):
        for file in files:
            file_path = os.path.join(subdir, file)
            relative_path = os.path.relpath(file_path, root_dir)

            # Skip binary files and __pycache__ directories
            if file.endswith(('.pyc', '.pyo')) or '__pycache__' in subdir:
                continue

            try:
                with open(file_path, 'r+', encoding='utf-8') as f:
                    content = f.readlines()
                    # Check if the first line already contains the relative path
                    if content and content[0].strip() == f"{comment_prefix} filepath: {relative_path}":
                        continue
                    # Add the relative path comment at the top
                    f.seek(0)
                    f.write(f"{comment_prefix} filepath: {relative_path}\n")
                    f.writelines(content)
            except Exception as e:
                print(f"Error processing file {file_path}: {e}")

if __name__ == "__main__":
    project_root = "/home/martineserios/projects/ongoing/muti_db_rag_ai_agent/rag-chatbot"
    add_relative_path_comment(project_root)