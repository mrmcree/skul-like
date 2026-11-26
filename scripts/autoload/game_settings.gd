extends Node
## Persistent user settings (autoload `GameSettings`).
## Saved to user://settings.cfg and applied immediately on startup/change.

signal changed
signal menu_toggle_requested

const CONFIG_PATH := "user://settings.cfg"

var master_volume := 0.85
var sfx_volume := 0.80
var weapon_volume := 0.75
var shake_scale := 1.0
var hit_stop_enabled := true
var fullscreen := false


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	load_settings()
	apply_all()


func apply_all() -> void:
	var mute := master_volume <= 0.001
	AudioServer.set_bus_mute(0, mute)
	AudioServer.set_bus_volume_db(0, linear_to_db(maxf(master_volume, 0.001)))
	if DisplayServer.get_name() != "headless":
		var target := DisplayServer.WINDOW_MODE_EXCLUSIVE_FULLSCREEN if fullscreen else DisplayServer.WINDOW_MODE_WINDOWED
		if DisplayServer.window_get_mode() != target:
			DisplayServer.window_set_mode(target)


func set_master_volume(value: float) -> void:
	master_volume = clampf(value, 0.0, 1.0)
	_commit()


func set_sfx_volume(value: float) -> void:
	sfx_volume = clampf(value, 0.0, 1.0)
	_commit()


func set_weapon_volume(value: float) -> void:
	weapon_volume = clampf(value, 0.0, 1.0)
	_commit()


func set_shake_scale(value: float) -> void:
	shake_scale = clampf(value, 0.0, 1.0)
	_commit()


func set_hit_stop_enabled(enabled: bool) -> void:
	hit_stop_enabled = enabled
	_commit()


func set_fullscreen(enabled: bool) -> void:
	fullscreen = enabled
	_commit()


func reset_defaults() -> void:
	master_volume = 0.85
	sfx_volume = 0.80
	weapon_volume = 0.75
	shake_scale = 1.0
	hit_stop_enabled = true
	fullscreen = false
	_commit()


func request_toggle_menu() -> void:
	menu_toggle_requested.emit()


func save_settings() -> void:
	var cfg := ConfigFile.new()
	cfg.set_value("audio", "master_volume", master_volume)
	cfg.set_value("audio", "sfx_volume", sfx_volume)
	cfg.set_value("audio", "weapon_volume", weapon_volume)
	cfg.set_value("gameplay", "shake_scale", shake_scale)
	cfg.set_value("gameplay", "hit_stop_enabled", hit_stop_enabled)
	cfg.set_value("video", "fullscreen", fullscreen)
	cfg.save(CONFIG_PATH)


func load_settings() -> void:
	var cfg := ConfigFile.new()
	if cfg.load(CONFIG_PATH) != OK:
		return
	master_volume = clampf(float(cfg.get_value("audio", "master_volume", 0.85)), 0.0, 1.0)
	sfx_volume = clampf(float(cfg.get_value("audio", "sfx_volume", 0.80)), 0.0, 1.0)
	weapon_volume = clampf(float(cfg.get_value("audio", "weapon_volume", 0.75)), 0.0, 1.0)
	shake_scale = clampf(float(cfg.get_value("gameplay", "shake_scale", 1.0)), 0.0, 1.0)
	hit_stop_enabled = bool(cfg.get_value("gameplay", "hit_stop_enabled", true))
	fullscreen = bool(cfg.get_value("video", "fullscreen", false))


func _commit() -> void:
	apply_all()
	save_settings()
	changed.emit()
