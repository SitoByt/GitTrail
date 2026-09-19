import os
from typing import Dict, Tuple

from gittrail_core.track.model import Track, Branch

"""
Renders the layout visually
"""

from gittrail_core.track.model import Track


def display_via_txt(track: Track):
    if not track.lanes or not track.node_hashes:
        return

    lane_count = len(track.lanes)
    node_count = len(track.node_hashes)
    
    branch_to_vlane: Dict[str, int] = {}
    for lane_idx, lane in enumerate(track.lanes):
        for branch in lane:
            branch_to_vlane[str(id(branch))] = lane_idx

    hash_to_col = {h: idx for idx, h in enumerate(track.node_hashes)}

    branch_bounds: Dict[str, list[int]] = {}
    for lane in track.lanes:
        for branch in lane:
            b_id = str(id(branch))
            cols = [hash_to_col[h] for h in track.node_hashes if str(track.nodes_by_hash[h].branch) == b_id]
            if cols:
                branch_bounds[b_id] = [min(cols), max(cols)]


    grid = [[' ' for _ in range(node_count)] for _ in range(lane_count)]

    for c, c_hash in enumerate(track.node_hashes):
        node = track.nodes_by_hash[c_hash]
        active_b_id = str(node.branch)
        active_lane = branch_to_vlane.get(active_b_id)

        slash_lanes: Dict[int, str] = {}

        if active_lane is not None:
            is_first_commit = (c == branch_bounds[active_b_id][0])

            for i, parent_hash in enumerate(node.parents):
                parent_node = track.nodes_by_hash.get(parent_hash)
                if not parent_node or not parent_node.branch:
                    continue
                
                p_lane = branch_to_vlane.get(str(parent_node.branch))
                if p_lane is None or p_lane == active_lane:
                    continue

                step = 1 if active_lane > p_lane else -1
                char = '/' if step == 1 else '\\'
            
                if is_first_commit and i == 0:
                    for l in range(p_lane + step, active_lane + step, step):
                        slash_lanes[l] = char
                        
                elif i > 0:
                    for l in range(p_lane, active_lane, step):
                        slash_lanes[l] = char

        for l in range(lane_count):
            if l in slash_lanes:
                grid[l][c] = slash_lanes[l]
            else:
                is_alive = False
                for branch in track.lanes[l]:
                    b_id = str(id(branch))
                    if b_id in branch_bounds:
                        bounds = branch_bounds[b_id]
                        if bounds[0] <= c <= bounds[1]:
                            is_alive = True
                            break
                grid[l][c] = '-' if is_alive else ' '

    main_lane_idx = 0
    if track.node_hashes:
        first_node = track.nodes_by_hash[track.node_hashes[0]]
        main_lane_idx = branch_to_vlane.get(str(first_node.branch), 0)

    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(current_dir, "../../../"))
    output_dir = os.path.join(project_root, "output")
    os.makedirs(output_dir, exist_ok=True)
    
    filename = os.path.join(output_dir, "git_graph.txt")

    with open(filename, "w", encoding="utf-8") as f:
        f.write(f"--- GitTrail Horizontal Graph ({lane_count} Lanes, {node_count} Commits) ---\n")
        for v_lane in range(lane_count - 1, -1, -1):
            row_str = "".join(grid[v_lane])
            label = v_lane - main_lane_idx
            f.write(f"{label:2d} | {row_str}\n")

"""
Example/Idea on how this could look:
3 |        /----\     /--\
2 |    /---------------------\
1 |    /     /-------\       \
0 | ----------------------------------
-1|       \       /-------\   /
-2|       \-------------------/
-3|           \-------/
"""