class_name SheetFrames
## Builds SpriteFrames from a sprite sheet laid out as rows of equal-sized cells.
##
## `anims` maps animation name -> [row, first column, frame count, fps, loop].


static func build(sheet: Texture2D, cell: Vector2i, anims: Dictionary) -> SpriteFrames:
	var frames := SpriteFrames.new()
	frames.remove_animation(&"default")
	for anim: StringName in anims:
		var spec: Array = anims[anim]
		frames.add_animation(anim)
		frames.set_animation_speed(anim, spec[3])
		frames.set_animation_loop(anim, spec[4])
		for i in int(spec[2]):
			var atlas := AtlasTexture.new()
			atlas.atlas = sheet
			var coords := Vector2i(int(spec[1]) + i, int(spec[0]))
			atlas.region = Rect2(Vector2(coords * cell), Vector2(cell))
			frames.add_frame(anim, atlas)
	return frames
