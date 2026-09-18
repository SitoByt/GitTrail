from __future__ import annotations
import sys
from typing import Dict, List, Optional, Set, Tuple
from pydantic import BaseModel, Field
from gittrail_core.track.model import Branch, CommitNode, Connection, ConnectionType, Track

"""
This module calculates the layout of the git-history on our track
"""

# determines the branches and whether they are still active
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
                        if ref.startswith("origin/"):
                            b_name = ref.split("/", 1)[-1]
                            is_ongoing = True
                            break
                        elif not b_name:
                            b_name = ref
            
            parents = commits_by_hash[curr]["parents"]
            curr = parents[0] if parents else None
        
        is_ongoing = bool(b_name)
        branch_name = b_name if b_name else f"branch-{len(branches)}"
        current_branch_hashes.reverse() # last to first => first to last
        branches.append(Branch(name=branch_name, commits=current_branch_hashes, ongoing=is_ongoing))
    return branches

# Creates the track-object
def construct_track(commits: List[Dict]) -> Track:
    if not commits:
        return Track()

    # construct branches
    branches = get_branches(commits)
    hash_to_branch_id: Dict[str, str] = {}
    for branch in branches:
        for hash in branch.commits:
            hash_to_branch_id[hash] = str(id(branch))

    commits.reverse() # sorted from oldest to newest
    nodes_by_hash: Dict[str, CommitNode] = {}   
    hashes: List[str] = []

    for commit in commits:
        hash = commit["hash"]
        nodes_by_hash[hash] = CommitNode(
            hash=hash,
            author=commit["author"],
            timestamp=commit["timestamp"],
            message=commit["message"],
            parents=commit["parents"],
            branch=hash_to_branch_id.get(hash)
        )
        hashes.append(hash)

    for hash in hashes:
        nodes_by_hash[hash].create_connections(nodes_by_hash)

    # Create the Graph/Track
    lanes = construct_lanes(nodes_by_hash, branches)

    return Track(lanes=lanes,
                 node_hashes=hashes, 
                 nodes_by_hash=nodes_by_hash)


"""
Lane-Building Algorithm
"""

# Data-Class to calculate with the comparative branch-length
class Interval:
    def __init__(self, branch_id: str, min: int, max: int, parent_id: Optional[str] = None):
        self.branch_id = branch_id
        self.parent_id = parent_id
        self.min = min
        self.max = max

    def contains(self, other: Interval) -> bool:
        return self.min <= other.min and other.max <= self.max

    def overlaps(self, other: Interval) -> bool:
        return max(self.min, other.min) <= min(self.max, other.max)
    
# transform Branches into intervals
def calculate_branch_intervals(hash_to_node: Dict[str, CommitNode], branches: list[Branch]) -> list[Interval]:
    nodes_list = list(hash_to_node.values())
    hash_to_step = {node.hash: idx for idx, node in enumerate(nodes_list)}
    intervals = []
    for branch in branches:
        branch_id = str(id(branch))
        steps = [hash_to_step[h] for h in branch.commits if h in hash_to_step]
        if not steps: 
            continue

        # Calculate the parent-branch
        first_node =  hash_to_node.get(branch.commits[0])
        parent_id = None
        if first_node.parents:
            parent_node = hash_to_node.get(first_node.parents[0])
            if parent_node and parent_node.branch:
                parent_id = str(parent_node.branch)
            if parent_id == branch_id:
                parent_id = None

        # Add the Intervals
        intervals.append(Interval(
                branch_id=branch_id,
                parent_id=parent_id,
                min=min(steps),
                max=max(steps)
            ))
        
    if intervals:
        main_id = intervals[0].branch_id
        for inv in intervals[1:]:
            if inv.parent_id is None:
                inv.parent_id = main_id
        intervals.sort(key=lambda x: x.min)
    return intervals

"""
The cluster class is used to calculate the layout of each lane inside of the branch efficiently.
"""
class Cluster:
    def __init__(self, interval:Interval, intervals: List[Interval]):
        self.interval = interval
        self.child_clusters = [Cluster(inv, intervals) for inv in intervals if inv.parent_id == self.interval.branch_id] 
        self._min = self.interval.min
        self._max = -1
        self._width = -1
        self._cluster_lanes: List[List[Cluster]] = []
        self._physical_lanes: List[List[Cluster]] = []

    # transform the Cluster into lanes with branch-ids
    def get_lanes(self) -> List[List[str]]:
        cluster_lanes = self._get_physical_lanes()
        id_lanes = []
        for lane in cluster_lanes:
            current_lane = []
            for cluster in lane:
                current_lane.append(cluster.interval.branch_id)
            id_lanes.append(current_lane)
        return id_lanes

    # calculates cluster-layout
    def _get_clusterd_lanes(self) -> List[List[Cluster]]:
        if self._cluster_lanes:
            return self._cluster_lanes
        
        # responsible for inserting a cluster into the lanes (relative to the parent)
        def cascade_insert(idx: int, cluster: Cluster, push_dir: int):
            nonlocal parent_idx

            if idx < 0:
                lanes.insert(0, [cluster])
                parent_idx += 1
                return
            if idx >= len(lanes):
                lanes.append([cluster])
                return
                
            overlapping = [c for c in lanes[idx] if c.overlaps(cluster)]
            lanes[idx] = [c for c in lanes[idx] if not c.overlaps(cluster)]
            lanes[idx].append(cluster)
            lanes[idx].sort(key=lambda x: x.get_min())
            
            for ev in overlapping:
                cascade_insert(idx + push_dir, ev, push_dir)

        lanes = [[self]]  
        parent_idx = 0 
        # We chronologically iterate over each Cluster, and add it to our lanes 
        for child in self.child_clusters:
            candidates = []

            # Algorithm to determine priority of where to insert it
            for idx in range(len(lanes) + 2):
                if idx == parent_idx: 
                    continue
                    
                crossings = 0
                if idx < parent_idx:
                    check_range = range(idx + 1, parent_idx)
                else:
                    check_range = range(parent_idx + 1, idx)
                    
                for i in check_range:
                    if i < len(lanes) and any(child.overlaps(c) for c in lanes[i]):
                        crossings += 1

                dist = (parent_idx - idx) if idx <= parent_idx else (idx - 1 - parent_idx)
                is_above = idx > parent_idx
                candidates.append((crossings, is_above, dist, idx))
                    
            if candidates:
                # Priority: 1. least crossings, 2. is_above, 3. distance.
                candidates.sort(key=lambda c: (c[0], not c[1], c[2]))

                result = candidates[0]
                target_idx = result[3]

                push_dir = -1 if target_idx < parent_idx else 1
                cascade_insert(target_idx, child, push_dir)
            
        self._cluster_lanes = lanes
        return lanes

    # calculates line-positioning
    def _get_physical_lanes(self) -> List[List[Cluster]]:
        if self._physical_lanes:
            return self._physical_lanes
        
        # Merging together all the sub-lanes by translating a lane of clusters to a list of lanes as wide as the widest sub-cluster
        logical_lanes = self._get_clusterd_lanes()
        physical_lanes: List[List[Cluster]] = []

        parent_idx = 0
        for i, lane in enumerate(logical_lanes):
            if self in lane:
                parent_idx = i
                break

        for idx, lane in enumerate(logical_lanes):
            if self in lane:
                physical_lanes.append([self])
            else:
                lane_width = 0
                for cluster in lane:
                    lane_width = max(lane_width, cluster.get_width())
                sub_lanes: List[List[Cluster]] = [[] for _ in range(lane_width)]
                for cluster in lane:
                    cluster_phys = cluster._get_physical_lanes()
                    if idx < parent_idx:
                        # Mirroring the layout if the sub-cluster is below the cluster
                        cluster_phys = list(reversed(cluster_phys))
                        offset = lane_width - len(cluster_phys)
                    else:
                        offset = 0
                    for i in range(lane_width):
                        if i < len(cluster_phys):
                            sub_lanes[offset + i].extend(cluster_phys[i])
                physical_lanes.extend(sub_lanes)
                
        self._physical_lanes = physical_lanes
        return physical_lanes

    # getters

    def get_width(self) -> int:
        if self._width == -1:
            self._width = len(self._get_physical_lanes())
        return self._width

    def get_min(self) -> int:
        return self._min

    def get_max(self) -> int:
        if(self._max == -1):
            if self.child_clusters:
                self._max = max(max(c.get_max() for c in self.child_clusters), self.interval.max)
            else:
                self._max = self.interval.max
        return self._max

    def get_min_max(self) -> tuple[int, int]:
        return (self.get_min(), self.get_max())

    # helper functions

    def contains(self, other: Cluster) -> bool:
        s_min, s_max = self.get_min_max()
        o_min, o_max = other.get_min_max()
        return s_min <= o_min and o_max <= s_max
    
    def overlaps(self, other: Cluster) -> bool:
        s_min, s_max = self.get_min_max()
        o_min, o_max = other.get_min_max()
        return max(s_min, o_min) <= min(s_max, o_max)

def construct_lanes(hash_to_node: Dict[str, CommitNode], branches: List[Branch]) -> List[List[Branch]]:
    intervals = calculate_branch_intervals(hash_to_node=hash_to_node, branches=branches)
    if not intervals:
        return []

    id_to_branch = {str(id(branch)) : branch for branch in branches}

    root_cluster = Cluster(interval=intervals[0], intervals=intervals)
    id_lanes = root_cluster.get_lanes()

    return[[id_to_branch[branch_id] for branch_id in lane] for lane in id_lanes]


# TODO: Funktion um Linien/Gleise zu minimieren (ohne Cluster zu zerstören(!)) 
# => Wenn zwei Linien von mehreren branches zu den gleichen zeitpunkten nicht genutzt wird, können wir sie vereinigen

# TODO: Maybe a Function to update a Track (continue from an existing history)