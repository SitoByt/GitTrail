from gittrail_core.config.config_model import TrackConfig, get_default_layout_config, get_default_style_config

def create_track_config(git_info, track, loaded_style_config, loaded_layout_config) -> TrackConfig:
    track_config = TrackConfig(
        git_info=git_info,
        track=track,
        style_config=loaded_style_config,
        layout_config=loaded_layout_config
    )
    return track_config

def generate_default_track_config(track: Track, git_info: GitConfig) -> TrackConfig:
    return TrackConfig(
        git_info=git_info,
        track=track,
        style_config=get_default_style_config(),
        layout_config=get_default_layout_config()
    )

def write_track_config(track_config: TrackConfig):
    config = track_config.model_dump_json(indent=2)
    with open("output/test.json", "w", encoding="utf-8") as f:
        f.write(config)

def load_track_config(json_path: str):
    pass # TODO: return the json based off the provided path
    