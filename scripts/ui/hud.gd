class_name Hud
extends CanvasLayer
## Pixel HUD (art from tools/gen_ui.py): portrait, hearts (HP_PER_HEART each, with
## half hearts), an energy bar showing dash readiness, skill cooldown slots (U / I / O)
## under it, and the coin counter.

const HEART_FULL := preload("res://assets/ui/heart_full.png")
const HEART_HALF := preload("res://assets/ui/heart_half.png")
const HEART_EMPTY := preload("res://assets/ui/heart_empty.png")
const DIGITS := preload("res://assets/ui/digits.png")
const DIGIT_SIZE := Vector2i(7, 9)
const HP_PER_HEART := 20
const COIN_DIGITS := 3
const SKILL_SLOT_POS := Vector2(36, 31)
const SKILL_SLOT_SIZE := Vector2(20, 5)
const SKILL_SLOT_GAP := 2.0
const SKILL_BG := Color(0.09, 0.07, 0.11, 0.9)
const SKILL_CHARGING := Color(0.42, 0.4, 0.48)
const SKILL_READY := Color(0.89, 0.36, 0.31)

@export var player: Player

var _digit_textures: Array[AtlasTexture] = []
var _skill_fills: Array[ColorRect] = []
var _skill_was_ready: Array[bool] = []
## Skill index shown by each slot (skills without a cooldown get no slot).
var _skill_slots: Array[int] = []

@onready var _hearts: HBoxContainer = $Hearts
@onready var _bar_fill: ColorRect = $Bar/Fill
@onready var _digits: HBoxContainer = $Coins/Digits
@onready var _settings_btn: TextureButton = $SettingsBtn
@onready var _bar_width := _bar_fill.size.x


func _ready() -> void:
	_build_digits()
	_build_skill_slots.call_deferred()   # after the player's _ready built its skills
	_settings_btn.pressed.connect(GameSettings.request_toggle_menu)
	player.health.changed.connect(_on_health_changed)
	player.coins_changed.connect(_on_coins_changed)
	_on_health_changed(player.health.hp, player.health.max_hp)
	_on_coins_changed(player.coins)


func _process(_delta: float) -> void:
	_bar_fill.size.x = roundf(_bar_width * player.get_dash_ready_ratio())
	for n in _skill_fills.size():
		var i := _skill_slots[n]
		var ratio := player.get_skill_ready_ratio(i)
		var fill := _skill_fills[n]
		var ready := ratio >= 1.0
		fill.size.x = roundf((SKILL_SLOT_SIZE.x - 2.0) * ratio)
		fill.color = SKILL_READY if ready else SKILL_CHARGING
		if ready and not _skill_was_ready[n]:
			_flash(fill)
		_skill_was_ready[n] = ready


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


func _build_skill_slots() -> void:
	for i in player.get_skill_count():
		if player.get_skill_cooldown(i) <= 0.0:
			continue   # no cooldown, nothing to show
		var bg := ColorRect.new()
		bg.mouse_filter = Control.MOUSE_FILTER_IGNORE
		bg.color = SKILL_BG
		bg.position = SKILL_SLOT_POS + Vector2(_skill_slots.size() * (SKILL_SLOT_SIZE.x + SKILL_SLOT_GAP), 0)
		bg.size = SKILL_SLOT_SIZE
		add_child(bg)
		var fill := ColorRect.new()
		fill.mouse_filter = Control.MOUSE_FILTER_IGNORE
		fill.position = Vector2.ONE
		fill.size = SKILL_SLOT_SIZE - Vector2(2, 2)
		fill.color = SKILL_READY
		bg.add_child(fill)
		_skill_fills.append(fill)
		_skill_was_ready.append(true)
		_skill_slots.append(i)


## Brief white blink when a skill comes off cooldown.
func _flash(fill: ColorRect) -> void:
	fill.modulate = Color(2.0, 2.0, 2.0)
	var tw := create_tween()
	tw.tween_property(fill, "modulate", Color.WHITE, 0.25)
