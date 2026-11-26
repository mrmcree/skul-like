class_name Hud
extends CanvasLayer
## Pixel HUD (art from tools/gen_ui.py): portrait, hearts (HP_PER_HEART each, with
## half hearts), an energy bar showing dash readiness, and the coin counter.

const HEART_FULL := preload("res://assets/ui/heart_full.png")
const HEART_HALF := preload("res://assets/ui/heart_half.png")
const HEART_EMPTY := preload("res://assets/ui/heart_empty.png")
const DIGITS := preload("res://assets/ui/digits.png")
const DIGIT_SIZE := Vector2i(7, 9)
const HP_PER_HEART := 20
const COIN_DIGITS := 3

@export var player: Player

var _digit_textures: Array[AtlasTexture] = []

@onready var _hearts: HBoxContainer = $Hearts
@onready var _bar_fill: ColorRect = $Bar/Fill
@onready var _digits: HBoxContainer = $Coins/Digits
@onready var _bar_width := _bar_fill.size.x


func _ready() -> void:
	_build_digits()
	player.health.changed.connect(_on_health_changed)
	player.coins_changed.connect(_on_coins_changed)
	_on_health_changed(player.health.hp, player.health.max_hp)
	_on_coins_changed(player.coins)


func _process(_delta: float) -> void:
	_bar_fill.size.x = roundf(_bar_width * player.get_dash_ready_ratio())


func _on_health_changed(hp: int, max_hp: int) -> void:
	var count := ceili(float(max_hp) / HP_PER_HEART)
	while _hearts.get_child_count() < count:
		var heart := TextureRect.new()
		heart.mouse_filter = Control.MOUSE_FILTER_IGNORE
		_hearts.add_child(heart)
	for i in _hearts.get_child_count():
		var heart := _hearts.get_child(i) as TextureRect
		heart.visible = i < count
		var heart_hp := hp - i * HP_PER_HEART
		if heart_hp >= HP_PER_HEART:
			heart.texture = HEART_FULL
		elif heart_hp > 0:
			heart.texture = HEART_HALF
		else:
			heart.texture = HEART_EMPTY


func _on_coins_changed(coins: int) -> void:
	var text := str(clampi(coins, 0, 999)).pad_zeros(COIN_DIGITS)
	for i in COIN_DIGITS:
		(_digits.get_child(i) as TextureRect).texture = _digit_textures[int(text[i])]


func _build_digits() -> void:
	for d in 10:
		var atlas := AtlasTexture.new()
		atlas.atlas = DIGITS
		atlas.region = Rect2(Vector2(d * DIGIT_SIZE.x, 0), Vector2(DIGIT_SIZE))
		_digit_textures.append(atlas)
	for i in COIN_DIGITS:
		var slot := TextureRect.new()
		slot.mouse_filter = Control.MOUSE_FILTER_IGNORE
		_digits.add_child(slot)
