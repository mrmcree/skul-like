class_name AttackData
extends Resource
## One attack in a combo. Each skull will later own its own list of these.
## Double-click a .tres in data/attacks/ to tweak values in the Inspector.

@export var damage := 10

@export_group("Timing (seconds)")
## Wind-up before the hitbox appears.
@export var startup := 0.06
## How long the hitbox stays active.
@export var active := 0.08
## Cool-down after the hitbox; next combo hit / jump / dash can cancel it.
@export var recovery := 0.18

@export_group("Hitbox")
@export var hitbox_size := Vector2(24, 18)
## Center of the hitbox relative to the player's feet, when facing right.
@export var hitbox_offset := Vector2(14, -11)

@export_group("Feel")
## Heavy hits get the big spark, heavy sound, screen flash and stronger recoil.
@export var heavy := false
## Pushes the target away (x is flipped automatically by facing).
@export var knockback := Vector2(80, 0)
## Small forward lunge when the attack starts on the ground.
@export var forward_step := 50.0
@export var hit_stop := 0.04
@export var shake_strength := 0.0
