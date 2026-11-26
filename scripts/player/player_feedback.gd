class_name PlayerFeedback
extends RefCounted
## All the "juice" for the player's actions — VFX, SFX, camera shake, flashes —
## so player.gd can stay about movement and combat logic.

var _player: Player


func _init(player: Player) -> void:
	_player = player


func on_jump(from_ground: bool) -> void:
	var at := _player.global_position
	if from_ground:
		Vfx.spawn("dust_jump", _world(), at, _player.facing, 0)
	else:
		Vfx.spawn("puff", _world(), at + Vector2(0, -2), _player.facing, 0)
	Sfx.play("jump", -6.0)


func on_land() -> void:
	Vfx.spawn("dust_land", _world(), _player.global_position, _player.facing, 0)
	Sfx.play("land", -4.0)


## Dust kicked up at the feet plus a speed streak trailing behind the body.
func on_dash(on_floor: bool) -> void:
	var facing := _player.facing
	if on_floor:
		Vfx.spawn("dust_land", _world(), _player.global_position, -facing, 0)
	var streak_at := _player.global_position + Vector2(-facing * 4.0, -11.0)
	Vfx.spawn("dash_streak", _world(), streak_at, facing, -1)
	Sfx.play("dash", -3.0)


## The samurai sheet already draws its slash arcs, so light hits only need sound.
## The heavy stab gets a speed streak along the blade.
func on_swing(attack: AttackData, combo_index: int) -> void:
	var facing := _player.facing
	var feet := _player.global_position
	if attack.heavy:
		Vfx.spawn("slash_heavy", _player, feet + Vector2(facing * 6.0, 2.0), facing, 5)
	else:
		var arc := Vfx.spawn("slash_light", _player, feet + Vector2(facing * 4.0, 0.0), facing, 5)
		if arc and combo_index == 1:
			# Second hit is an upward cut: tilt the arc up (mirrors with facing).
			arc.rotation = -0.7 * facing
	Sfx.play("swing_heavy" if attack.heavy else "swing_light", -2.0)


## Impact: freeze, shake toward the hit, sound, sparks (bigger for heavy hits).
func on_hit(target: Hurtbox, attack: AttackData) -> void:
	var facing := _player.facing
	GameFeel.hit_stop(attack.hit_stop)
	GameFeel.shake(attack.shake_strength, 0.2 if attack.heavy else 0.1, Vector2(facing, 0))
	Sfx.play("hit_heavy" if attack.heavy else "hit_light")
	var at := Vector2(target.global_position.x - facing * 6.0, target.global_position.y - 16.0)
	Vfx.spawn("hit_crit" if attack.heavy else "hit_spark", _world(), at, facing, 6)
	ImpactBurst.spawn(_world(), at, facing, attack.heavy)


## Player got hit: heavier freeze and a shake away from the attacker.
func on_hurt(hit: HitInfo) -> void:
	GameFeel.hit_stop(maxf(hit.hit_stop, 0.08))
	GameFeel.shake(2.5, 0.2, Vector2(hit.direction, 0))
	Sfx.play("hit_heavy", 0.0, 0.03)
	var at := _player.global_position + Vector2(0, -14)
	ImpactBurst.spawn(_world(), at, hit.direction, false)


func on_death() -> void:
	Sfx.play("break")
	GameFeel.shake(3.0, 0.3)


func on_respawn() -> void:
	Vfx.spawn("puff", _world(), _player.global_position, 1, 2)


func _world() -> Node:
	return _player.get_parent()
