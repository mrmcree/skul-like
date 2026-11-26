class_name ImpactBurst
extends CPUParticles2D
## One-shot spray of pixel sparks flying away from a hit, then frees itself.
## ImpactBurst.spawn(world, position, facing, heavy)

static var _gradient: Gradient


static func spawn(parent: Node, at: Vector2, dir: int, heavy: bool) -> void:
	var burst := ImpactBurst.new()
	burst.amount = 16 if heavy else 8
	parent.add_child(burst)
	burst.global_position = at.round()
	burst._configure(dir, heavy)


func _configure(dir: int, heavy: bool) -> void:
	z_index = 7
	one_shot = true
	explosiveness = 1.0
	lifetime = 0.45 if heavy else 0.3
	direction = Vector2(dir, -0.4)
	spread = 40.0 if heavy else 30.0
	gravity = Vector2(0, 520)
	initial_velocity_min = 90.0
	initial_velocity_max = 260.0 if heavy else 180.0
	damping_min = 120.0
	damping_max = 240.0
	scale_amount_min = 1.0
	scale_amount_max = 3.0 if heavy else 2.0
	color_ramp = _get_gradient()
	finished.connect(queue_free)
	emitting = true


## White-hot -> orange -> fading red, shared by all bursts.
static func _get_gradient() -> Gradient:
	if _gradient == null:
		_gradient = Gradient.new()
		_gradient.offsets = PackedFloat32Array([0.0, 0.35, 1.0])
		_gradient.colors = PackedColorArray([
			Color(1, 1, 0.95, 1), Color(1, 0.72, 0.3, 1), Color(0.9, 0.3, 0.2, 0),
		])
	return _gradient
