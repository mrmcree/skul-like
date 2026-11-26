class_name GameCamera
extends Camera2D
## Follows a target and shakes when GameFeel.shake() is called.
## Shake = a directional kick that springs back + random jitter that fades out.
## Runs on real time so it keeps moving during hit stop.

const KICK_PER_STRENGTH := 1.5
const KICK_RECOVERY_SPEED := 40.0

@export var target: Node2D
@export var follow_offset := Vector2(0, -30)

var _shake_strength := 0.0
var _shake_time := 0.0
var _shake_duration := 0.001
var _kick := Vector2.ZERO


func _ready() -> void:
	GameFeel.shake_requested.connect(_on_shake_requested)


func _physics_process(_delta: float) -> void:
	if target:
		global_position = target.global_position + follow_offset


func _process(delta: float) -> void:
	var real_delta := delta / maxf(Engine.time_scale, 0.001)
	_kick = _kick.move_toward(Vector2.ZERO, KICK_RECOVERY_SPEED * real_delta)
	var jitter := Vector2.ZERO
	if _shake_time > 0.0:
		_shake_time -= real_delta
		var fade := clampf(_shake_time / _shake_duration, 0.0, 1.0)
		jitter = Vector2(randf_range(-1.0, 1.0), randf_range(-1.0, 1.0)) * _shake_strength * fade
	offset = (_kick + jitter).round()


func _on_shake_requested(strength: float, duration: float, direction: Vector2) -> void:
	_shake_strength = maxf(_shake_strength if _shake_time > 0.0 else 0.0, strength)
	_shake_time = maxf(_shake_time, duration)
	_shake_duration = maxf(_shake_time, 0.001)
	_kick += direction.normalized() * strength * KICK_PER_STRENGTH
