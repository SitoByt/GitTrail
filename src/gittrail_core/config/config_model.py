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