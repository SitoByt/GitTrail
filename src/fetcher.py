import tkinter
from tkinter import filedialog
import os
import re
import tempfile

import subprocess
import json

"""
Fetches the Git History from a local Directory or from GitLab/GitHub
"""

# determine local path
def select_repo_directory() -> str | None:
    root = tkinter.Tk()
    root.withdraw()
    root.attributes("-topmost", True)

    folder_path = filedialog.askdirectory(
        title="Select your local Git-Repository"
    )
    root.destroy()

    if folder_path:
        if os.path.exists(os.path.join(folder_path, ".git")):
            return folder_path
        else:
            print("Error: the selected Folder isn't a Git-Repository")
            return None
    return None

# local history
def get_local_git_history(path: str):
    sep = "%x00"
    cmd = [
        "git", "-C", path, "log", "--all", "--topo-order",
        f"--pretty=format:%H{sep}%P{sep}%an{sep}%at{sep}%s{sep}%D"
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=True,
        encoding="utf-8"
    )

    commits = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        parts = line.split(sep)
        commits.append({
            "hash": parts[0],
            "parents": parts[1].split() if parts[1] else [],
            "author": parts[2],
            "timestamp": int(parts[3]),
            "message": parts[4] if len(parts) > 4 else ""
        })

    return commits

# fetches (only the Git-History) via an Web-URL
def fetch_remote_git_history(url: str):
    with tempfile.TemporaryDirectory() as temp_dir:
        clone_cmd = ["git", "clone", "--bare", "--filter=blob:none", url, temp_dir]
        try:
            subprocess.run(clone_cmd, capture_output=True, text=True, check=True)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Error while cloning repository: {e.stderr.strip()}")
        return get_local_git_history(temp_dir)


if __name__ == "__main__":
    path = select_repo_directory()
    if path:
        print(f"Selected Repository: {path}")
        history = get_local_git_history(path)
        print(json.dumps(history, indent=2, ensure_ascii=False))
        print(f"\nResulting Json: {len(history)} Commits.")
    else:
        print("Failed reading the repository")
