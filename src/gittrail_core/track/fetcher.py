import tkinter
from tkinter import filedialog
import os
import re
import tempfile

import subprocess
import json

from gittrail_core.config.config_model import GitConfig

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

# local history
def get_local_git_history(path: str):
    sep = "%x00"
    cmd = [
        "git", "-C", path, "log", "--all", "--topo-order",
        f"--pretty=format:%H{sep}%P{sep}%an{sep}%at{sep}%s{sep}%D%x1E"
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=True,
        encoding="utf-8"
    )

    commits = []
    for line in result.stdout.split("\x1E"):
        if not line.strip():
            continue
        parts = line.split("\x00")
        commits.append({
            "hash": parts[0].strip(),
            "parents": parts[1].split() if parts[1] else [],
            "author": parts[2],
            "timestamp": int(parts[3]),
            "message": parts[4] if len(parts) > 4 else "",
            "refs": [r.strip() for r in parts[5].split(",")] if len(parts) > 5 and parts[5] else []
        })

    return commits

# fetches (only the Git-History) via an Web-URL
def fetch_remote_git_history(url: str):
    temp_dir = tempfile.mkdtemp()
    clone_cmd = ["git", "clone", "--bare", "--filter=blob:none", url, temp_dir]
    try:
        subprocess.run(clone_cmd, capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Error while cloning repository: {e.stderr.strip()}")
    return temp_dir

# creates a git config for the git repository
def create_git_info(path: str, url: str = "") -> GitConfig:
    project_name = os.path.basename(os.path.abspath(path))

    if not url:
        try:
            result = subprocess.run(
                ["git", "-C", path, "remote", "get-url", "origin"],
                capture_output=True,
                text=True,
                check=True,
                encoding="utf-8"
            )
            url = result.stdout.strip()
        except subprocess.SubprocessError:
            url = ""

    description = ""
    desc_path = os.path.join(path, ".git", "description")
    if os.path.exists(desc_path):
        try:
            with open(desc_path, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if content and not content.startswith("Unnamed repository"):
                    description = content
        except Exception:
            pass
            
    if not description:
        description = f"Git repository for {project_name}"

    return GitConfig(
        project_name=project_name,
        project_url=url,
        project_description=description
    )

