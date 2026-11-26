class_name Hitbox
extends Area2D
## Damage-dealing area. Turned on/off by its owner for each attack.
## Each attack hits a given Hurtbox at most once.

signal hit_landed(target: Hurtbox, attack: AttackData)

## Show the hitbox as a translucent red box while active (for tuning).
@export var debug_draw := false

var _attack: AttackData
var _direction := 1
var _active := false
var _already_hit: Array[Hurtbox] = []

@onready var _shape: CollisionShape2D = $CollisionShape2D
@onready var _debug_rect: ColorRect = $DebugRect


func _ready() -> void:
	monitoring = false
	_debug_rect.visible = false
	area_entered.connect(_on_area_entered)


func activate(attack: AttackData, direction: int) -> void:
	_attack = attack
	_direction = direction
	_already_hit.clear()

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


func _on_area_entered(area: Area2D) -> void:
	var hurtbox := area as Hurtbox
	if hurtbox == null or _attack == null or hurtbox.invulnerable or hurtbox in _already_hit:
		return
	_already_hit.append(hurtbox)
	var knockback := Vector2(_attack.knockback.x * _direction, _attack.knockback.y)
	hurtbox.take_hit(HitInfo.new(_attack.damage, knockback, _direction, _attack.hit_stop, _attack.heavy))
	hit_landed.emit(hurtbox, _attack)
