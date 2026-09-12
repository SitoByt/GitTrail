import json
from gittrail_core.fetcher import get_local_git_history, select_repo_directory
from gittrail_core.track.layout import construct_track
from gittrail_core.track.visualizer import display_via_cmdln


def main():
    repo_path = select_repo_directory()
    if not repo_path:
        print("didn't select a repository")
        return

    print(f"reading commits from: {repo_path}")
    git_history = get_local_git_history(repo_path)
    print(f"{len(git_history)} calculating layout...")

    track = construct_track(git_history)
    lanes = track.lanes
    lane_count = len(lanes)

    print(f"\nfinished layout:")
    print(f" - lane count: {lane_count}")
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

    display_via_cmdln(track)

if __name__ == "__main__":
    main()