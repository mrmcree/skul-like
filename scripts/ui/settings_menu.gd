class_name SettingsMenu
extends CanvasLayer
## Twilight-themed pause & settings overlay (Esc or HUD Settings button).
## Runs during pause (PROCESS_MODE_ALWAYS) and persists via GameSettings.

const PREVIEW_COOLDOWN_MS := 180
const COLOR_PANEL_BG := Color(0.11, 0.10, 0.15, 0.96)
const COLOR_BORDER := Color(0.91, 0.85, 0.67, 1.0)
const COLOR_GOLD := Color(0.95, 0.82, 0.48, 1.0)
const COLOR_TEXT := Color(0.95, 0.91, 0.85, 1.0)
const COLOR_MUTED := Color(0.70, 0.68, 0.78, 1.0)
const COLOR_BTN_BG := Color(0.18, 0.16, 0.24, 1.0)
const COLOR_BTN_HOVER := Color(0.28, 0.24, 0.36, 1.0)
const COLOR_BTN_PRESS := Color(0.38, 0.24, 0.28, 1.0)
const COLOR_ACCENT := Color(0.84, 0.28, 0.26, 1.0)

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
	_fullscreen_btn.text = "全屏" if GameSettings.fullscreen else "窗口"
	_syncing = false


func _preview_sfx(sound: String, base_db: float) -> void:
	if _syncing:
		return
	var now := Time.get_ticks_msec()
	if now - _last_preview_ms < PREVIEW_COOLDOWN_MS:
		return
	_last_preview_ms = now
	Sfx.play(sound, base_db, 0.04)


func _make_font() -> SystemFont:
	var font := SystemFont.new()
	font.font_names = PackedStringArray(["Microsoft YaHei", "SimHei", "PingFang SC", "Noto Sans CJK SC", "sans-serif"])
	font.antialiasing = TextServer.FONT_ANTIALIASING_LCD
	return font


func _make_box(bg: Color, border: Color, border_w := 1, pad_h := 6, pad_v := 3) -> StyleBoxFlat:
	var sb := StyleBoxFlat.new()
	sb.bg_color = bg
	sb.border_color = border
	sb.set_border_width_all(border_w)
	sb.set_corner_radius_all(2)
	sb.content_margin_left = pad_h
	sb.content_margin_right = pad_h
	sb.content_margin_top = pad_v
	sb.content_margin_bottom = pad_v
	return sb


func _build_theme() -> Theme:
	var theme := Theme.new()
	var font := _make_font()
	theme.default_font = font
	theme.default_font_size = 9

	theme.set_color("font_color", "Label", COLOR_TEXT)

	var btn_norm := _make_box(COLOR_BTN_BG, COLOR_BORDER, 1, 8, 2)
	var btn_hover := _make_box(COLOR_BTN_HOVER, COLOR_GOLD, 1, 8, 2)
	var btn_press := _make_box(COLOR_BTN_PRESS, COLOR_GOLD, 1, 8, 2)
	theme.set_stylebox("normal", "Button", btn_norm)
	theme.set_stylebox("hover", "Button", btn_hover)
	theme.set_stylebox("focus", "Button", btn_hover)
	theme.set_stylebox("pressed", "Button", btn_press)
	theme.set_color("font_color", "Button", COLOR_TEXT)
	theme.set_color("font_hover_color", "Button", COLOR_GOLD)
	theme.set_color("font_focus_color", "Button", COLOR_GOLD)
	theme.set_color("font_pressed_color", "Button", COLOR_TEXT)

	var slider_bg := _make_box(Color(0.06, 0.05, 0.09, 1.0), Color(0.45, 0.42, 0.52, 1.0), 1, 0, 2)
	var slider_fill := _make_box(COLOR_ACCENT, COLOR_ACCENT, 0, 0, 2)
	var slider_hi := _make_box(COLOR_GOLD, COLOR_GOLD, 0, 0, 2)
	theme.set_stylebox("slider", "HSlider", slider_bg)
	theme.set_stylebox("grabber_area", "HSlider", slider_fill)
	theme.set_stylebox("grabber_area_highlight", "HSlider", slider_hi)
	var grabber := _make_grabber_texture(COLOR_BORDER)
	var grabber_hi := _make_grabber_texture(COLOR_GOLD)
	theme.set_icon("grabber", "HSlider", grabber)
	theme.set_icon("grabber_highlight", "HSlider", grabber_hi)
	return theme


func _make_grabber_texture(fill: Color) -> ImageTexture:
	var img := Image.create(7, 10, false, Image.FORMAT_RGBA8)
	img.fill(Color(0.08, 0.06, 0.10, 1.0))
	for y in range(1, 9):
		for x in range(1, 6):
			img.set_pixel(x, y, fill)
	return ImageTexture.create_from_image(img)


func _build_ui() -> void:
	_root = Control.new()
	_root.set_anchors_preset(Control.PRESET_FULL_RECT)
	_root.theme = _build_theme()
	add_child(_root)

	var backdrop := ColorRect.new()
	backdrop.set_anchors_preset(Control.PRESET_FULL_RECT)
	backdrop.color = Color(0.05, 0.04, 0.08, 0.65)
	backdrop.mouse_filter = Control.MOUSE_FILTER_STOP
	_root.add_child(backdrop)

	var panel := PanelContainer.new()
	panel.position = Vector2(96, 20)
	panel.size = Vector2(288, 230)
	var panel_sb := _make_box(COLOR_PANEL_BG, COLOR_BORDER, 2, 14, 10)
	panel_sb.shadow_color = Color(0.03, 0.02, 0.05, 0.85)
	panel_sb.shadow_size = 3
	panel.add_theme_stylebox_override("panel", panel_sb)
	_root.add_child(panel)

	var vbox := VBoxContainer.new()
	vbox.add_theme_constant_override("separation", 6)
	panel.add_child(vbox)

	var title := Label.new()
	title.text = "游戏设置"
	title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	title.add_theme_font_size_override("font_size", 11)
	title.add_theme_color_override("font_color", COLOR_GOLD)
	vbox.add_child(title)

	var div := ColorRect.new()
	div.custom_minimum_size = Vector2(0, 1)
	div.color = Color(0.91, 0.85, 0.67, 0.45)
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

	var spacer := Control.new()
	spacer.custom_minimum_size = Vector2(0, 2)
	vbox.add_child(spacer)

	var actions := HBoxContainer.new()
	actions.alignment = BoxContainer.ALIGNMENT_CENTER
	actions.add_theme_constant_override("separation", 14)
	vbox.add_child(actions)

	var reset_btn := Button.new()
	reset_btn.text = "恢复默认"
	reset_btn.custom_minimum_size = Vector2(76, 20)
	reset_btn.pressed.connect(func() -> void:
		GameSettings.reset_defaults()
		_preview_sfx("land", -4.0)
	)
	actions.add_child(reset_btn)

	var resume_btn := Button.new()
	resume_btn.text = "继续游戏"
	resume_btn.custom_minimum_size = Vector2(76, 20)
	resume_btn.pressed.connect(close)
	actions.add_child(resume_btn)

	var hint := Label.new()
	hint.text = "A/D 移动 · K/空格 跳跃 · J 攻击 · L/Shift 冲刺 · Esc 设置"
	hint.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	hint.add_theme_font_size_override("font_size", 7)
	hint.add_theme_color_override("font_color", COLOR_MUTED)
	vbox.add_child(hint)


func _add_slider_row(parent: VBoxContainer, label_text: String, step: float, on_change: Callable) -> Array:
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 8)
	parent.add_child(row)

	var lbl := Label.new()
	lbl.text = label_text
	lbl.custom_minimum_size = Vector2(62, 0)
	row.add_child(lbl)

	var slider := HSlider.new()
	slider.min_value = 0.0
	slider.max_value = 100.0
	slider.step = step
	slider.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	slider.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	slider.value_changed.connect(on_change)
	row.add_child(slider)

	var val_lbl := Label.new()
	val_lbl.custom_minimum_size = Vector2(30, 0)
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
	lbl.custom_minimum_size = Vector2(62, 0)
	row.add_child(lbl)

	var spacer := Control.new()
	spacer.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	row.add_child(spacer)

	var btn := Button.new()
	btn.custom_minimum_size = Vector2(64, 18)
	btn.pressed.connect(on_press)
	row.add_child(btn)
	return btn
