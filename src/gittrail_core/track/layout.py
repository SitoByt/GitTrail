from __future__ import annotations
import sys
from typing import Dict, List, Optional, Set
from pydantic import BaseModel, Field
from gittrail_core.track.model import Branch, CommitNode, Connection, ConnectionType, Track

"""
This module calculates the layout of the git-history on our track
"""

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
        branches.append(Branch(name=branch_name, commits=current_branch_hashes))
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

    # get a list of commit-objects
    nodes_by_hash: Dict[str, CommitNode] = {}
    hashes: List[str] = []

    for commit in commits:
        hash = commit["hash"]
        branch = hash_to_branch_id.get(hash)

        node = CommitNode(
            hash=hash,
            author=commit["author"],
            timestamp=commit["timestamp"],
            message=commit["message"],
            parents=commit["parents"],
            branch=branch
        )
        nodes_by_hash[hash] = node
        hashes.append(hash)

    for hash in hashes:
        nodes_by_hash[hash].create_connections(nodes_by_hash)

    # Create the Graph/Track
    lanes = build_lanes_clustered(nodes_by_hash, branches)

    return Track(lanes=lanes,
                 node_hashes=hashes, 
                 nodes_by_hash=nodes_by_hash)


"""
Lane-Building Algorithm
"""

class Interval(BaseModel):
    branch_id: str
    parent_id: Optional[str] = None
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
            if parent_id == branch:
                parent_id = None

        # Add the Intervals
        intervals.append(
            Interval(
                branch_id=branch_id,
                parent_id=parent_id,
                min=min(steps),
                max=max(steps)
            )
        )
    return intervals

# TODO: Replace this function(!)
def build_lanes_clustered(hash_to_node: Dict[str, CommitNode], branches: List[Branch]) -> List[List[Branch]]:
    intervals = calculate_branch_intervals(hash_to_node, branches)
    if not intervals:
        return []

    id_to_branch = {str(id(b)): b for b in branches}
    
    root = intervals[0]
    lanes: List[List[str]] = [[root.branch_id]]
    
    branch_to_interval = {interval.branch_id: interval for interval in intervals}
    remaining = [i for i in intervals if i != root]
    remaining.sort(key=lambda x: x.min)

    for interval in remaining:
        parent_idx = 0
        if interval.parent_id:
            for idx, lane in enumerate(lanes):
                if interval.parent_id in lane:
                    parent_idx = idx
                    break

        options = []
        lanes_before = parent_idx
        lanes_after = len(lanes) - 1 - parent_idx

        # 1. Prüfe bestehende Linien (Anhängen)
        for idx, lane in enumerate(lanes):
            fits = True
            for b_id in lane:
                if interval.overlaps(branch_to_interval[b_id]):
                    fits = False
                    break
            if fits:
                crossed = range(parent_idx + 1, idx) if parent_idx < idx else range(idx + 1, parent_idx)
                intersections = sum(interval.count_crossings([branch_to_interval[b_id] for b_id in lanes[i]]) for i in crossed)
                dist = abs(parent_idx - idx)
                # Option-Format: (Intersections, Is_Insert_Penalty, Distance, Balance_Penalty, Target_Idx)
                balance_penalty = 1 if (idx < parent_idx and lanes_before > lanes_after) or (idx > parent_idx and lanes_after > lanes_before) else 0
                options.append((intersections, 0, dist, balance_penalty, False, idx))

        # 2. Prüfe neue Linien (Einfügen)
        for idx in range(len(lanes) + 1):
            crossed = range(parent_idx + 1, idx) if parent_idx < idx else range(idx, parent_idx)
            intersections = sum(interval.count_crossings([branch_to_interval[b_id] for b_id in lanes[i]]) for i in crossed)
            
            dist_after = (parent_idx + 1) - idx if idx <= parent_idx else idx - parent_idx
            balance_penalty = 1 if (idx <= parent_idx and lanes_before > lanes_after) or (idx > parent_idx and lanes_after > lanes_before) else 0
            options.append((intersections, 1, dist_after, balance_penalty, True, idx))

        # Sortiere nach: 1. Schnittpunkte, 2. Bestehende recyclen, 3. Nähe zum Parent, 4. Balance
        options.sort(key=lambda x: (x[0], x[1], x[2], x[3]))
        best_opt = options[0]

        is_insert = best_opt[4]
        target_idx = best_opt[5]

        if is_insert:
            lanes.insert(target_idx, [interval.branch_id])
        else:
            lanes[target_idx].append(interval.branch_id)

    resulting_lanes = []
    for lane in lanes:
        resulting_lanes.append([id_to_branch[branch_id] for branch_id in lane])
    return resulting_lanes

class Cluster(BaseModel):
    interval: Interval
    child_clusters: List[Cluster] = Field(default_factory=list)

# TODO: REPLACE STANDARD ALGORITHM
"""
1. Neue Klasse -> Cluster (enthält den ur-branch, und alle seine sub-Cluster) => Ermittlung der Breite
2. Wir checken an der grenze jedes gleichwertigen clusters (gleicher parent) die geringste Schnitt-Anzahl
3.1. Wir erstellen neue Linien für die Branches (wenn es bereits ausreichend Linien gibt können wir diese nehmen)
    a) Linien außerhalb den Schwester-Clustern (der äußerer Branch ist länger als der innere) => Einfach greedy neu erstellen
    b) Linien in den Schwester-Clustern  (der äußere Branch ist kürzer als der innere) => greedy linien erstellen
3.2. Linien existieren bereits (Greedy würde formatierung zerstören!)
        -> zu wenig linien? 
            ganz oben: einfach neu erstellen, 
            sonst: gleichmaßig nach oben und unten für schöne formatierung (priorität: nähe zum parent-branch(!))
    => Wir berechnen die beste darstellung im vorhinaus, und fügen sie dann in den linien entsprechend ein
Wenn wir können wollen wir wenn wir die freie Wahl haben einen Branch (solange kein zukünftiger Schwester-branch früher aufhören würde) weiter innen sein.
    
4. Wir übersetzen die Darstellung zu Branches und erstellen daraus den Track

    
    
Punkt 1 ermöglicht einfaches Traversieren der Branches/der Intervalle
Punkt 2 wird implementiert, indem wir alle Lines basierend auf ihren Intervallen berechnen
Punkt 3 kann als eine Funktion genutzt werden => wenn die linien noch nicht existieren fügen wir einfach die neuen Listen hinzu, ansonsten hängen wir sie an den entsprechenden Indexen an
"""

# TODO: Funktion um Linien/Gleise zu minimieren (ohne Cluster zu zerstören(!)) 
# => Wenn zwei Linien von mehreren branches zu den gleichen zeitpunkten nicht genutzt wird, können wir sie vereinigen

# Sind andere Optimierungen/Automatisierungen möglich?
