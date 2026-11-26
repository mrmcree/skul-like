extends Node
## Global "juice" helpers (autoload `GameFeel`):
## - hit_stop: brief freeze on impact so hits read clearly
## - shake: camera shake with an optional directional kick (sells the impact)

signal shake_requested(strength: float, duration: float, direction: Vector2)

const HIT_STOP_TIME_SCALE := 0.05

var _hit_stop_active := false


func hit_stop(duration: float) -> void:
	if duration <= 0.0 or _hit_stop_active:
		return
	_hit_stop_active = true
	Engine.time_scale = HIT_STOP_TIME_SCALE
	# ignore_time_scale = true, otherwise the timer itself would be slowed down.
	await get_tree().create_timer(duration, true, false, true).timeout
	Engine.time_scale = 1.0
	_hit_stop_active = false


## `direction` kicks the camera that way first (e.g. the direction of the hit).
func shake(strength: float, duration: float, direction := Vector2.ZERO) -> void:
	if strength > 0.0:
		shake_requested.emit(strength, duration, direction)
