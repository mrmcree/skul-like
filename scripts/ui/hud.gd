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
@onready var _settings_btn: Button = $SettingsBtn
@onready var _bar_width := _bar_fill.size.x


func _ready() -> void:
	_build_digits()
	_style_settings_button()
	player.health.changed.connect(_on_health_changed)
	player.coins_changed.connect(_on_coins_changed)
	_on_health_changed(player.health.hp, player.health.max_hp)
	_on_coins_changed(player.coins)


func _style_settings_button() -> void:
	var font := SystemFont.new()
	font.font_names = PackedStringArray(["Microsoft YaHei", "SimHei", "PingFang SC", "Noto Sans CJK SC", "sans-serif"])
	_settings_btn.add_theme_font_override("font", font)
	_settings_btn.add_theme_font_size_override("font_size", 7)
	_settings_btn.add_theme_color_override("font_color", Color(0.95, 0.91, 0.85, 1.0))
	_settings_btn.add_theme_color_override("font_hover_color", Color(0.95, 0.82, 0.48, 1.0))
	var norm := StyleBoxFlat.new()
	norm.bg_color = Color(0.13, 0.12, 0.16, 0.86)
	norm.border_color = Color(0.91, 0.85, 0.67, 0.9)
	norm.set_border_width_all(1)
	norm.set_corner_radius_all(2)
	var hover := norm.duplicate() as StyleBoxFlat
	hover.bg_color = Color(0.24, 0.21, 0.30, 0.95)
	hover.border_color = Color(0.95, 0.82, 0.48, 1.0)
	_settings_btn.add_theme_stylebox_override("normal", norm)
	_settings_btn.add_theme_stylebox_override("hover", hover)
	_settings_btn.add_theme_stylebox_override("pressed", hover)
	_settings_btn.pressed.connect(GameSettings.request_toggle_menu)


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
