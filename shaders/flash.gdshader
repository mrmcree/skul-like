// Character shader (applied by HitReaction to a character's Body; children inherit it).
//  1. Recolor: pixels whose hue lies in recolor_hue_range (may wrap past 1.0) and are
//     saturated enough get their hue shifted / saturation / value scaled.
//     Used for palette-swap variants (e.g. blue-armoured elite skeleton).
//  2. Flash: tints everything toward flash_color by flash_amount (the "got hit" flash).
shader_type canvas_item;

uniform vec4 flash_color : source_color = vec4(1.0);
uniform float flash_amount : hint_range(0.0, 1.0) = 0.0;

uniform float recolor_hue_shift = 0.0;
uniform float recolor_saturation = 1.0;
uniform float recolor_value = 1.0;
uniform vec2 recolor_hue_range = vec2(0.92, 0.04);
uniform float recolor_min_saturation = 0.25;

vec3 rgb2hsv(vec3 c) {
	vec4 k = vec4(0.0, -1.0 / 3.0, 2.0 / 3.0, -1.0);
	vec4 p = mix(vec4(c.bg, k.wz), vec4(c.gb, k.xy), step(c.b, c.g));
	vec4 q = mix(vec4(p.xyw, c.r), vec4(c.r, p.yzx), step(p.x, c.r));
	float d = q.x - min(q.w, q.y);
	float e = 1.0e-10;
	return vec3(abs(q.z + (q.w - q.y) / (6.0 * d + e)), d / (q.x + e), q.x);
}

vec3 hsv2rgb(vec3 c) {
	vec3 p = abs(fract(c.xxx + vec3(1.0, 2.0 / 3.0, 1.0 / 3.0)) * 6.0 - 3.0);
	return c.z * mix(vec3(1.0), clamp(p - 1.0, 0.0, 1.0), c.y);
}

bool hue_in_range(float hue) {
	vec2 r = recolor_hue_range;
	return r.x > r.y ? (hue >= r.x || hue <= r.y) : (hue >= r.x && hue <= r.y);
}

vec3 recolor(vec3 rgb) {
	bool active = recolor_hue_shift != 0.0 || recolor_saturation != 1.0 || recolor_value != 1.0;
	if (!active) {
		return rgb;
	}
	vec3 hsv = rgb2hsv(rgb);
	if (!hue_in_range(hsv.x) || hsv.y < recolor_min_saturation) {
		return rgb;
	}
	hsv.x = fract(hsv.x + recolor_hue_shift);
	hsv.y = clamp(hsv.y * recolor_saturation, 0.0, 1.0);
	hsv.z = clamp(hsv.z * recolor_value, 0.0, 1.0);
	return hsv2rgb(hsv);
}

void fragment() {
	vec4 tex = texture(TEXTURE, UV);
	// Recolor the texture first, then apply modulate (so tints like the attack telegraph stay as-is).
	vec4 base = vec4(recolor(tex.rgb), tex.a) * COLOR;
	COLOR = vec4(mix(base.rgb, flash_color.rgb, flash_amount), base.a);
}
