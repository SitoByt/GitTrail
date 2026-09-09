import json
from fetcher import get_local_git_history, select_repo_directory
from layout import build_track_layout


def main():
    repo_path = select_repo_directory()
    if not repo_path:
        print("Kein Verzeichnis ausgewählt.")
        return

    print(f"Lese Commits aus: {repo_path}")
    raw_history = get_local_git_history(repo_path)
    print(f"{len(raw_history)} Commits eingelesen. Berechne Layout...")

    track = build_track_layout(raw_history)

    print(f"\nLayout erfolgreich berechnet:")
    print(f"- Anzahl Gleise (Lanes): {len(track.lanes)}")
    for lane in track.lanes:
        total_nodes = sum(len(b.nodes) for b in lane.branches)
        print(f"  * Gleis {lane.lane_id}: {len(lane.branches)} Branch-Abschnitte, {total_nodes} Haltestellen")

    # Stichprobe des ersten Knotens
    first_node = track.lanes[0].branches[0].nodes[0]
    print(f"\nErster Knoten: {first_node.hash[:7]} at ({first_node.x}, {first_node.y})")
    print(f"Verbindungen: {[c.conn_type.value + ' -> ' + c.target_hash[:7] for c in first_node.connections]}")


if __name__ == "__main__":
    main()