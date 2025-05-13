import os
import glob
import shutil
import sys

if len(sys.argv) != 3:
    print(f"Usage: python {sys.argv[0]} <source_dir> <target_dir>")
    sys.exit(1)

source_dir = sys.argv[1]
target_dir = sys.argv[2]

if os.path.exists(target_dir):
    files = glob.glob(os.path.join(target_dir, "*"))
    for f in files:
        os.remove(f)
else:
    os.makedirs(target_dir, exist_ok=True)

for root, _, files in os.walk(source_dir):
    for file in files:
        src_path = os.path.join(root, file)
        # Get the relative path from source_dir
        rel_path = os.path.relpath(root, source_dir)
        if rel_path == '.':
            # If file is in root directory, just use the filename
            new_filename = file
        else:
            # Convert path separators to underscores and combine with filename
            path_prefix = rel_path.replace(os.sep, '_')
            base, ext = os.path.splitext(file)
            new_filename = f"{path_prefix}_{base}{ext}"
        
        dst_path = os.path.join(target_dir, new_filename)
        # To avoid overwriting files with the same name, add a suffix if needed
        if os.path.exists(dst_path):
            base, ext = os.path.splitext(new_filename)
            i = 1
            while os.path.exists(dst_path):
                dst_path = os.path.join(target_dir, f"{base}_{i}{ext}")
                i += 1
        shutil.copy2(src_path, dst_path)

print("All files copied into:", target_dir)