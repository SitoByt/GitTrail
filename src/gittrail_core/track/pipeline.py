import json
from gittrail_core.config.config_manager import create_track_config, generate_default_track_config, write_track_config
from gittrail_core.config.config_model import GitConfig, TrackConfig
from gittrail_core.fetcher import create_git_info, fetch_remote_git_history, get_local_git_history, select_repo_directory
from gittrail_core.track.layout import construct_track
from gittrail_core.track.model import Track
from gittrail_core.track.visualizer import display_via_cmdln, display_via_txt

"""
This File serves as a mediator between the interface and program
"""
# TODO: Save the current JSON/Track/... somewhere => this file?
git_info: GitConfig = GitConfig()
track: Track

"""
 Commands
"""

#TODO: "Create" Function -> creates a new Graph based on the configs and git-histories
def init_local(path: str = "") -> str:
    if not path:
        repo_path = select_repo_directory()

    if not repo_path:
        print("didn't select a repository")
        return ""
    
    global git_info
    git_info = create_git_info(repo_path)
    return repo_path

def init_remote(url: str) -> str:
    temp_dir = fetch_remote_git_history(url)
    global git_info
    git_info = create_git_info(temp_dir, url)
    return temp_dir

def create_track(repo_path: str):
    git_history = get_local_git_history(repo_path)
    print(f"{len(git_history)} calculating layout...")

    global track
    track = construct_track(git_history)
    display_track_creation_cmdln()

    # Save it to JSON
    write_track_config(
        generate_default_track_config(track=track, git_info=git_info)
    )

def update_track(repo_path: str, json_path: str = ""):
    if not json_path:
        pass
        # json_path = _select_json_file()

    track_config: TrackConfig = read_json(json_path)
    global track
    track = track_config.track

    #TODO: "Update" Function -> add to existing config (new commits get added to the old track)

    write_track_config(
            create_track_config(
                track=track, 
                git_info=track_config.git_info,
                loaded_layout_config=track_config.layout_config,
                loaded_style_config=track_config.style_config
            )
        )

def _select_json_path() -> str:
    pass # TODO

"""
 Input
"""

def read_json(json_path: str) -> TrackConfig:
    with open(json_path, "r", encoding="utf-8") as f:
        data = f.read()
    return TrackConfig.model_validate_json(data)


"""
 Display/Output
"""


    
def display_track_creation_cmdln():
    lanes = track.lanes
    print(f"\nfinished layout:")
    print(f" - lane count: {len(lanes)}")
    for i, lane in enumerate(lanes):
        node_count = sum(len(b.commits) for b in lane)
        print(f"  * lane {i}: {len(lanes[i])} branches, {node_count} nodes")
    if track.node_hashes:
        first_hash = track.node_hashes[0]
        first_node = track.nodes_by_hash[first_hash]
        print(f"\nFirst Node: {first_hash[:7]} by {first_node.author}")
        connections_summary = [
            f"{c.connection_type.value} -> {c.target_hash[:7]}" 
            for c in first_node.connections
        ]
        print(f"Connections: {connections_summary}")
    else:
        print("\nNo nodes found in track.")

def display_track_in_txt(track: Track):
    display_via_txt(track)