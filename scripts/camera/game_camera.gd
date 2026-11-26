class_name GameCamera
extends Camera2D
## Follows a target and shakes on GameFeel.trauma_added (game-feel skill's trauma model):
##   - trauma (0..1) is added by hits and decays linearly in REAL time, so the shake keeps
##     settling during hit stop instead of freezing off-centre;
##   - shake amount = trauma² × the player's shake setting: light hits barely move the
##     screen, heavy hits punch;
##   - the offset follows summed sines (smooth), never a fresh random value per frame;
##   - a directional kick toward the hit springs back exponentially.
## No camera roll: rotating pixel art smears it.

const TRAUMA_DECAY := 1.5            # trauma lost per real second (0.75 trauma ≈ 0.5 s)
const MAX_OFFSET := Vector2(4.0, 3.0)    # logical px at full trauma
const KICK_PER_TRAUMA := 6.0         # logical px of kick per unit of trauma
const KICK_RECOVERY := 12.0          # exponential spring-back rate per second

@export var target: Node2D
@export var follow_offset := Vector2(0, -30)

var trauma := 0.0
var _kick := Vector2.ZERO
var _t := 0.0


func _ready() -> void:
	GameFeel.trauma_added.connect(_on_trauma_added)


func _physics_process(_delta: float) -> void:
	if target:
		global_position = target.global_position + follow_offset


func _process(delta: float) -> void:
	var real_dt := delta / maxf(Engine.time_scale, 0.0001)
	_t += real_dt
	trauma = maxf(trauma - TRAUMA_DECAY * real_dt, 0.0)
	_kick = _kick.lerp(Vector2.ZERO, 1.0 - exp(-KICK_RECOVERY * real_dt))
	if trauma == 0.0 and _kick.length_squared() < 0.0001:
		_kick = Vector2.ZERO
		offset = Vector2.ZERO
		return
	var setting := GameSettings.shake_scale
	var amount := trauma * trauma * setting
	var wobble := Vector2(MAX_OFFSET.x * _axis(0.0), MAX_OFFSET.y * _axis(7.3)) * amount
	offset = wobble + _kick * setting


## Smooth pseudo-noise in -1..1: two sines at unrelated rates (~6 and ~10 Hz), fast enough
## that a ~0.4 s heavy shake gets 2-3 tight oscillations instead of one slow sway.
func _axis(seed: float) -> float:
	return 0.6 * sin(_t * 40.0 + seed) + 0.4 * sin(_t * 63.0 + seed * 2.0)


func _on_trauma_added(amount: float, direction: Vector2) -> void:
	trauma = clampf(trauma + amount, 0.0, 1.0)   # hits add up, they don't reset
	if direction != Vector2.ZERO:
		_kick += direction.normalized() * amount * KICK_PER_TRAUMA
