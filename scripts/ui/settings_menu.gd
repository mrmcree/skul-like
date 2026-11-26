class_name SettingsMenu
extends CanvasLayer
## 16-bit Japanese shrine pixel-art pause & settings overlay (Esc or HUD gear).
## Runs during pause (PROCESS_MODE_ALWAYS) and persists via GameSettings.

const PIXEL_FONT := preload("res://assets/ui/pixel_font.ttf")
const TEX_PANEL := preload("res://assets/ui/panel_frame.png")
const TEX_BTN_NORM := preload("res://assets/ui/btn_normal.png")
const TEX_BTN_HOVER := preload("res://assets/ui/btn_hover.png")
const TEX_BTN_PRESS := preload("res://assets/ui/btn_pressed.png")
const TEX_TRACK := preload("res://assets/ui/slider_track.png")
const TEX_FILL := preload("res://assets/ui/slider_fill.png")
const TEX_FILL_HI := preload("res://assets/ui/slider_fill_hi.png")
const TEX_GRABBER := preload("res://assets/ui/slider_grabber.png")
const TEX_GRABBER_HI := preload("res://assets/ui/slider_grabber_hi.png")
const TEX_DIVIDER := preload("res://assets/ui/divider.png")
const TEX_GEM_ON := preload("res://assets/ui/gem_on.png")
const TEX_GEM_OFF := preload("res://assets/ui/gem_off.png")

const PREVIEW_COOLDOWN_MS := 180
const COLOR_INK := Color(0.08, 0.04, 0.06, 1.0)
const COLOR_GOLD := Color(1.0, 0.92, 0.66, 1.0)
const COLOR_TEXT := Color(0.95, 0.91, 0.88, 1.0)
const COLOR_MUTED := Color(0.75, 0.71, 0.78, 1.0)

var _root: Control
var _master_slider: HSlider
var _master_val: Label
var _sfx_slider: HSlider
var _sfx_val: Label
var _weapon_slider: HSlider
var _weapon_val: Label
var _shake_slider: HSlider
var _shake_val: Label
var _hit_stop_btn: Button
var _fullscreen_btn: Button

var _syncing := false
var _last_preview_ms := 0


func _ready() -> void:
	layer = 20
	process_mode = Node.PROCESS_MODE_ALWAYS
	_build_ui()
	_root.visible = false
	GameSettings.menu_toggle_requested.connect(toggle)
	GameSettings.changed.connect(_sync_controls)


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed and not event.echo and event.keycode == KEY_ESCAPE:
		toggle()
		get_viewport().set_input_as_handled()


func is_open() -> bool:
	return _root.visible


func open() -> void:
	_sync_controls()
	_root.visible = true
	get_tree().paused = true
	_master_slider.grab_focus()


func close() -> void:
	_root.visible = false
	get_tree().paused = false


func toggle() -> void:
	if is_open():
		close()
	else:
		open()


func _sync_controls() -> void:
	_syncing = true
	_master_slider.value = roundf(GameSettings.master_volume * 100.0)
	_sfx_slider.value = roundf(GameSettings.sfx_volume * 100.0)
	_weapon_slider.value = roundf(GameSettings.weapon_volume * 100.0)
	_shake_slider.value = roundf(GameSettings.shake_scale * 100.0)
	_master_val.text = "%d%%" % int(_master_slider.value)
	_sfx_val.text = "%d%%" % int(_sfx_slider.value)
	_weapon_val.text = "%d%%" % int(_weapon_slider.value)
	_shake_val.text = "%d%%" % int(_shake_slider.value)
	_hit_stop_btn.text = "开启" if GameSettings.hit_stop_enabled else "关闭"
	_hit_stop_btn.icon = TEX_GEM_ON if GameSettings.hit_stop_enabled else TEX_GEM_OFF
	_fullscreen_btn.text = "全屏" if GameSettings.fullscreen else "窗口"
	_fullscreen_btn.icon = TEX_GEM_ON if GameSettings.fullscreen else TEX_GEM_OFF
	_syncing = false


func _preview_sfx(sound: String, base_db: float) -> void:
	if _syncing:
		return
	var now := Time.get_ticks_msec()
	if now - _last_preview_ms < PREVIEW_COOLDOWN_MS:
		return
	_last_preview_ms = now
	Sfx.play(sound, base_db, 0.04)


func _make_box_tex(tex: Texture2D, mh: int, mv: int, pad_h: float, pad_top: float, pad_bot := -1.0) -> StyleBoxTexture:
	var sb := StyleBoxTexture.new()
	sb.texture = tex
	sb.texture_margin_left = mh
	sb.texture_margin_right = mh
	sb.texture_margin_top = mv
	sb.texture_margin_bottom = mv
	sb.axis_stretch_horizontal = StyleBoxTexture.AXIS_STRETCH_MODE_TILE
	sb.axis_stretch_vertical = StyleBoxTexture.AXIS_STRETCH_MODE_STRETCH
	sb.content_margin_left = pad_h
	sb.content_margin_right = pad_h
	sb.content_margin_top = pad_top
	sb.content_margin_bottom = pad_top if pad_bot < 0.0 else pad_bot
	return sb


func _build_theme() -> Theme:
	var theme := Theme.new()
	theme.default_font = PIXEL_FONT
	theme.default_font_size = 12

	theme.set_color("font_color", "Label", COLOR_TEXT)
	theme.set_color("font_outline_color", "Label", COLOR_INK)
	theme.set_constant("outline_size", "Label", 3)

	var btn_norm := _make_box_tex(TEX_BTN_NORM, 5, 5, 8.0, 2.0)
	var btn_hover := _make_box_tex(TEX_BTN_HOVER, 5, 5, 8.0, 2.0)
	var btn_press := _make_box_tex(TEX_BTN_PRESS, 5, 5, 8.0, 2.0)
	theme.set_stylebox("normal", "Button", btn_norm)
	theme.set_stylebox("hover", "Button", btn_hover)
	theme.set_stylebox("focus", "Button", btn_hover)
	theme.set_stylebox("pressed", "Button", btn_press)
	theme.set_color("font_color", "Button", COLOR_TEXT)
	theme.set_color("font_hover_color", "Button", COLOR_GOLD)
	theme.set_color("font_focus_color", "Button", COLOR_GOLD)
	theme.set_color("font_pressed_color", "Button", COLOR_TEXT)
	theme.set_color("font_outline_color", "Button", COLOR_INK)
	theme.set_constant("outline_size", "Button", 3)
	theme.set_constant("h_separation", "Button", 4)

	var track := _make_box_tex(TEX_TRACK, 4, 3, 2.0, 4.0, 5.0)
	var fill := _make_box_tex(TEX_FILL, 3, 3, 2.0, 4.0, 5.0)
	var fill_hi := _make_box_tex(TEX_FILL_HI, 3, 3, 2.0, 4.0, 5.0)
	theme.set_stylebox("slider", "HSlider", track)
	theme.set_stylebox("grabber_area", "HSlider", fill)
	theme.set_stylebox("grabber_area_highlight", "HSlider", fill_hi)
	theme.set_icon("grabber", "HSlider", TEX_GRABBER)
	theme.set_icon("grabber_highlight", "HSlider", TEX_GRABBER_HI)
	return theme


func _build_ui() -> void:
	_root = Control.new()
	_root.set_anchors_preset(Control.PRESET_FULL_RECT)
	_root.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	_root.theme = _build_theme()
	add_child(_root)

	var backdrop := ColorRect.new()
	backdrop.set_anchors_preset(Control.PRESET_FULL_RECT)
	backdrop.color = Color(0.05, 0.04, 0.08, 0.65)
	backdrop.mouse_filter = Control.MOUSE_FILTER_STOP
	_root.add_child(backdrop)

	var panel := PanelContainer.new()
	panel.position = Vector2(82, 14)
	panel.size = Vector2(316, 242)
	panel.add_theme_stylebox_override("panel", _make_box_tex(TEX_PANEL, 12, 12, 16.0, 12.0))
	_root.add_child(panel)

	var vbox := VBoxContainer.new()
	vbox.add_theme_constant_override("separation", 5)
	panel.add_child(vbox)

	var title := Label.new()
	title.text = "游戏设置"
	title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	title.add_theme_color_override("font_color", COLOR_GOLD)
	vbox.add_child(title)

	var div := TextureRect.new()
	div.texture = TEX_DIVIDER
	div.stretch_mode = TextureRect.STRETCH_KEEP_CENTERED
	vbox.add_child(div)

	var master_row := _add_slider_row(vbox, "主音量", 5.0, func(val: float) -> void:
		if not _syncing:
			GameSettings.set_master_volume(val / 100.0)
			_preview_sfx("katana_slash_1", -11.0)
	)
	_master_slider = master_row[0]
	_master_val = master_row[1]

	var sfx_row := _add_slider_row(vbox, "音效音量", 5.0, func(val: float) -> void:
		if not _syncing:
			GameSettings.set_sfx_volume(val / 100.0)
			_preview_sfx("land", -4.0)
	)
	_sfx_slider = sfx_row[0]
	_sfx_val = sfx_row[1]

	var weapon_row := _add_slider_row(vbox, "武器音量", 5.0, func(val: float) -> void:
		if not _syncing:
			GameSettings.set_weapon_volume(val / 100.0)
			_preview_sfx("katana_slash_1", -11.0)
	)
	_weapon_slider = weapon_row[0]
	_weapon_val = weapon_row[1]

	var shake_row := _add_slider_row(vbox, "屏幕震动", 10.0, func(val: float) -> void:
		if not _syncing:
			GameSettings.set_shake_scale(val / 100.0)
	)
	_shake_slider = shake_row[0]
	_shake_val = shake_row[1]

	_hit_stop_btn = _add_toggle_row(vbox, "打击顿帧", func() -> void:
		GameSettings.set_hit_stop_enabled(not GameSettings.hit_stop_enabled)
	)
	_fullscreen_btn = _add_toggle_row(vbox, "显示模式", func() -> void:
		GameSettings.set_fullscreen(not GameSettings.fullscreen)
	)

	var actions := HBoxContainer.new()
	actions.alignment = BoxContainer.ALIGNMENT_CENTER
	actions.add_theme_constant_override("separation", 14)
	vbox.add_child(actions)

	var reset_btn := Button.new()
	reset_btn.text = "恢复默认"
	reset_btn.custom_minimum_size = Vector2(86, 22)
	reset_btn.pressed.connect(func() -> void:
		GameSettings.reset_defaults()
		_preview_sfx("land", -4.0)
	)
	actions.add_child(reset_btn)

	var resume_btn := Button.new()
	resume_btn.text = "继续游戏"
	resume_btn.custom_minimum_size = Vector2(86, 22)
	resume_btn.pressed.connect(close)
	actions.add_child(resume_btn)

	var hint := Label.new()
	hint.text = "A/D移动  K跳  J攻  L冲  Esc设置"
	hint.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	hint.add_theme_color_override("font_color", COLOR_MUTED)
	vbox.add_child(hint)


func _add_slider_row(parent: VBoxContainer, label_text: String, step: float, on_change: Callable) -> Array:
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 8)
	parent.add_child(row)

	var lbl := Label.new()
	lbl.text = label_text
	lbl.custom_minimum_size = Vector2(56, 0)
	row.add_child(lbl)

	var slider := HSlider.new()
	slider.min_value = 0.0
	slider.max_value = 100.0
	slider.step = step
	slider.custom_minimum_size = Vector2(0, 13)
	slider.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	slider.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	slider.value_changed.connect(on_change)
	row.add_child(slider)

	var val_lbl := Label.new()
	val_lbl.custom_minimum_size = Vector2(36, 0)
	val_lbl.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	val_lbl.add_theme_color_override("font_color", COLOR_GOLD)
	row.add_child(val_lbl)
	return [slider, val_lbl]


func _add_toggle_row(parent: VBoxContainer, label_text: String, on_press: Callable) -> Button:
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 8)
	parent.add_child(row)

	var lbl := Label.new()
	lbl.text = label_text
	lbl.custom_minimum_size = Vector2(56, 0)
	row.add_child(lbl)

	var spacer := Control.new()
	spacer.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	row.add_child(spacer)

	var btn := Button.new()
	btn.custom_minimum_size = Vector2(68, 20)
	btn.pressed.connect(on_press)
	row.add_child(btn)
	return btn
