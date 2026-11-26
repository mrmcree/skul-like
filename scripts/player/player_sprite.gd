class_name PlayerSprite
extends AnimatedSprite2D
## The heroine's animations. Sheet made by tools/process_sprites.py from the Jimeng
## sheets in assets/raw/hero (Move.png + Combat.png): 128x96 cells, faces right,
## feet at FEET, drawn at DENSITY texels per game pixel (so scaled by 1 / DENSITY).

const SHEET := preload("res://assets/characters/hero/hero.png")
const FRAME_SIZE := Vector2i(128, 96)
const FEET := Vector2(64, 90)
const DENSITY := 2.0
const RUN_SPEED_THRESHOLD := 10.0
## name: [row, first column, frame count, fps, loop]
const ANIMS := {
	&"idle": [0, 0, 6, 8.0, true],
	&"run": [1, 0, 8, 14.0, true],
	&"jump": [2, 0, 3, 14.0, false],
	&"fall": [2, 3, 1, 1.0, false],
	&"dash": [3, 0, 4, 24.0, false],
	&"attack_1": [4, 0, 6, 10.0, false],
	&"attack_2": [5, 0, 6, 10.0, false],
	&"attack_3": [6, 0, 6, 10.0, false],
	&"hurt": [7, 0, 3, 12.0, false],
	&"death": [8, 0, 6, 10.0, false],
	# Skill rows from assets/raw/hero/Skills.png. Used only once the processed sheet has them
	# (see _has_row); until then skills fall back to the combo rows.
	&"attack_spin": [9, 0, 6, 10.0, false],
	&"attack_rising": [10, 0, 6, 10.0, false],
}
const ATTACK_ANIMS: Array[StringName] = [&"attack_1", &"attack_2", &"attack_3"]
## Frames shown during [wind-up, swing, follow-through] for each attack row.
const DEFAULT_PHASES := [[0, 1], [2, 3], [4, 5]]
const ATTACK_PHASES := {
	# Horizontal cut peaks on frame 2; frame 3 already pulls the blade back.
	&"attack_1": [[0, 1], [2], [3, 4, 5]],
	# The thrust row pulls back for three frames and only stabs on frame 3.
	&"attack_3": [[0, 1, 2], [3], [4, 5]],
	# The whole turn plays during the wind-up (crouch, front, facing us, back) while the slash
	# effect draws its ring; the hit lands on frame 4 as she turns back to the front.
	&"attack_spin": [[0, 1, 2, 3], [4], [5]],
	# Crouch, leap and cut upward, then the airborne follow-through.
	&"attack_rising": [[0, 1], [2, 3], [4, 5]],
}

static var _frames: SpriteFrames
static var _available: Dictionary = {}


func _ready() -> void:
	if _frames == null:
		var anims := {}
		for anim: StringName in ANIMS:
			if _has_row(int(ANIMS[anim][0])):
				anims[anim] = ANIMS[anim]
				_available[anim] = true
		_frames = SheetFrames.build(SHEET, FRAME_SIZE, anims)
	sprite_frames = _frames
	centered = false
	offset = -FEET
	scale = Vector2.ONE / DENSITY
	play(&"idle")


## Pick idle / run / jump / fall / dash from the body's current motion.
func update_locomotion(on_floor: bool, velocity: Vector2, dashing: bool) -> void:
	var anim := &"idle"
	if dashing:
		anim = &"dash"
	elif not on_floor:
		anim = &"jump" if velocity.y < 0.0 else &"fall"
	elif absf(velocity.x) > RUN_SPEED_THRESHOLD:
		anim = &"run"
	speed_scale = 1.0
	if animation != anim:
		play(anim)


## Play a fixed pose/animation at normal speed ("hurt", "death").
func play_pose(anim: StringName) -> void:
	speed_scale = 1.0
	play(anim)
	set_frame_and_progress(0, 0.0)


## Start combo hit `index`. Frames are then driven by show_attack_time(), so the
## swing drawing lines up exactly with the hitbox.
func play_attack(index: int) -> void:
	speed_scale = 1.0
	play(ATTACK_ANIMS[clampi(index, 0, ATTACK_ANIMS.size() - 1)])
	pause()
	frame = 0


## Show the frame for time `t` into the attack: each phase (startup = wind-up,
## active = the swing, recovery = follow-through) steps through its own frames.
func show_attack_time(t: float, attack: AttackData) -> void:
	var phases: Array = ATTACK_PHASES.get(animation, DEFAULT_PHASES)
	var phase := 0
	var progress := t / maxf(attack.startup, 0.001)
	if t >= attack.startup + attack.active:
		phase = 2
		progress = (t - attack.startup - attack.active) / maxf(attack.recovery, 0.001)
	elif t >= attack.startup:
		phase = 1
		progress = (t - attack.startup) / maxf(attack.active, 0.001)
	var frames: Array = phases[phase]
	frame = frames[clampi(int(progress * frames.size()), 0, frames.size() - 1)]


## Play a skill's own row if the sheet has it, else combo row `fallback_index`. Frames are then
## driven by show_attack_time(), like play_attack().
func play_skill(anim: StringName, fallback_index: int) -> void:
	if anim != &"" and _available.has(anim):
		speed_scale = 1.0
		play(anim)
		pause()
		frame = 0
	else:
		play_attack(fallback_index)


static func _has_row(row: int) -> bool:
	return SHEET.get_height() >= (row + 1) * FRAME_SIZE.y
