"""Draws a sheet with textures, sprites and the status bar into preview.png (for checking without launching the game)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from rendering.canvas import Canvas, rgb
from rendering.sprites import make_sprite
from rendering.textures import GENERATORS
from ui.hud import StatusBar
from tests.helpers import make_game

sheet = Canvas(660, 420, rgb(30, 30, 40))
for i, name in enumerate(GENERATORS):
    sheet.blit(GENERATORS[name](), 4 + (i % 6) * 66, 4 + (i // 6) * 66)
names = [f"{m}_{f}" for m in ("zombieman", "imp") for f in "ABCDEF"]
x = 4
for n in names:
    s = make_sprite(n); sheet.blit(s, x, 140); x += s.w + 4
x = 4
for n in ("medikit", "stimpack", "health_bonus", "armor_bonus", "green_armor", "clip", "shells", "shotgun_pickup",
          "chaingun_pickup", "key_red", "key_blue", "key_yellow", "fireball", "fireball_hit", "plasma", "puff", "blood"):
    s = make_sprite(n); sheet.blit(s, x, 210); x += s.w + 4
x = 4
for w in ("fist", "pistol", "shotgun", "chaingun"):
    for f in ("ready", "fire"):
        sheet.blit(make_sprite(f"{w}:{f}"), x, 245); x += 82
g = make_game()
g.player.take_damage(g, 35, None); g.player.armor = 50; g.player.keys.add("red")
sheet.blit(StatusBar().render(g)[0], 0, 320)
Path("preview.png").write_bytes(sheet.to_png())
print("preview.png")
