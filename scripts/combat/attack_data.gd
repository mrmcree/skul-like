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
## Heavy hits get the big spark, heavy sound and stronger recoil.
@export var heavy := false
## Pushes the target away (x is flipped automatically by facing).
@export var knockback := Vector2(80, 0)
## Push each target away from the attacker's centre instead of along facing (spins, novas).
@export var radial := false
## Small forward lunge when the attack starts on the ground.
@export var forward_step := 50.0
## Freeze on impact, real seconds. Light 0.04-0.06, heavy 0.10-0.15 (keep under ~0.15).
@export var hit_stop := 0.04
## Camera trauma: 1 light (0.25 trauma), 2 medium, 3 heavy (0.75), 4 max. Shake = trauma².
@export_range(0.0, 4.0, 0.5) var shake_strength := 0.0
