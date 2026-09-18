from __future__ import annotations
from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict
from pydantic import BaseModel, Field

class ConnectionType(str, Enum):
    COMMIT = "commit"
    BRANCH = "branch"
    MERGE = "merge"
    REFACTOR = "refactor" 

class Connection(BaseModel):
    target_hash : str
    connection_type : ConnectionType

class CommitNode(BaseModel):
    #Data
    hash : str
    author: str
    timestamp : int
    message : str
    #Layout
    branch: Optional[str] = None # Branch id
    parents : list[str] = Field(default_factory=list)
    connections: list[Connection] = Field(default_factory=list)
    #Style
    color: str = "#000000"

    def set_branch(self, branch: Branch):
        self.branch = id(branch)
        if self not in branch.commits:
            branch.commits.append(self)

    def get_date(self) -> datetime:
        return datetime.fromtimestamp(self.timestamp)

    def is_merge(self) -> bool:
        return len(self.parents) > 1

    def is_root(self) -> bool:
        return len(self.parents) == 0
    
    # determines the connections for each node
    def create_connections(self, nodes_by_hash: Dict[str, CommitNode]):
        self.connections = []
        for idx, parent_hash in enumerate(self.parents):
            parent_node = nodes_by_hash.get(parent_hash)
            if not parent_node:
                continue
            if idx > 0:
                connection_type = ConnectionType.MERGE
            elif parent_node.branch != self.branch:
                connection_type = ConnectionType.BRANCH
            else:
                connection_type = ConnectionType.COMMIT
            parent_node.connections.append(Connection(target_hash=self.hash, connection_type=connection_type))

class Branch(BaseModel):
    name: str
    color: str = "#000000"
    commits: list[str] = Field(default_factory=list)
    ongoing: bool = False

    def add_commit(self, commit: CommitNode):
        self.commits.append(commit.hash)

class Track(BaseModel):
    lanes: list[list[Branch]] = Field(default_factory=list)
    node_hashes: list[str] = Field(default_factory=list)
    nodes_by_hash: Dict[str, CommitNode] = Field(default_factory=dict)




