class_name Hurtbox
extends Area2D
## Damage-receiving area. The owner listens to `hurt` and decides what happens.
## While `invulnerable` (dash i-frames, post-hit blink, dead), hits pass through
## without being counted, so they don't trigger the attacker's impact effects.

signal hurt(hit: HitInfo)

var invulnerable := false


func take_hit(hit: HitInfo) -> void:
	hurt.emit(hit)
