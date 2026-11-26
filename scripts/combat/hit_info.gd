class_name HitInfo
extends RefCounted
## Everything a target needs to know about a single hit.

var damage: int
## Already flipped to point away from the attacker.
var knockback: Vector2
## 1 = hit came from the left (pushes right), -1 = from the right.
var direction: int
## Freeze-frame duration in seconds; targets shudder for this long.
var hit_stop: float
## Finishers / big hits: stronger reaction, screen flash, heavy sound.
var heavy: bool


func _init(p_damage: int, p_knockback: Vector2, p_direction: int, p_hit_stop: float, p_heavy: bool) -> void:
	damage = p_damage
	knockback = p_knockback
	direction = p_direction
	hit_stop = p_hit_stop
	heavy = p_heavy
