class_name PlayerSkills
extends RefCounted
## The samurai's skills (U / I / O / Y): cooldowns, input buffer and the SKILL state for Player.
##   一闪 ISSEN   wind-up, dash through enemies untouchable, sheathe, every cut lands at once
##   十字斩 CROSS  a down cut and an up cut crossing it; the second hit is the heavy one
##   燕返·升 RISING  rising cut that launches the target and carries the samurai up after it
##   瞬身斩 BLINK  vanish, reappear behind the nearest enemy facing it, and cut
##   (旋风斩 SPIN is still supported: data/skills/spin.tres)
## Skills can cancel combo recovery, and their own recovery cancels into dash / jump / a skill.

const ACTIONS: Array[StringName] = [&"skill_1", &"skill_2", &"skill_3", &"skill_4"]
const DEFAULT_PATHS: Array[String] = [
	"res://data/skills/issen.tres",
	"res://data/skills/cross.tres",
	"res://data/skills/rising.tres",
	"res://data/skills/blink.tres",
]
## BLINK: vertical reach for picking a target (px).
const BLINK_VERTICAL := 48.0
const BUFFER_TIME := 0.15
## Max fall speed while hanging in the air during a skill.
const HANG_FALL_SPEED := 30.0

var skills: Array[SkillData] = []
var current: SkillData

var _player: Player
var _cooldowns: Array[float] = []
var _buffered := -1
var _buffer_timer := 0.0
var _time := 0.0
var _opened := false
var _closed := false
var _released := false
var _rising_used := false
var _vfx_started := false
var _vfx: Array[Vfx] = []
# CROSS second cut
var _fu_started := false
var _fu_opened := false
var _fu_closed := false
# BLINK
var _hidden := false
var _shown := false
var _blink_target := Vector2.ZERO
var _blink_face := 1
var _cut := AttackData.new()


func _init(player: Player, list: Array[SkillData]) -> void:
	_player = player
	skills = list
	if skills.is_empty():
		for path in DEFAULT_PATHS:
			var skill := load(path) as SkillData
			if skill:
				skills.append(skill)
	_cooldowns.resize(skills.size())
	_cooldowns.fill(0.0)


func count() -> int:
	return skills.size()


## 1.0 when skill `index` is ready, rising from 0 while it recharges (drives the HUD).
func ready_ratio(index: int) -> float:
	if index < 0 or index >= skills.size():
		return 0.0
	return 1.0 - clampf(_cooldowns[index] / maxf(skills[index].cooldown, 0.001), 0.0, 1.0)


func tick(delta: float) -> void:
	for i in _cooldowns.size():
		_cooldowns[i] = maxf(_cooldowns[i] - delta, 0.0)
	_buffer_timer = maxf(_buffer_timer - delta, 0.0)
	if _buffer_timer <= 0.0:
		_buffered = -1
	for i in mini(ACTIONS.size(), skills.size()):
		if InputMap.has_action(ACTIONS[i]) and Input.is_action_just_pressed(ACTIONS[i]):
			_buffered = i
			_buffer_timer = BUFFER_TIME


## Start the buffered skill if it is ready. Returns true if a skill started.
func try_start_buffered() -> bool:
	if _buffered < 0:
		return false
	return try_start(_buffered)


func try_start(index: int) -> bool:
	if index < 0 or index >= skills.size() or _cooldowns[index] > 0.0:
		return false
	var skill := skills[index]
	var p := _player
	if skill.kind == SkillData.Kind.RISING and not p.is_on_floor() and _rising_used:
		return false
	interrupt()
	_buffered = -1
	_buffer_timer = 0.0
	_cooldowns[index] = skill.cooldown
	current = skill
	_time = 0.0
	_opened = false
	_closed = false
	_released = false
	_vfx_started = false
	_vfx.clear()
	_fu_started = false
	_fu_opened = false
	_fu_closed = false
	_hidden = false
	_shown = false
	p.state = Player.State.SKILL
	p._attack_in_air = false
	if p._input_x() != 0.0:
		p._set_facing(p._input_x())
	p._sprite.play_skill(skill.anim, skill.anim_index)
	match skill.kind:
		SkillData.Kind.ISSEN:
			p.is_invincible = true
			p.velocity = Vector2.ZERO
		SkillData.Kind.BLINK:
			p.is_invincible = true
			p.velocity = Vector2.ZERO
			_pick_blink_target(skill)
			_cut.startup = maxf(skill.startup - skill.blink_arrive, 0.01)
			_cut.active = skill.active
			_cut.recovery = skill.recovery
		_:
			p.velocity.x *= 0.3
			if not p.is_on_floor():
				p.velocity.y = minf(p.velocity.y, 0.0)
	if skill.vfx_start != "":
		Vfx.spawn(skill.vfx_start, p.get_parent(), p.global_position, p.facing, 6)
	p._fx.on_skill_windup(skill)
	return true


## Called every physics frame while the player is in the SKILL state.
func process(delta: float) -> void:
	var s := current
	var p := _player
	if s == null:
		p.state = Player.State.NORMAL
		return
	_time += delta
	var active_end := s.startup + s.active
	var release_at := active_end + (s.sheath_delay if s.kind == SkillData.Kind.ISSEN else 0.0)
	var end_at := release_at + s.recovery
	var fu: AttackData = s.follow_up if s.kind == SkillData.Kind.CROSS else null
	if fu:
		end_at = active_end + fu.startup + fu.active + fu.recovery

	if s.kind == SkillData.Kind.BLINK:
		_process_blink(s)
	if not _vfx_started and _time >= s.startup - s.vfx_lead:
		_vfx_started = true
		_vfx = p._fx.on_skill_vfx(s)
	if not _opened and _time >= s.startup:
		_open(s)
	if _opened and not _closed and _time >= active_end:
		_closed = true
		p._hitbox.deactivate()
		if s.kind == SkillData.Kind.ISSEN:
			p.velocity = Vector2.ZERO
		if s.kind == SkillData.Kind.BLINK:
			p.is_invincible = false
	if s.kind == SkillData.Kind.ISSEN and _closed and not _released and _time >= release_at:
		_released = true
		var hits := p._hitbox.release_collected()
		p.is_invincible = false
		p._fx.on_issen_release(s, hits)
	if fu:
		_process_follow_up(s, fu, active_end)

	_move(s, delta)
	_show_sprite(s, fu, active_end, release_at)

	var can_cancel := _closed and (s.kind != SkillData.Kind.ISSEN or _released) and (fu == null or _fu_closed)
	if can_cancel and p._try_cancel_attack():
		if p.state != Player.State.SKILL:
			current = null   # cancelled into dash / jump; a new skill keeps its own `current`
		return
	if _time >= end_at:
		current = null
		p.is_invincible = false
		p._visual.visible = true
		p.state = Player.State.NORMAL


func on_landed() -> void:
	_rising_used = false


## Stop the running skill (hurt, death, respawn). Gathered 一闪 targets are dropped.
func interrupt() -> void:
	if current == null:
		return
	_player._hitbox.deactivate()
	_player._hitbox.discard_collected()
	if not _opened:
		# Cut short before the hit: don't leave a slash playing in the air.
		for fx in _vfx:
			if is_instance_valid(fx):
				fx.queue_free()
	_vfx.clear()
	if current.kind == SkillData.Kind.ISSEN or current.kind == SkillData.Kind.BLINK:
		_player.is_invincible = false
	_player._visual.visible = true
	current = null


func _open(s: SkillData) -> void:
	var p := _player
	_opened = true
	p._hitbox.activate(s, p.facing, s.kind == SkillData.Kind.ISSEN)
	p._fx.on_skill(s)
	match s.kind:
		SkillData.Kind.ISSEN:
			p.velocity = Vector2(p.facing * s.travel / maxf(s.active, 0.001), 0.0)
		SkillData.Kind.RISING:
			_rising_used = true
			p.velocity = Vector2(p.facing * 40.0, s.rise_speed)
			p._air_attacks_left = p.max_air_attacks   # follow up with an air slash
			p._squash(Vector2(0.8, 1.25))
		SkillData.Kind.SPIN:
			p._squash(Vector2(1.2, 0.85))
		SkillData.Kind.CROSS:
			if p.is_on_floor():
				p.velocity.x = p.facing * s.forward_step


func _move(s: SkillData, delta: float) -> void:
	var p := _player
	var swinging := _opened and not _closed
	if s.kind == SkillData.Kind.ISSEN and swinging:
		p.velocity.y = 0.0   # keep the dash velocity set in _open()
		return
	if s.kind == SkillData.Kind.ISSEN and not _released:
		p.velocity = Vector2.ZERO   # wind-up and the sheathing beat: stand still, even in the air
		return
	if s.kind == SkillData.Kind.BLINK and not _closed:
		p.velocity = Vector2.ZERO   # vanished, then planted for the cut, even in the air
		return
	if s.kind == SkillData.Kind.RISING and _opened:
		p.velocity.x = move_toward(p.velocity.x, p._input_x() * p.run_speed * 0.5, p.air_accel * delta)
		p._apply_gravity(delta, p.max_fall_speed)
		return
	if p.is_on_floor():
		p.velocity.x = move_toward(p.velocity.x, 0.0, p.ground_friction * 0.5 * delta)
	else:
		var hanging := s.hang and not _closed
		p.velocity.x = move_toward(p.velocity.x, p._input_x() * p.run_speed * 0.5, p.air_accel * delta)
		p._apply_gravity(delta, HANG_FALL_SPEED if hanging else p.max_fall_speed)


## 一闪 has a sheathing beat between the swing and the recovery; stretch the recovery frames
## over both so the sprite holds the follow-through pose while the cuts are pending.
func _sprite_time(s: SkillData, active_end: float, release_at: float) -> float:
	if _time < active_end or release_at <= active_end:
		return _time
	var span := (release_at - active_end) + s.recovery
	return active_end + (_time - active_end) * s.recovery / maxf(span, 0.001)


func _show_sprite(s: SkillData, fu: AttackData, active_end: float, release_at: float) -> void:
	var p := _player
	if fu and _fu_started:
		p._sprite.show_attack_time(_time - active_end, fu)
	elif s.kind == SkillData.Kind.BLINK:
		if _shown:
			p._sprite.show_attack_time(_time - s.blink_arrive, _cut)
	else:
		p._sprite.show_attack_time(_sprite_time(s, active_end, release_at), s)


## CROSS: right after the first cut, switch to the second row and run `fu` on the same hitbox.
func _process_follow_up(s: SkillData, fu: AttackData, active_end: float) -> void:
	var p := _player
	var t := _time - active_end
	if not _fu_started and _time >= active_end:
		_fu_started = true
		p._sprite.play_attack(s.anim2_index)
	if _fu_started and not _fu_opened and t >= fu.startup:
		_fu_opened = true
		p._hitbox.activate(fu, p.facing)   # a fresh hit list: the first target can be hit again
		if p.is_on_floor():
			p.velocity.x = p.facing * fu.forward_step
		p._squash(Vector2(0.85, 1.15))
	if _fu_opened and not _fu_closed and t >= fu.startup + fu.active:
		_fu_closed = true
		p._hitbox.deactivate()


## BLINK: hide the body, move it, then show it again for the cut.
func _process_blink(s: SkillData) -> void:
	var p := _player
	if not _hidden and _time >= s.blink_hide:
		_hidden = true
		p._visual.visible = false
		p.global_position = _blink_target
		p.velocity = Vector2.ZERO
		p._set_facing(_blink_face)
		if s.vfx_arrive != "":
			Vfx.spawn(s.vfx_arrive, p.get_parent(), p.global_position, p.facing, 6)
		Sfx.play("dash", -4.0, 0.05)
	if _hidden and not _shown and _time >= s.blink_arrive:
		_shown = true
		p._visual.visible = true
		p._squash(Vector2(1.2, 0.85))


## Nearest living enemy within reach, preferring the ones in front. Reappear just past it,
## facing back at it; with no enemy, blink `travel` px forward. Never ends up inside a wall.
func _pick_blink_target(s: SkillData) -> void:
	var p := _player
	var origin := p.global_position
	var best: Node2D = null
	var best_score := INF
	for node in p.get_tree().get_nodes_in_group(&"enemy"):
		var enemy := node as Node2D
		if enemy == null or (enemy.has_method("is_targetable") and not enemy.call("is_targetable")):
			continue
		var d := enemy.global_position - origin
		if absf(d.x) > s.blink_range or absf(d.y) > BLINK_VERTICAL:
			continue
		var in_front := d.x * p.facing >= 0.0
		var score := absf(d.x) + (0.0 if in_front else s.blink_range)
		if score < best_score:
			best_score = score
			best = enemy
	var dir := p.facing
	var target := origin + Vector2(p.facing * s.travel, 0.0)
	if best:
		dir = 1 if best.global_position.x >= origin.x else -1
		target = Vector2(best.global_position.x + dir * s.blink_behind, best.global_position.y)
	var query := PhysicsRayQueryParameters2D.create(origin + Vector2(0, -12), target + Vector2(0, -12), 1)
	query.exclude = [p.get_rid()]
	var hit := p.get_world_2d().direct_space_state.intersect_ray(query)
	if not hit.is_empty():
		target.x = (hit["position"] as Vector2).x - dir * 8.0
	_blink_target = target
	_blink_face = -dir if best else dir
