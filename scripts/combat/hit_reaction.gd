class_name HitReaction
extends Node
## Visual reaction to being hit, reusable on any character. Point `body` at the
## node that holds the character's visuals (its position/scale must rest at 0 / 1).
##   1. White flash (shader) — holds through hit stop, then fades.
##   2. Shudder — body vibrates in place for the hit stop duration (real time).
##   3. Recoil — body is shoved and squashed, then springs back elastically.

const FLASH_SHADER := preload("res://shaders/flash.gdshader")
const SHUDDER_STEP := 0.02

@export var body: Node2D
@export var flash_time := 0.12
@export var recoil_distance := 3.0
@export var spring_time := 0.4

var _material: ShaderMaterial
var _flash_tween: Tween
var _recoil_tween: Tween


func _ready() -> void:
	_material = ShaderMaterial.new()
	_material.shader = FLASH_SHADER
	body.material = _material
	for child in body.get_children():
		if child is CanvasItem:
			(child as CanvasItem).use_parent_material = true


## Palette swap for variants: shift the hue of pixels in `hue_range` (0..1, may wrap).
func set_recolor(hue_shift: float, saturation := 1.0, value := 1.0, hue_range := Vector2(0.92, 0.04)) -> void:
	_material.set_shader_parameter("recolor_hue_shift", hue_shift)
	_material.set_shader_parameter("recolor_saturation", saturation)
	_material.set_shader_parameter("recolor_value", value)
	_material.set_shader_parameter("recolor_hue_range", hue_range)


func react(hit: HitInfo) -> void:
	_flash()
	_recoil(hit)


func _flash() -> void:
	if _flash_tween:
		_flash_tween.kill()
	_material.set_shader_parameter("flash_amount", 1.0)
	# Normal (scaled) time: barely moves during hit stop, so the target stays white.
	_flash_tween = create_tween()
	_flash_tween.tween_property(_material, "shader_parameter/flash_amount", 0.0, flash_time)


func _recoil(hit: HitInfo) -> void:
	if _recoil_tween:
		_recoil_tween.kill()
	var strength := 2.0 if hit.heavy else 1.0
	var push := Vector2(hit.direction * recoil_distance * strength, 0.0)
	body.position = push
	body.scale = Vector2(0.7, 1.25) if hit.heavy else Vector2(0.82, 1.12)

	_recoil_tween = create_tween().set_ignore_time_scale(true)
	var steps := int(hit.hit_stop / SHUDDER_STEP)
	for i in steps:
		var jitter := Vector2(1.0 if i % 2 == 0 else -1.0, 0.0) * strength
		_recoil_tween.tween_property(body, "position", push + jitter, SHUDDER_STEP)
	_recoil_tween.tween_property(body, "position", Vector2.ZERO, spring_time) \
		.set_trans(Tween.TRANS_ELASTIC).set_ease(Tween.EASE_OUT)
	_recoil_tween.parallel().tween_property(body, "scale", Vector2.ONE, spring_time) \
		.set_trans(Tween.TRANS_ELASTIC).set_ease(Tween.EASE_OUT)
