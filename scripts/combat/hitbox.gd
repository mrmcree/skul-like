class_name Hitbox
extends Area2D
## Damage-dealing area. Turned on/off by its owner for each attack.
## Each attack hits a given Hurtbox at most once.
## Collect mode (used by 一闪): targets touched are only remembered, and every one of them is
## hit at once later by release_collected().

signal hit_landed(target: Hurtbox, attack: AttackData)

## Show the hitbox as a translucent red box while active (for tuning).
@export var debug_draw := false

var _attack: AttackData
var _direction := 1
var _active := false
var _collect := false
var _already_hit: Array[Hurtbox] = []
var _collected: Array[Hurtbox] = []

@onready var _shape: CollisionShape2D = $CollisionShape2D
@onready var _debug_rect: ColorRect = $DebugRect


func _ready() -> void:
	monitoring = false
	_debug_rect.visible = false
	area_entered.connect(_on_area_entered)


func activate(attack: AttackData, direction: int, collect := false) -> void:
	_attack = attack
	_direction = direction
	_collect = collect
	_already_hit.clear()
	_collected.clear()

	var center := Vector2(attack.hitbox_offset.x * direction, attack.hitbox_offset.y)
	(_shape.shape as RectangleShape2D).size = attack.hitbox_size
	_shape.position = center
	_debug_rect.size = attack.hitbox_size
	_debug_rect.position = center - attack.hitbox_size / 2.0
	_debug_rect.visible = debug_draw
	_active = true
	set_deferred("monitoring", true)


func deactivate() -> void:
	if not _active:
		return
	_active = false
	_debug_rect.visible = false
	set_deferred("monitoring", false)


## Hit everything gathered in collect mode. Returns how many targets were hit.
func release_collected() -> int:
	var count := 0
	for hurtbox in _collected:
		if is_instance_valid(hurtbox) and not hurtbox.invulnerable:
			_hit(hurtbox)
			count += 1
	_collected.clear()
	return count


## Forget gathered targets without hitting them (the attack was interrupted).
func discard_collected() -> void:
	_collected.clear()


func _on_area_entered(area: Area2D) -> void:
	var hurtbox := area as Hurtbox
	if hurtbox == null or _attack == null or hurtbox.invulnerable or hurtbox in _already_hit:
		return
	_already_hit.append(hurtbox)
	if _collect:
		_collected.append(hurtbox)
	else:
		_hit(hurtbox)


func _hit(hurtbox: Hurtbox) -> void:
	var direction := _direction
	if _attack.radial:
		direction = 1 if hurtbox.global_position.x >= global_position.x else -1
	var knockback := Vector2(_attack.knockback.x * direction, _attack.knockback.y)
	var hit := HitInfo.new(_attack.damage, knockback, direction, _attack.hit_stop, _attack.heavy)
	hit.source = owner if owner else get_parent()
	hurtbox.take_hit(hit)
	hit_landed.emit(hurtbox, _attack)
