class_name DamageNumber
extends Label
## Floating number that rises and fades. Use DamageNumber.spawn(parent, pos, amount).

const RISE := 16.0
const DURATION := 0.5
const FONT_SIZE := 10


static func spawn(parent: Node, at: Vector2, amount: int) -> void:
	var label := DamageNumber.new()
	label.text = str(amount)
	label.z_index = 10
	label.add_theme_font_size_override("font_size", FONT_SIZE)
	label.add_theme_color_override("font_outline_color", Color.BLACK)
	label.add_theme_constant_override("outline_size", 3)
	parent.add_child(label)
	label.global_position = at + Vector2(randf_range(-6.0, 2.0), -FONT_SIZE)
	label._animate()


func _animate() -> void:
	var tween := create_tween().set_parallel()
	tween.tween_property(self, "position:y", position.y - RISE, DURATION) \
		.set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_OUT)
	tween.tween_property(self, "modulate:a", 0.0, DURATION * 0.5).set_delay(DURATION * 0.5)
	tween.chain().tween_callback(queue_free)
