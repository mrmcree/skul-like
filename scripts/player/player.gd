class_name Player
extends CharacterBody2D
## Greybox player: run, jump (coyote time + buffer + variable height), double jump,
## dash with i-frames, drop through one-way platforms, 3-hit combo.
## Every tuning value is exported: select the Player node and tweak it in the Inspector.

signal coins_changed(coins: int)

enum State { NORMAL, DASH, ATTACK, HURT, DEAD }

const ONE_WAY_LAYER := 6
const DROP_THROUGH_TIME := 0.25
const DEFAULT_COMBO_PATHS: Array[String] = [
	"res://data/attacks/basic_1.tres",
	"res://data/attacks/basic_2.tres",
	"res://data/attacks/basic_3.tres",
]

@export_group("Run")
@export var run_speed := 110.0
@export var ground_accel := 1400.0
@export var ground_friction := 1600.0
@export var air_accel := 900.0

@export_group("Jump")
@export var jump_velocity := -270.0
@export var gravity := 820.0
@export var fall_gravity_multiplier := 1.6
@export var max_fall_speed := 320.0
## Releasing jump early multiplies upward speed by this (short hop).
@export var jump_cut_multiplier := 0.45
@export var max_air_jumps := 1
@export var coyote_time := 0.1
@export var jump_buffer_time := 0.12

@export_group("Dash")
@export var dash_speed := 280.0
@export var dash_duration := 0.14
@export var dash_cooldown := 0.35
@export var max_air_dashes := 1

@export_group("Attack")
## Leave empty to use data/attacks/basic_1..3.tres.
@export var combo: Array[AttackData] = []
@export var attack_buffer_time := 0.15
## Max fall speed while attacking in the air (Skul-style hang time).
@export var air_attack_fall_speed := 30.0

@export_group("Damage")
## Seconds without control after being hit.
@export var hurt_time := 0.3
@export var respawn_delay := 1.5

var state := State.NORMAL
var facing := 1
## True during dash: enemy attacks pass through.
var is_invincible := false
var coins := 0
var _hurt_timer := 0.0
var _spawn_position := Vector2.ZERO

var _coyote_timer := 0.0
var _jump_buffer_timer := 0.0
var _attack_buffer_timer := 0.0
var _dash_timer := 0.0
var _dash_cooldown_timer := 0.0
var _drop_timer := 0.0
var _air_jumps_left := 0
var _air_dashes_left := 0
var _combo_index := 0
var _attack_time := 0.0
var _hitbox_opened := false
## Starts true so spawning on the ground doesn't play a landing effect.
var _was_on_floor := true
var _squash_tween: Tween
var _fx := PlayerFeedback.new(self)

@onready var _visual: Node2D = $Visual
@onready var _body: Node2D = $Visual/Body
@onready var _hitbox: Hitbox = $Hitbox
@onready var _sprite: PlayerSprite = $Visual/Body/Sprite
@onready var _hurtbox: Hurtbox = $Hurtbox
@onready var _hit_reaction: HitReaction = $HitReaction
@onready var health: PlayerHealth = $Health


func _ready() -> void:
	add_to_group("player")
	_spawn_position = global_position
	if combo.is_empty():
		for path in DEFAULT_COMBO_PATHS:
			combo.append(load(path) as AttackData)
	_hitbox.hit_landed.connect(_on_hit_landed)
	_hurtbox.hurt.connect(_on_hurt)
	health.died.connect(_die)


func _physics_process(delta: float) -> void:
	_tick_timers(delta)
	_buffer_inputs()
	match state:
		State.NORMAL:
			_process_normal(delta)
		State.DASH:
			_process_dash()
		State.ATTACK:
			_process_attack(delta)
		State.HURT, State.DEAD:
			_process_stunned(delta)
	move_and_slide()
	_after_move()
	_hurtbox.invulnerable = state == State.DEAD or is_invincible or health.is_invincible()
	if state == State.NORMAL or state == State.DASH:
		_sprite.update_locomotion(is_on_floor(), velocity, state == State.DASH)


# --- Timers & input -------------------------------------------------------

func _tick_timers(delta: float) -> void:
	_coyote_timer = maxf(_coyote_timer - delta, 0.0)
	_jump_buffer_timer = maxf(_jump_buffer_timer - delta, 0.0)
	_attack_buffer_timer = maxf(_attack_buffer_timer - delta, 0.0)
	_dash_timer = maxf(_dash_timer - delta, 0.0)
	_dash_cooldown_timer = maxf(_dash_cooldown_timer - delta, 0.0)
	if _drop_timer > 0.0:
		_drop_timer -= delta
		if _drop_timer <= 0.0:
			set_collision_mask_value(ONE_WAY_LAYER, true)


## Remember presses for a short time so slightly-early inputs still work.
func _buffer_inputs() -> void:
	if Input.is_action_just_pressed("jump"):
		_jump_buffer_timer = jump_buffer_time
	if Input.is_action_just_pressed("attack"):
		_attack_buffer_timer = attack_buffer_time


## 1.0 when dash is ready, rising from 0 while it recharges (drives the HUD bar).
func get_dash_ready_ratio() -> float:
	return 1.0 - clampf(_dash_cooldown_timer / maxf(dash_cooldown, 0.001), 0.0, 1.0)


func add_coins(amount: int) -> void:
	coins += amount
	coins_changed.emit(coins)


func _input_x() -> float:
	return Input.get_axis("move_left", "move_right")


# --- NORMAL state ---------------------------------------------------------

func _process_normal(delta: float) -> void:
	var input_x := _input_x()
	if input_x != 0.0:
		_set_facing(input_x)
	_apply_run(input_x, delta)
	_apply_gravity(delta, max_fall_speed)

	if _try_drop_through():
		return
	_try_jump()
	if Input.is_action_just_released("jump") and velocity.y < 0.0:
		velocity.y *= jump_cut_multiplier

	if Input.is_action_just_pressed("dash") and _try_start_dash():
		return
	if _attack_buffer_timer > 0.0:
		_start_attack(0)


func _apply_run(input_x: float, delta: float) -> void:
	var accel := ground_accel if is_on_floor() else air_accel
	if input_x == 0.0 and is_on_floor():
		accel = ground_friction
	velocity.x = move_toward(velocity.x, input_x * run_speed, accel * delta)


func _apply_gravity(delta: float, fall_limit: float) -> void:
	if is_on_floor():
		return
	var multiplier := fall_gravity_multiplier if velocity.y > 0.0 else 1.0
	velocity.y = minf(velocity.y + gravity * multiplier * delta, fall_limit)


func _try_jump() -> bool:
	if _jump_buffer_timer <= 0.0:
		return false
	if is_on_floor() or _coyote_timer > 0.0:
		_do_jump()
		return true
	# Air jump only on a fresh press, so a buffered press before landing
	# becomes a normal ground jump instead of wasting the double jump.
	if Input.is_action_just_pressed("jump") and _air_jumps_left > 0:
		_air_jumps_left -= 1
		_do_jump()
		return true
	return false


func _do_jump() -> void:
	velocity.y = jump_velocity
	_jump_buffer_timer = 0.0
	_coyote_timer = 0.0
	_squash(Vector2(0.75, 1.25))
	_fx.on_jump(is_on_floor())


func _try_drop_through() -> bool:
	if _jump_buffer_timer <= 0.0 or not Input.is_action_pressed("move_down"):
		return false
	if not is_on_floor() or not _is_on_one_way_platform():
		return false
	_jump_buffer_timer = 0.0
	_drop_timer = DROP_THROUGH_TIME
	set_collision_mask_value(ONE_WAY_LAYER, false)
	position.y += 1.0
	return true


func _is_on_one_way_platform() -> bool:
	for i in get_slide_collision_count():
		var collider := get_slide_collision(i).get_collider()
		if collider is CollisionObject2D and collider.get_collision_layer_value(ONE_WAY_LAYER):
			return true
	return false


# --- DASH state -----------------------------------------------------------

func _try_start_dash() -> bool:
	if _dash_cooldown_timer > 0.0:
		return false
	if not is_on_floor():
		if _air_dashes_left <= 0:
			return false
		_air_dashes_left -= 1
	if _input_x() != 0.0:
		_set_facing(_input_x())
	_hitbox.deactivate()
	state = State.DASH
	is_invincible = true
	_dash_timer = dash_duration
	_dash_cooldown_timer = dash_cooldown
	velocity = Vector2(facing * dash_speed, 0.0)
	_squash(Vector2(1.3, 0.75))
	_fx.on_dash(is_on_floor())
	return true


func _process_dash() -> void:
	velocity.y = 0.0
	if _dash_timer <= 0.0:
		state = State.NORMAL
		is_invincible = false
		velocity.x = facing * run_speed


# --- ATTACK state ---------------------------------------------------------

func _start_attack(index: int) -> void:
	if combo.is_empty():
		return
	_combo_index = index % combo.size()
	_attack_time = 0.0
	_hitbox_opened = false
	_attack_buffer_timer = 0.0
	state = State.ATTACK
	if _input_x() != 0.0:
		_set_facing(_input_x())
	_sprite.play_attack(_combo_index)
	if is_on_floor():
		velocity.x = facing * combo[_combo_index].forward_step
	else:
		velocity.y = minf(velocity.y, 0.0)


func _process_attack(delta: float) -> void:
	var attack := combo[_combo_index]
	_attack_time += delta
	_move_during_attack(delta)
	_sprite.show_attack_time(_attack_time, attack)

	var active_end := attack.startup + attack.active
	if not _hitbox_opened and _attack_time >= attack.startup:
		_hitbox_opened = true
		_hitbox.activate(attack, facing)
		_fx.on_swing(attack, _combo_index)
	if _attack_time < active_end:
		return

	# Recovery phase: can chain the next hit or cancel into jump/dash.
	_hitbox.deactivate()
	if _try_cancel_attack():
		return
	if _attack_buffer_timer > 0.0 and _combo_index < combo.size() - 1:
		_start_attack(_combo_index + 1)
	elif _attack_time >= active_end + attack.recovery:
		state = State.NORMAL


func _move_during_attack(delta: float) -> void:
	if is_on_floor():
		velocity.x = move_toward(velocity.x, 0.0, ground_friction * 0.5 * delta)
	else:
		velocity.x = move_toward(velocity.x, _input_x() * run_speed * 0.5, air_accel * delta)
		velocity.y = minf(velocity.y + gravity * delta, air_attack_fall_speed)


func _try_cancel_attack() -> bool:
	if Input.is_action_just_pressed("dash") and _try_start_dash():
		return true
	if _jump_buffer_timer > 0.0 and (is_on_floor() or _coyote_timer > 0.0):
		state = State.NORMAL
		_do_jump()
		return true
	return false


func _on_hit_landed(target: Hurtbox, attack: AttackData) -> void:
	_fx.on_hit(target, attack)


# --- HURT / DEAD states ---------------------------------------------------

func _on_hurt(hit: HitInfo) -> void:
	if _hurtbox.invulnerable:
		return
	_hitbox.deactivate()
	is_invincible = false
	velocity = hit.knockback
	_hit_reaction.react(hit)
	_fx.on_hurt(hit)
	health.take(hit.damage)  # may call _die()
	if state != State.DEAD:
		state = State.HURT
		_hurt_timer = hurt_time
		_sprite.play_pose(&"hurt")


## No control: just gravity and friction until the timer runs out.
func _process_stunned(delta: float) -> void:
	_apply_gravity(delta, max_fall_speed)
	if is_on_floor():
		velocity.x = move_toward(velocity.x, 0.0, ground_friction * 0.5 * delta)
	if state == State.HURT:
		_hurt_timer -= delta
		if _hurt_timer <= 0.0:
			state = State.NORMAL


func _die() -> void:
	state = State.DEAD
	_sprite.play_pose(&"death")
	_fx.on_death()
	await get_tree().create_timer(respawn_delay).timeout
	_respawn()


func _respawn() -> void:
	global_position = _spawn_position
	velocity = Vector2.ZERO
	state = State.NORMAL
	health.restore()
	_fx.on_respawn()


# --- Helpers --------------------------------------------------------------

func _after_move() -> void:
	var on_floor := is_on_floor()
	if on_floor:
		_coyote_timer = coyote_time
		_air_jumps_left = max_air_jumps
		_air_dashes_left = max_air_dashes
		if not _was_on_floor:
			_squash(Vector2(1.25, 0.8))
			_fx.on_land()
	_was_on_floor = on_floor


func _set_facing(direction: float) -> void:
	facing = 1 if direction > 0.0 else -1
	_visual.scale.x = facing


## Stretch/squash the body sprite, then spring back. Pivot is at the feet.
func _squash(amount: Vector2) -> void:
	if _squash_tween:
		_squash_tween.kill()
	_body.scale = amount
	_squash_tween = create_tween()
	_squash_tween.tween_property(_body, "scale", Vector2.ONE, 0.12) \
		.set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
