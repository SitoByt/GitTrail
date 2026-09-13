import json
import os
from gittrail_core.track.model import Track
from enum import Enum
from typing import Dict, List, Optional, Union
from pydantic import BaseModel, Field

"""
Style Config
"""

# ---
class LineColorType(str, Enum):
    BRANCH_INDEXED = "branch_indexed" # changes color based on how far away it is from the main-branch

class NodeColorType(str, Enum):
    COMMIT_TYPED = "commit_typed" # bases its color on the commit type
    BRANCH_BASED = "branch_based" # copies the color from the branch it's on

# --- 
class LineColorPalette(BaseModel):
    name: str # key
    type: LineColorType  
    colors: List[str] = Field(default_factory=list)

class LineStyleConfig(BaseModel):
    color_palatte: LineColorPalette

class NodeColorPalette(BaseModel):
    name: str # key (later important for the presets)
    type: NodeColorType 
    colors: Dict[str, str] = Field(default_factory=dict)

class NodeStyleConfig(BaseModel):
    color_palatte: NodeColorPalette

class StyleConfig(BaseModel):
    line_config: LineStyleConfig
    node_config: NodeStyleConfig

"""
Layout Config
"""

class NodeDisplayType(str, Enum):
    CRICLE = "circle"
    DOUBLE_CIRCLE = "double_circle" 

# describes how to connect Nodes between lanes
class LaneChangeType(str, Enum):
    LINEAR = "linear"   # straight line
    CURVED = "curved"   # curvein the shape of x^{distance}

class ContinuationType(str, Enum):
    BLUNT = "blunt"
    FADE = "fade"
    DASHED = "dashed"
    ARROW = "arrow"
    #...

class MarginsConfig(BaseModel):
    side_margin: float = 30.0
    lane_margin: float = 50.0
    commit_margin: float = 20.0

class NodesLayoutConfig(BaseModel):
    toggled : bool = True
    display_type : NodeDisplayType = NodeDisplayType.DOUBLE_CIRCLE
    node_radius: float = 10.0

class LaneChangeConfig(BaseModel):
    type: LaneChangeType = LaneChangeType.LINEAR
    margin: float = 10.0

class BranchLayoutConfig(BaseModel):
    stroke_width: float = 5.0
    decrement_per_branch:  float = 1.0
    max_decrement: float = 2.0
    continuation_type: ContinuationType = ContinuationType.FADE 

class ConnectionConfig(BaseModel):
    lane_change: LaneChangeConfig
    branch: BranchLayoutConfig
    

class LayoutConfig(BaseModel):
    orientation: str = "horizontal"     # horizontal || vertical
    margins: MarginsConfig
    nodes: NodesLayoutConfig
    connections: BranchLayoutConfig

"""
Git Config 
"""

class GitConfig(BaseModel):
    project_name: str
    project_url: str
    project_description: str


"""
Track Config
"""

class TrackConfig(BaseModel):
    git_info: GitConfig
    style_config: StyleConfig
    layout_config: LayoutConfig
    track: Track


"""
Config Factory
"""

# --- default configs ---
def get_default_style_config() -> StyleConfig:
    return StyleConfig(
        line_config=LineStyleConfig(
            color_palatte=LineColorPalette(
                name="default-line", 
                type=LineColorType.BRANCH_INDEXED, 
                colors=["#000000"]
            )
        ),
        node_config=NodeStyleConfig(
            color_palatte=NodeColorPalette(
                name="default-node", 
                type=NodeColorType.BRANCH_BASED, 
                colors={
                    "commit" : "#000000",
                    "branch" : "#000000",
                    "merge" : "#000000"
                }
            )
        )
    )

def get_default_layout_config() -> LayoutConfig:
    return LayoutConfig(
        orientation="horizontal",
        margins=MarginsConfig(
            side_margin=30.0, 
            lane_margin=50.0, 
            commit_margin=20.0),
        nodes=NodesLayoutConfig(
            toggled=True, 
            node_radius=10.0),
        connections=BranchLayoutConfig(
            stroke_width=5.0)
    )

