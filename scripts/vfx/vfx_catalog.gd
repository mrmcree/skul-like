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
