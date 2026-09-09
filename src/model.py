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

class Branch(BaseModel):
    name: str
    color: str = "#000000"
    commits_by_hash: list[str] = Field(default_factory=list)

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
    branch: Optional[Branch] = None
    parents : list[str] = Field(default_factory=list)
    connections: list[Connection] = Field(default_factory=list)
    #Style
    color: str = "#000000"

    def set_branch(self, branch: Branch):
        self.branch = branch
        if self.hash not in branch.commits_by_hash:
            branch.commits_by_hash.append(self.hash)

    def get_date(self) -> datetime:
        return datetime.fromtimestamp(self.timestamp)

    def is_merge(self) -> bool:
        return len(self.parents) > 1

    def is_root(self) -> bool:
        return len(self.parents) == 0
    
    # determines the connections for each node
    def create_connections(self, hash_to_node: Dict[str, CommitNode]):
        self.connections = []
        branch = self.branch

        for idx, parent_hash in enumerate(self.parents):
            parent_node = hash_to_node.get(parent_hash)
            parent_branch = parent_node.branch if parent_node else None
            if idx > 0:
                connection_type = ConnectionType.MERGE
            elif parent_branch != branch:
                connection_type = ConnectionType.BRANCH
            else:
                connection_type = ConnectionType.COMMIT
            self.connections.append(Connection(target_hash=parent_hash, conn_type=connection_type))

class Track(BaseModel):
    lanes: list[list[Branch]] = Field(default_factory=list)
    nodes: list[CommitNode] = Field(default_factory=list)

def find_node(nodes: list[CommitNode], commit_hash: str) -> Optional[CommitNode]:
    for node in nodes:
        if node.hash == commit_hash:
            return node
    return None




