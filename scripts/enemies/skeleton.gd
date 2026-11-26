class_name Skeleton
extends CharacterBody2D
## Skeleton ashigaru. Patrols around its spawn point, chases the player when it
## sees them, telegraphs (red glow + crouch) and lunges with its spear.
## Hits stagger it (interrupting an attack). At 0 HP it collapses, fades, respawns.
## Attack timing lives in `attack_data` (startup = wind-up, active = spear out,
## recovery = pulling back). Variants (e.g. scenes/enemies/skeleton_elite.tscn)
## override the exports: stats, attack, super armor and armour colour.

enum State { PATROL, IDLE, CHASE, ATTACK, HURT, DEAD }

const GROUND_MASK := 1 | 32
const TELEGRAPH_COLOR := Color(1.8, 0.7, 0.7)
## Attack frames in the "attack" row: wind-up, spear out, pull back.
const WINDUP_FRAMES: Array[int] = [0, 2]
const ACTIVE_FRAMES: Array[int] = [3, 4]
const RECOVERY_FRAMES: Array[int] = [5]

@export var max_hp := 60
@export_group("Movement")
@export var patrol_speed := 28.0
@export var chase_speed := 55.0
@export var acceleration := 600.0
@export var patrol_range := 50.0
@export var patrol_pause := 1.0
@export var gravity := 820.0
@export var max_fall_speed := 320.0
@export var ground_friction := 900.0
@export_group("Senses")
@export var detect_range := 110.0
@export var lose_range := 170.0
@export var vertical_tolerance := 40.0
## Starts an attack when the player is this close horizontally.
@export var attack_range := 34.0
@export var attack_cooldown := 0.9
@export var attack_data: AttackData = preload("res://data/attacks/skeleton_thrust.tres")
@export_group("Reactions")
@export var stagger_time := 0.3
## Light (non-heavy) hits don't interrupt this enemy's attack — only finishers do.
@export var super_armor := false
@export var respawn_delay := 3.0
@export var bounce_factor := 0.45
@export var min_bounce_speed := 120.0
@export_group("Look")
## Palette swap of the red armour (0 = original red, 0.62 = blue, 0.12 = gold).
@export_range(0.0, 1.0) var armor_hue_shift := 0.0
@export var armor_saturation := 1.0
@export var armor_value := 1.0

var hp := 0
var state := State.PATROL
var facing := -1
var _state_time := 0.0
var _cooldown := 0.0
var _hitbox_opened := false
var _spawn_position := Vector2.ZERO
var _telegraph_tween: Tween

@onready var _sprite: SkeletonSprite = $Body/Sprite
@onready var _hitbox: Hitbox = $Hitbox
@onready var _hurtbox: Hurtbox = $Hurtbox
@onready var _hit_reaction: HitReaction = $HitReaction
@onready var _hp_bar: Node2D = $HpBar
@onready var _hp_fill: ColorRect = $HpBar/Fill
@onready var _hp_bar_width := _hp_fill.size.x


func _ready() -> void:
	hp = max_hp
	_spawn_position = global_position
	_face(facing)
	_hit_reaction.set_recolor(armor_hue_shift, armor_saturation, armor_value)
	_hurtbox.hurt.connect(_on_hurt)
	_hitbox.hit_landed.connect(_on_attack_landed)
	_sprite.action_finished.connect(_on_sprite_action_finished)


func _physics_process(delta: float) -> void:
	_state_time += delta
	_cooldown = maxf(_cooldown - delta, 0.0)
	match state:
		State.PATROL:
			_process_patrol(delta)
		State.IDLE:
			_process_idle(delta)
		State.CHASE:
			_process_chase(delta)
		State.ATTACK:
			_process_attack(delta)
		State.HURT:
			if _state_time >= stagger_time:
				_enter(State.CHASE)
	_move(delta)


# --- States -----------------------------------------------------------------

func _enter(new_state: State) -> void:
	if state == State.ATTACK:
		_hitbox.deactivate()
		_end_telegraph()
	state = new_state
	_state_time = 0.0
	match new_state:
		State.PATROL, State.IDLE, State.CHASE:
			_sprite.play(&"walk" if new_state == State.PATROL else &"idle")
		State.ATTACK:
			_start_attack()
		State.HURT:
			_sprite.play_once(&"hit")
		State.DEAD:
			_sprite.play_once(&"death")


func _process_patrol(delta: float) -> void:
	if _sees_player():
		_enter(State.CHASE)
		return
	var offset := global_position.x - _spawn_position.x
	var too_far := offset * facing > patrol_range
	if too_far or is_on_wall() or _ledge_ahead():
		_enter(State.IDLE)
		return
	_run(facing * patrol_speed, delta)


func _process_idle(delta: float) -> void:
	_run(0.0, delta)
	if _sees_player():
		_enter(State.CHASE)
	elif _state_time >= patrol_pause:
		_face(-facing)
		_enter(State.PATROL)


func _process_chase(delta: float) -> void:
	var player := _player()
	if player == null or _distance_to(player).x > lose_range:
		_enter(State.IDLE)
		return
	var to_player := player.global_position - global_position
	_face(1 if to_player.x > 0.0 else -1)
	var in_range := absf(to_player.x) <= attack_range and absf(to_player.y) <= vertical_tolerance
	if in_range and _cooldown <= 0.0:
		_enter(State.ATTACK)
		return
	var blocked := in_range or is_on_wall() or _ledge_ahead()
	_run(0.0 if blocked else facing * chase_speed, delta)
	_sprite.play(&"idle" if blocked else &"walk")


# --- Attack -----------------------------------------------------------------

func _start_attack() -> void:
	_hitbox_opened = false
	_sprite.play(&"attack")
	_sprite.pause()
	_sprite.frame = WINDUP_FRAMES[0]
	# Telegraph: glow red during the wind-up so the player can react (dash through!).
	_end_telegraph()
	_sprite.modulate = TELEGRAPH_COLOR
	_telegraph_tween = create_tween()
	_telegraph_tween.tween_property(_sprite, "modulate", Color.WHITE, attack_data.startup)


func _process_attack(delta: float) -> void:
	var t := _state_time
	var active_end := attack_data.startup + attack_data.active
	if t < attack_data.startup:
		_run(0.0, delta)
		_sprite.frame = _pick(WINDUP_FRAMES, t / attack_data.startup)
	elif t < active_end:
		if not _hitbox_opened:
			_hitbox_opened = true
			velocity.x = facing * attack_data.forward_step
			_hitbox.activate(attack_data, facing)
			Sfx.play("spear_thrust", -12.0, 0.10)
		_sprite.frame = _pick(ACTIVE_FRAMES, (t - attack_data.startup) / attack_data.active)
	elif t < active_end + attack_data.recovery:
		_hitbox.deactivate()
		_run(0.0, delta)
		_sprite.frame = _pick(RECOVERY_FRAMES, (t - active_end) / attack_data.recovery)
	else:
		_cooldown = attack_cooldown
		_enter(State.CHASE)


func _pick(frames: Array[int], progress: float) -> int:
	return frames[clampi(int(progress * frames.size()), 0, frames.size() - 1)]


func _end_telegraph() -> void:
	if _telegraph_tween:
		_telegraph_tween.kill()
	_sprite.modulate = Color.WHITE


## Hit stop / shake / sound come from the player's own hurt feedback; add a spark here.
func _on_attack_landed(target: Hurtbox, _attack: AttackData) -> void:
	var at := target.global_position + Vector2(-facing * 4.0, -14.0)
	Vfx.spawn("hit_spark", get_parent(), at, facing, 6)


# --- Taking damage ----------------------------------------------------------

func _on_hurt(hit: HitInfo) -> void:
	if state == State.DEAD:
		return
	hp = maxi(hp - hit.damage, 0)
	DamageNumber.spawn(get_parent(), global_position + Vector2(0, -36), hit.damage)
	_hit_reaction.react(hit)
	_hp_fill.size.x = _hp_bar_width * float(hp) / max_hp
	if hp == 0:
		velocity = hit.knockback
		_die()
		return
	# Super armor: light hits still hurt and flash, but the attack keeps going.
	if super_armor and state == State.ATTACK and not hit.heavy:
		return
	velocity = hit.knockback
	_face(-hit.direction)
	_enter(State.HURT)


func _die() -> void:
	_enter(State.DEAD)
	_hurtbox.set_deferred("monitorable", false)
	_hp_bar.visible = false
	Sfx.play("break", -2.0)
	var fade := create_tween()
	fade.tween_interval(respawn_delay * 0.5)
	fade.tween_property(_sprite, "modulate:a", 0.0, respawn_delay * 0.3)
	await get_tree().create_timer(respawn_delay).timeout
	_respawn()


func _respawn() -> void:
	global_position = _spawn_position
	velocity = Vector2.ZERO
	hp = max_hp
	_hp_fill.size.x = _hp_bar_width
	_hp_bar.visible = true
	_sprite.modulate = Color.WHITE
	_hurtbox.set_deferred("monitorable", true)
	Vfx.spawn("puff", get_parent(), global_position, 1, 2)
	_enter(State.PATROL)


func _on_sprite_action_finished(anim: StringName) -> void:
	if anim == &"hit" and state == State.HURT:
		_sprite.play(&"idle")


# --- Helpers ----------------------------------------------------------------

func _run(target_speed: float, delta: float) -> void:
	velocity.x = move_toward(velocity.x, target_speed, acceleration * delta)


func _move(delta: float) -> void:
	var airborne := not is_on_floor()
	if airborne:
		velocity.y = minf(velocity.y + gravity * delta, max_fall_speed)
	elif state == State.HURT or state == State.DEAD:
		velocity.x = move_toward(velocity.x, 0.0, ground_friction * delta)
	var fall_speed := velocity.y
	move_and_slide()
	if airborne and is_on_floor() and fall_speed >= min_bounce_speed:
		velocity.y = -fall_speed * bounce_factor
		Vfx.spawn("dust_land", get_parent(), global_position, 1, 0)
		Sfx.play("land", -2.0)
		GameFeel.shake(1.0, 0.08, Vector2.DOWN)


func _face(direction: int) -> void:
	facing = direction
	_sprite.face(direction)


func _player() -> Player:
	var player := get_tree().get_first_node_in_group("player") as Player
	if player == null or player.state == Player.State.DEAD:
		return null
	return player


func _distance_to(node: Node2D) -> Vector2:
	return (node.global_position - global_position).abs()


func _sees_player() -> bool:
	var player := _player()
	if player == null:
		return false
	var d := _distance_to(player)
	return d.x <= detect_range and d.y <= vertical_tolerance


## True when there is no ground just ahead of our feet (don't walk off edges).
func _ledge_ahead() -> bool:
	if not is_on_floor():
		return false
	var from := global_position + Vector2(facing * 10.0, -4.0)
	var query := PhysicsRayQueryParameters2D.create(from, from + Vector2(0, 14), GROUND_MASK)
	return get_world_2d().direct_space_state.intersect_ray(query).is_empty()
