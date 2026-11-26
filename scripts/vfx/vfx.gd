class_name Vfx
extends AnimatedSprite2D
## Pixel-art sprite-sheet effect. One-shot effects play once and free themselves;
## looping effects (props such as braziers) play forever from a random frame.
##
## Spawn from code:   Vfx.spawn("hit_spark", get_parent(), global_position, facing)
## Or place a node in a scene, attach this script and set `effect`.
## Effects are described in VfxCatalog and drawn facing right; `facing` = -1 mirrors them.

## Catalog key of the effect to play (see VfxCatalog.EFFECTS).
@export var effect := ""
## 1 = as exported (facing right), -1 = mirrored.
@export var facing := 1

## Built SpriteFrames per effect name, shared by every instance.
static var _frames_cache: Dictionary = {}


## Create an effect as a child of `parent` with its pivot at world position `at`.
## Returns null (and logs an error) if the effect is unknown or the parent is missing.
static func spawn(effect_name: String, parent: Node, at: Vector2, direction := 1, z := 1) -> Vfx:
	if parent == null:
		push_error("Vfx.spawn: no parent for '%s'" % effect_name)
		return null
	if VfxCatalog.info(effect_name).is_empty():
		return null   # sheet not exported yet; VfxCatalog already warned once
	var fx := Vfx.new()
	fx.effect = effect_name
	fx.facing = direction
	fx.z_index = z
	parent.add_child(fx)
	fx.global_position = at.round()
	return fx


func _ready() -> void:
	var info: Dictionary = VfxCatalog.info(effect)
	if info.is_empty():
		push_error("Vfx: unknown effect '%s'" % effect)
		queue_free()
		return
	sprite_frames = _get_frames(effect, info)
	centered = false
	offset = -(info["pivot"] as Vector2)
	var inv := 1.0 / float(info.get("density", 1.0))
	scale = Vector2(inv if facing >= 0 else -inv, inv)
	animation = &"default"
	if info["loop"]:
		frame = randi() % int(info["frames"])
	else:
		animation_finished.connect(queue_free)
	play()


## Slice the sheet into one animation, cached per effect name.
static func _get_frames(effect_name: String, info: Dictionary) -> SpriteFrames:
	if _frames_cache.has(effect_name):
		return _frames_cache[effect_name]
	var sheet := load(VfxCatalog.SHEET_DIR + effect_name + ".png") as Texture2D
	var size: Vector2i = info["frame_size"]
	var columns := int(info["columns"])
	var frames := SpriteFrames.new()
	frames.set_animation_speed(&"default", info["fps"])
	frames.set_animation_loop(&"default", info["loop"])
	for i in int(info["frames"]):
		var atlas := AtlasTexture.new()
		atlas.atlas = sheet
		var col := i % columns
		var row := floori(float(i) / columns)
		atlas.region = Rect2(Vector2(col * size.x, row * size.y), Vector2(size))
		frames.add_frame(&"default", atlas)
	_frames_cache[effect_name] = frames
	return frames
