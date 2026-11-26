class_name VfxCatalog
extends RefCounted
## Sprite-sheet metadata for every effect in res://assets/vfx/<name>.png.
## Sheets are exported from pixelfx (MIT, see assets/vfx/LICENSE-pixelfx.txt) as a grid of
## equally sized frames, read left to right, top to bottom.
## Keys: frame_size (px), frames, columns, fps, loop, pivot (px inside a frame that is placed
## at the spawn position; the effect faces right and is mirrored by Vfx.facing).

const SHEET_DIR := "res://assets/vfx/"

const EFFECTS := {
	"brazier": {"frame_size": Vector2i(17, 43), "frames": 90, "columns": 60, "fps": 30.0, "loop": true, "pivot": Vector2(8, 43)},
	"dash_streak": {"frame_size": Vector2i(32, 16), "frames": 2, "columns": 2, "fps": 20.0, "loop": false, "pivot": Vector2(26, 8)},
	"dust_jump": {"frame_size": Vector2i(40, 12), "frames": 20, "columns": 20, "fps": 40.0, "loop": false, "pivot": Vector2(20, 8)},
	"dust_land": {"frame_size": Vector2i(54, 16), "frames": 24, "columns": 18, "fps": 40.0, "loop": false, "pivot": Vector2(27, 11)},
	"hit_crit": {"frame_size": Vector2i(77, 37), "frames": 14, "columns": 13, "fps": 40.0, "loop": false, "pivot": Vector2(29, 24)},
	"hit_spark": {"frame_size": Vector2i(46, 31), "frames": 10, "columns": 10, "fps": 40.0, "loop": false, "pivot": Vector2(6, 21)},
	"puff": {"frame_size": Vector2i(32, 27), "frames": 22, "columns": 22, "fps": 36.0, "loop": false, "pivot": Vector2(14, 24)},
	"slash_heavy": {"frame_size": Vector2i(66, 50), "frames": 14, "columns": 14, "fps": 40.0, "loop": false, "pivot": Vector2(21, 49)},
	"slash_light": {"frame_size": Vector2i(54, 44), "frames": 12, "columns": 12, "fps": 40.0, "loop": false, "pivot": Vector2(18, 42)},
	"slash_1": {"frame_size": Vector2i(92, 44), "frames": 5, "columns": 5, "fps": 32.0, "loop": false, "pivot": Vector2(20, 22), "density": 2.0},
	"slash_2": {"frame_size": Vector2i(68, 84), "frames": 5, "columns": 5, "fps": 32.0, "loop": false, "pivot": Vector2(18, 48), "density": 2.0},
	"slash_3": {"frame_size": Vector2i(120, 56), "frames": 5, "columns": 5, "fps": 28.0, "loop": false, "pivot": Vector2(18, 28), "density": 2.0},
}


## Effects exported straight from pixelfx (`node tools/render.mjs <id> --sheet`, or
## tools/export_skill_vfx.py) need no entry above: put <name>.png and <name>.json in
## assets/vfx/ and the JSON's meta.pixelfx (frame size, frames, columns, fps, loop, pivot) is used.
static var _json_cache: Dictionary = {}


## Metadata for an effect, or {} if it has no sheet (warns once per name).
static func info(effect_name: String) -> Dictionary:
	if EFFECTS.has(effect_name):
		return EFFECTS[effect_name]
	if _json_cache.has(effect_name):
		return _json_cache[effect_name]
	var result := _read_pixelfx_json(effect_name)
	if result.is_empty():
		push_warning("VfxCatalog: no sheet for '%s' (run python tools/export_skill_vfx.py)" % effect_name)
	_json_cache[effect_name] = result
	return result


static func _read_pixelfx_json(effect_name: String) -> Dictionary:
	var json_path := SHEET_DIR + effect_name + ".json"
	if not ResourceLoader.exists(SHEET_DIR + effect_name + ".png"):
		return {}
	var data: Variant = null
	if ResourceLoader.exists(json_path):
		var res := load(json_path)
		if res is JSON:
			data = (res as JSON).data
	if data == null and FileAccess.file_exists(json_path):
		data = JSON.parse_string(FileAccess.get_file_as_string(json_path))
	if not data is Dictionary:
		return {}
	var meta: Dictionary = (data as Dictionary).get("meta", {}).get("pixelfx", {})
	if meta.is_empty():
		return {}
	var size: Array = meta["frameSize"]
	var pivot: Array = meta["pivot"]
	return {
		"frame_size": Vector2i(int(size[0]), int(size[1])),
		"frames": int(meta["frames"]),
		"columns": int(meta["columns"]),
		"fps": float(meta["fps"]),
		"loop": bool(meta["loop"]),
		"pivot": Vector2(float(pivot[0]), float(pivot[1])),
		"density": float(meta.get("density", 1.0)),
	}
