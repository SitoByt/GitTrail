from gittrail_core.config.config_model import TrackConfig
from gittrail_core.track.visualizer import display_via_cmdln

def create_track_config(git_info, track, loaded_style_config, loaded_layout_config):
    track_config = TrackConfig(
        git_info=git_info,
        track=track,
        style_config=loaded_style_config,
        layout_config=loaded_layout_config
    )

    config = track_config.model_dump_json(indent=2)

    with open("output/test.json", "w", encoding="utf-8") as f:
        f.write(config)