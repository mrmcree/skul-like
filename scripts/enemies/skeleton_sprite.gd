class_name SkeletonSprite
extends AnimatedSprite2D
## Skeleton ashigaru animations. Sheet made by tools/process_sprites.py from the
## Jimeng strips in assets/raw/skeleton: 160x96 cells, feet at ANCHOR, faces right.
## Drawn at DENSITY texels per game pixel (the game renders at window resolution,
## so the extra detail shows), hence the sprite is scaled by 1 / DENSITY.

signal action_finished(anim: StringName)

const SHEET := preload("res://assets/characters/skeleton/skeleton.png")
const CELL := Vector2i(160, 96)
const ANCHOR := Vector2(80, 90)
const DENSITY := 2.0
## name: [row, first column, frame count, fps, loop]
const ANIMS := {
	&"idle": [0, 0, 6, 6.0, true],
	&"walk": [1, 0, 6, 10.0, true],
	&"attack": [2, 0, 6, 12.0, false],
	&"hit": [3, 2, 2, 12.0, false],
	&"death": [4, 0, 6, 10.0, false],
}

static var _frames: SpriteFrames


func _ready() -> void:
	if _frames == null:
		_frames = SheetFrames.build(SHEET, CELL, ANIMS)
	sprite_frames = _frames
	centered = false
	offset = -ANCHOR
	scale = Vector2.ONE / DENSITY
	animation_finished.connect(func() -> void: action_finished.emit(animation))
	play(&"idle")


## Face left (-1) or right (1). The anchor is centred in the cell, so flipping is symmetric.
func face(direction: int) -> void:
	flip_h = direction < 0


func play_once(anim: StringName) -> void:
	play(anim)
	set_frame_and_progress(0, 0.0)
