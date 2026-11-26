class_name SkillData
extends AttackData
## A samurai skill: an AttackData (damage, startup/active/recovery, hitbox, feel) plus how the
## body moves, its cooldown and its pixelfx effect. PlayerSkills runs it in the SKILL state.
## Double-click a .tres in data/skills/ to tweak values in the Inspector.

enum Kind {
	ISSEN,   ## 一闪: dash through untouchable, sheathe, then every target is cut at once
	SPIN,    ## 旋风斩: hits both sides; set `radial` so enemies fly away from the body
	RISING,  ## 燕返·升: rising cut that launches the target and carries the samurai up
	CROSS,   ## 十字斩: a down cut, then `follow_up` crossing it (two hits, the second heavy)
	BLINK,   ## 瞬身斩: vanish, reappear behind the nearest enemy facing it, and cut
}

@export var display_name := ""
@export var kind := Kind.SPIN
## Seconds before the skill can be used again.
@export var cooldown := 3.0
## The skill's own hero animation (e.g. &"attack_spin"); empty = use `anim_index`.
@export var anim := &""
## Combo row used when `anim` is empty or not in the sheet yet: 0 = cut, 1 = rising cut, 2 = thrust.
@export_range(0, 2) var anim_index := 0

## CROSS: the second cut (its own damage, timing, hitbox and feel), played on combo row
## `anim2_index` straight after this skill's active window.
@export var follow_up: AttackData
@export_range(0, 2) var anim2_index := 1

@export_group("Movement")
## ISSEN: distance covered during the active window (px).
@export var travel := 0.0
## ISSEN: beat after arriving before the cuts land (s).
@export var sheath_delay := 0.0
## RISING: vertical speed when the swing starts (negative = up).
@export var rise_speed := 0.0
## In the air, hang during wind-up and swing instead of falling.
@export var hang := true
## BLINK: how far (px, horizontally) an enemy can be to be targeted; `travel` is used with none.
@export var blink_range := 150.0
## BLINK: where to reappear, this far past the enemy (px).
@export var blink_behind := 18.0
## BLINK: when the body disappears and is moved (s from the start).
@export var blink_hide := 0.16
## BLINK: when the body shows again at the new place (s from the start; < startup).
@export var blink_arrive := 0.33

@export_group("Effect")
## Effect name in assets/vfx (see VfxCatalog); spawned when the hitbox opens.
@export var vfx := ""
## Optional second sheet drawn BEHIND the body (e.g. the far half of a spin), same pivot.
@export var vfx_back := ""
## From the feet, facing right (x is mirrored with facing).
@export var vfx_offset := Vector2.ZERO
## Start the effect (and swing sound) this many seconds before the hitbox opens, so a slash
## that takes time to draw finishes exactly on the hit. 0 = when the hitbox opens.
@export var vfx_lead := 0.0
@export var swing_sound := ""
## Spawned at the feet when the skill starts (BLINK: the vanishing burst).
@export var vfx_start := ""
## BLINK: spawned at the new place when the body is moved (the arrival).
@export var vfx_arrive := ""
