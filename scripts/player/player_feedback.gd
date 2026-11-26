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
	Sfx.play("jump", -11.0)


func on_land() -> void:
	Vfx.spawn("dust_land", _world(), _player.global_position, _player.facing, 0)
	Sfx.play("land", -9.0)


## Dust kicked up at the feet plus a speed streak trailing behind the body.
func on_dash(on_floor: bool) -> void:
	var facing := _player.facing
	if on_floor:
		Vfx.spawn("dust_land", _world(), _player.global_position, -facing, 0)
	var streak_at := _player.global_position + Vector2(-facing * 4.0, -11.0)
	Vfx.spawn("dash_streak", _world(), streak_at, facing, -1)
	Sfx.play("dash", -8.0)


## Spawn the matching 2x katana trail in world space and trigger per-hit katana audio.
func on_swing(attack: AttackData, combo_index: int) -> void:
	var facing := _player.facing
	var feet := _player.global_position
	match combo_index:
		0:
			Vfx.spawn("slash_1", _world(), feet + Vector2(facing * 8.0, -14.0), facing, 5)
			Sfx.play("katana_slash_1", 0.0, 0.06)
		1:
			Vfx.spawn("slash_2", _world(), feet + Vector2(facing * 2.0, -19.0), facing, 5)
			Sfx.play("katana_slash_2", 0.0, 0.06)
		_:
			Vfx.spawn("slash_3", _world(), feet + Vector2(facing * 12.0, -18.0), facing, 5)
			Sfx.play("katana_thrust", 1.0, 0.05)


## Skill wind-up: 一闪 crouches with a puff of dust, the others just whoosh.
func on_skill_windup(skill: SkillData) -> void:
	if skill.kind == SkillData.Kind.ISSEN:
		Vfx.spawn("dust_land", _world(), _player.global_position, _player.facing, 0)
		Sfx.play("swing_heavy", -6.0, 0.04)


## The skill's pixelfx effect (front layer over the body, optional back layer under it) and its
## swing sound. Returns the spawned effects so an interrupted skill can remove them.
func on_skill_vfx(skill: SkillData) -> Array[Vfx]:
	var facing := _player.facing
	var at := _player.global_position + Vector2(skill.vfx_offset.x * facing, skill.vfx_offset.y)
	var spawned: Array[Vfx] = []
	if skill.vfx_back != "":
		var back := Vfx.spawn(skill.vfx_back, _world(), at, facing, -1)
		if back:
			spawned.append(back)
	if skill.vfx != "":
		var front := Vfx.spawn(skill.vfx, _world(), at, facing, 5)
		if front:
			spawned.append(front)
	if skill.swing_sound != "":
		Sfx.play(skill.swing_sound, 1.0, 0.05)
	return spawned


## The hitbox opens: some body dust per skill.
func on_skill(skill: SkillData) -> void:
	var facing := _player.facing
	var feet := _player.global_position
	match skill.kind:
		SkillData.Kind.ISSEN:
			Vfx.spawn("dust_land", _world(), feet, -facing, 0)
			Vfx.spawn("dash_streak", _world(), feet + Vector2(-facing * 4.0, -11.0), facing, -1)
		SkillData.Kind.RISING:
			if _player.is_on_floor():
				Vfx.spawn("dust_jump", _world(), feet, facing, 0)


## 一闪 after the sheathing beat: the cuts land (on_hit runs per target), then the click.
func on_issen_release(_skill: SkillData, hits: int) -> void:
	Sfx.play("katana_thrust", 2.0, 0.02)
	if hits == 0:
		GameFeel.shake(1.0, Vector2(_player.facing, 0))


func on_parry_start() -> void:
	Sfx.play("swing_light", -6.0, 0.05)


## Blades clash: big freeze, gold star at the contact point, heavy ring.
func on_parry(hit: HitInfo) -> void:
	var facing := _player.facing
	var at := _player.global_position + Vector2(facing * 10.0, -16.0)
	GameFeel.hit_stop(0.14)
	GameFeel.shake(2.5, Vector2(-hit.direction, 0))
	Vfx.spawn("parry_clash", _world(), at, facing, 7)
	Sfx.play("katana_thrust", 3.0, 0.02)
	Sfx.play("hit_heavy", -2.0, 0.04)


## Impact: freeze, shake toward the hit, sound, sparks (bigger for heavy hits).
func on_hit(target: Hurtbox, attack: AttackData) -> void:
	var facing := _player.facing
	GameFeel.hit_stop(attack.hit_stop)
	GameFeel.shake(attack.shake_strength, Vector2(facing, 0))
	Sfx.play("hit_heavy" if attack.heavy else "hit_light", 2.0 if attack.heavy else 1.0)
	var at := Vector2(target.global_position.x - facing * 6.0, target.global_position.y - 16.0)
	Vfx.spawn("hit_crit" if attack.heavy else "hit_spark", _world(), at, facing, 6)
	ImpactBurst.spawn(_world(), at, facing, attack.heavy)


## Player got hit: heavier freeze and a shake away from the attacker.
func on_hurt(hit: HitInfo) -> void:
	GameFeel.hit_stop(maxf(hit.hit_stop, 0.08))
	GameFeel.shake(2.5, Vector2(hit.direction, 0))
	Sfx.play("spear_hit", 0.0, 0.06)
	var at := _player.global_position + Vector2(0, -14)
	ImpactBurst.spawn(_world(), at, hit.direction, false)


func on_death() -> void:
	Sfx.play("break")
	GameFeel.shake(3.0)


func on_respawn() -> void:
	Vfx.spawn("puff", _world(), _player.global_position, 1, 2)


func _world() -> Node:
	return _player.get_parent()
