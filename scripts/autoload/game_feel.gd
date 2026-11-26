extends Node
## Global "juice" helpers (autoload `GameFeel`):
## - hit_stop: brief freeze on impact so hits read clearly
## - shake: adds camera trauma (shake = trauma², decays on its own) plus a directional kick
##
## Tiers (game-feel skill): light hit ~0.05 s freeze / shake 1, heavy hit ~0.13 s / shake 3.
## Keep freezes under ~0.15 s so input never feels laggy.

## Emitted for the camera. `amount` is trauma (0..1) to add, `direction` the hit direction.
signal trauma_added(amount: float, direction: Vector2)

const HIT_STOP_TIME_SCALE := 0.05
## shake(strength) adds strength × this much trauma: 1 → 0.25 (light), 3 → 0.75 (heavy).
const TRAUMA_PER_STRENGTH := 0.25

var _hit_stop_id := 0
var _hit_stop_end_ms := 0


## Freeze time for `duration` real seconds. Overlapping calls extend the freeze to whichever
## ends last, and only the newest call restores time, so a heavy hit is never cut short by
## the end of an earlier light one.
func hit_stop(duration: float) -> void:
	if not GameSettings.hit_stop_enabled or duration <= 0.0:
		return
	var now := Time.get_ticks_msec()
	_hit_stop_end_ms = maxi(_hit_stop_end_ms, now + int(duration * 1000.0))
	_hit_stop_id += 1
	var my_id := _hit_stop_id
	Engine.time_scale = HIT_STOP_TIME_SCALE
	# ignore_time_scale = true, otherwise the timer itself would be slowed down.
	var wait := float(_hit_stop_end_ms - now) / 1000.0
	await get_tree().create_timer(wait, true, false, true).timeout
	if my_id == _hit_stop_id:
		Engine.time_scale = 1.0


## Camera shake. `strength` uses the AttackData scale (1 light … 4 max);
## `direction` kicks the camera that way first. The player's shake setting is
## applied by the camera, so trauma bookkeeping stays the same at any setting.
func shake(strength: float, direction := Vector2.ZERO) -> void:
	if strength > 0.0:
		trauma_added.emit(strength * TRAUMA_PER_STRENGTH, direction)
