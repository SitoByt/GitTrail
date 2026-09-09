from __future__ import annotations
import sys
from typing import Dict, List, Optional, Set
from pydantic import BaseModel
from model import Branch, CommitNode, Connection, ConnectionType, Track, find_node

# determines the branches
def get_branches(commits: List[Dict]) -> List[Branch]:
    commits_by_hash = {c["hash"]: c for c in commits}
    assigned_hashes: Set[str] = set()
    branches: List[Branch] = []

    for commit in commits:
        c_hash = commit["hash"]
        if c_hash in assigned_hashes:
            continue

        # assign all hashes of a branch to one branch and define a name for the branch
        current_branch_hashes: List[str] = []
        curr = c_hash
        b_name : Optional[str] = None
        while curr and curr not in assigned_hashes and curr in commits_by_hash:
            assigned_hashes.add(curr)
            current_branch_hashes.append(curr)

            if not b_name:
                refs = commits_by_hash[curr].get("refs", [])
                if refs:
                    for ref in refs:
                        if not ref.startswith("tag:") and not ref.startswith("origin/HEAD"):
                            b_name = ref.split("/", 1)[-1] if ref.startswith("origin/") else ref
                            break
            
            parents = commits_by_hash[curr]["parents"]
            curr = parents[0] if parents else None

        branch_name = b_name if b_name else f"branch-{len(branches)}"
        current_branch_hashes.reverse() # last to first => first to last
        branches.append(Branch(name=branch_name, commits_by_hash=current_branch_hashes))
    return branches

# Creates the track-object
def construct_track(commits: List[Dict]) -> Track:
    if not commits:
        return Track()

    # construct branches
    branches = get_branches(commits)
    hash_to_branch: Dict[str, Branch] = {}
    for branch in branches:
        for hash in branch.commits_by_hash:
            hash_to_branch[hash] = branch

    # get a list of commit-objects
    sorted_commits = sorted(commits, key=(lambda c: c["timestamp"]))
    nodes: List[CommitNode] = []
    hash_to_node: Dict[str, CommitNode] = {}
    for commit in sorted_commits:
        hash = commit["hash"]
        branch = hash_to_branch.get(hash)

        node = CommitNode(
            hash=hash,
            author=commit["author"],
            timestamp=commit["timestamp"],
            message=commit["message"],
            parents=commit["parents"],
            branch=branch
        )
        nodes.append(node)
        hash_to_node[hash] = node
    nodes.sort(key=(lambda x: x.timestamp))

    # Create the Graph/Track
    lanes = build_lanes_clustered(hash_to_node, branches)
    for node in nodes:
        node.create_connections(hash_to_node)
    return Track(nodes=nodes, lanes=lanes)


"""
For our standard-Algorithm we have to make sure we have the minimum of lanes
"""

class Interval(BaseModel):
    branch: Branch
    parent: Optional[Branch] = None
    min: int
    max: int

    def contains(self, other: Interval) -> bool:
        return self.min <= other.min and other.max <= self.max

    def overlaps(self, other: Interval) -> bool:
        return max(self.min, other.min) <= min(self.max, other.max)

    def count_crossings(self, intervals: List[Interval]):
        conflicts = 0
        for other in intervals:
            if self.overlaps(other):
                if not (self.contains(other) or other.contains(self)):
                    conflicts += 1
        return conflicts
    

# transform Branches into intervals
def calculate_branch_intervals(hash_to_node: Dict[str, CommitNode], branches: list[Branch]) -> list[Interval]:
    nodes_list = list(hash_to_node.values())
    hash_to_step = {node.hash: idx for idx, node in enumerate(nodes_list)}
    intervals = []
    for branch in branches:
        steps = [hash_to_step[h] for h in branch.commits_by_hash if h in hash_to_step]
        if not steps: 
            continue

        # Calculate the parent-branch
        first_node =  hash_to_node.get(branch.commits_by_hash[0])
        parent_branch = None
        if first_node.parents:
            parent_node = hash_to_node.get(first_node.parents[0])
            if parent_node and parent_node.branch:
                parent_branch = parent_node.branch
            if parent_branch == branch:
                parent_branch = None

        # Add the Intervals
        intervals.append(
            Interval(
                branch=branch,
                parent=parent_branch,
                min=min(steps),
                max=max(steps)
            )
        )
    return intervals

# builds merge-clusters while minimizing intersections & lanes
def build_lanes_clustered(hash_to_node: Dict[str, CommitNode], branches: List[Branch]) -> List[List[Branch]]:
    intervals = calculate_branch_intervals(hash_to_node, branches)
    if not intervals:
        return []

    children_map: Dict[Branch, List[Branch]] = {interval.branch: [] for interval in intervals}
    for interval in intervals:
        parent = interval.parent
        if parent and parent in children_map:
            children_map[parent].append(interval.branch)

    def get_cluster_width(b: Branch) -> int:
        return 1 + sum(get_cluster_width(child) for child in children_map.get(b, []))
    cluster_width = {interval.branch: get_cluster_width(interval.branch) for interval in intervals}

    branch_to_interval = {interval.branch: interval for interval in intervals}
    
    root = intervals[0]
    lanes: List[List[Branch]] = [[root.branch]]

    remaining = [i for i in intervals if i != root]
    remaining.sort(key=(lambda x: x.min))

    for interval in remaining:
        parent_idx = 0
        if interval.parent:
            for idx, lane in enumerate(lanes):
                if interval.parent in lane:
                    parent_idx = idx
                    break

        least_intersections = sys.maxsize
        best_idx = None
        best_dist = sys.maxsize
        insert = True

        for idx, lane in enumerate(lanes):
            fits = True
            for b in lane:
                if interval.overlaps(branch_to_interval[b]):
                    fits = False
                    break
            if fits:
                # TODO: Rethink whether we should always insert if possible (fewer lines or fewer cross-sections? => Configurable?(!))
                crossed_indices = range(parent_idx + 1, idx) if parent_idx < idx else range(idx, parent_idx)
                intersections = sum(interval.count_crossings([branch_to_interval[b] for b in lanes[i]]) for i in crossed_indices)
                dist = abs(idx - parent_idx)
                if intersections < least_intersections or (intersections == least_intersections and dist < best_dist):
                    least_intersections = intersections
                    best_idx = idx
                    best_dist = dist
                    insert = False

        for idx in range(len(lanes) + 1):
            crossed_indices = range(parent_idx + 1, idx) if parent_idx < idx else range(idx, parent_idx)
            intersections = sum(interval.count_crossings([branch_to_interval[b] for b in lanes[i]]) for i in crossed_indices)
            dist = abs(idx - parent_idx)
            
            if intersections < least_intersections:
                least_intersections = intersections
                best_dist = dist
                best_idx = idx
                insert = True 
            elif intersections == least_intersections:
                if dist < best_dist:
                    best_dist = dist
                    best_idx = idx
                    insert = True 
                elif dist == best_dist:
                    if cluster_width[interval.branch] > 1 and not insert:
                        insert = True
                        best_idx = idx

        if insert:
            lanes.insert(best_idx, [interval.branch])
        else:
            lanes[best_idx].append(interval.branch)

    return lanes

        


