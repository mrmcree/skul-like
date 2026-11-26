class_name PlayerHealth
extends Node
## Player hit points plus post-hit invincibility (with blinking).

signal changed(hp: int, max_hp: int)
signal died

@export var max_hp := 100
## Seconds of invincibility after taking a hit.
@export var invincible_time := 1.0
## What blinks while invincible.
@export var blink_target: CanvasItem

const BLINK_INTERVAL := 0.06

var hp := 0
var _invincible_timer := 0.0


func _ready() -> void:
	hp = max_hp


func _process(delta: float) -> void:
	if _invincible_timer <= 0.0:
		return
	_invincible_timer -= delta
	if blink_target:
		var on := int(_invincible_timer / BLINK_INTERVAL) % 2 == 0
		blink_target.modulate.a = 1.0 if on or _invincible_timer <= 0.0 else 0.35


func is_invincible() -> bool:
	return _invincible_timer > 0.0


func is_dead() -> bool:
	return hp <= 0


## Apply damage and start invincibility. Emits `died` when HP reaches 0.
func take(damage: int) -> void:
	hp = maxi(hp - damage, 0)
	_invincible_timer = invincible_time
	changed.emit(hp, max_hp)
	if hp == 0:
		died.emit()


func restore() -> void:
	hp = max_hp
	_invincible_timer = invincible_time
	changed.emit(hp, max_hp)
