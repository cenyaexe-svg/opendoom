"""Panda3D application: window, input, fixed 35 Hz tic, wiring of the core to graphics, sound and HUD."""
from __future__ import annotations

import logging

from panda3d.core import ClockObject, KeyboardButton, MouseButton, loadPrcFileData

from config import CACHE_DIR, KEY_TURN_DEG, TIC_DT, VERSION
from engine.events import EventBus
from gameplay.game import Game
from gameplay.player import TicCommand
from world.level_loader import load_level

loadPrcFileData("", "\n".join([
    f"window-title OpenDoom {VERSION}", "win-size 1024 768", "win-fixed-size #t", "sync-video #t",
    "textures-power-2 none", "audio-library-name p3openal_audio", "show-frame-rate-meter #f"]))
from direct.showbase.ShowBase import ShowBase  # noqa: E402  (after prc configuration)
from panda3d.core import WindowProperties  # noqa: E402

from audio.sound_manager import SoundManager  # noqa: E402
from rendering.renderer import LevelRenderer, TextureLibrary  # noqa: E402
from ui.hud_view import HudView  # noqa: E402

log = logging.getLogger("opendoom")
RESTART_DELAY_TICS = 35


class OpenDoomApp(ShowBase):
    def __init__(self, defs, resources, bus: EventBus, start_map: str):
        super().__init__()
        self.defs, self.resources, self.bus = defs, resources, bus
        self.disableMouse()
        props = WindowProperties()
        props.setCursorHidden(True)
        self.win.requestProperties(props)
        self.setBackgroundColor(0, 0, 0)
        # 3D area sits above the status bar (as in Doom: 168 of 200 lines), horizontal FOV 90°
        self.cam.node().getDisplayRegion(0).setDimensions(0, 1, 0.16, 1)
        lens = self.cam.node().getLens()
        lens.setAspectRatio(1024 / (768 * 0.84))
        lens.setFov(90)
        lens.setNearFar(1.0, 6000.0)

        self.textures = TextureLibrary(self.loader, resources)
        self.hud = HudView(self, self.textures)
        self.game: Game | None = None
        self.renderer: LevelRenderer | None = None
        self.sounds: SoundManager | None = None
        self.map_name = start_map
        self.paused = False
        self.acc = 0.0
        self.dead_tics = 0
        self._ignore_mouse = 3
        self._use_prev = False
        self.bus.on("message", lambda text: self.game and self.hud.show_message(text, self.game.tic))
        self.bus.on("sound", lambda name, x, y: self.sounds and self.sounds.play(name, x, y))
        self.accept("escape", self._toggle_pause)
        self.accept("f12", self.userExit)
        self._load_map(start_map, None)
        self.taskMgr.add(self._update, "opendoom-update")

    # --- levels --------------------------------------------------------------------
    def _load_map(self, name: str, carry: dict | None) -> None:
        path = self.resources.find("maps", f"{name}.json")
        if path is None:
            raise FileNotFoundError(f"Map '{name}' not found (maps/{name}.json)")
        if self.renderer:
            self.renderer.destroy()
        self.map_name = name
        self.game = Game(self.defs, load_level(path), self.bus, carry=carry)
        self.renderer = LevelRenderer(self, self.game, self.resources, self.textures)
        self.sounds = SoundManager(self.loader, self.resources, CACHE_DIR, self.game.player)
        self.hud.set_center("")
        self.hud.show_message(self.game.level.name, 0)
        self.dead_tics = 0
        self.acc = 0.0

    def _toggle_pause(self) -> None:
        self.paused = not self.paused
        self.hud.set_center("PAUSED" if self.paused else "")

    # --- input ----------------------------------------------------------------------
    def _down(self, key) -> bool:
        return self.mouseWatcherNode.is_button_down(key)

    def _letter(self, ch: str) -> bool:
        return self._down(KeyboardButton.ascii_key(ch))

    def _read_mouse(self) -> float:
        if not self.mouseWatcherNode.hasMouse():
            return 0.0
        cx, cy = self.win.getXSize() // 2, self.win.getYSize() // 2
        pointer = self.win.getPointer(0)
        dx = pointer.getX() - cx
        self.win.movePointer(0, cx, cy)
        if self._ignore_mouse > 0:
            self._ignore_mouse -= 1
            return 0.0
        return dx * self.defs.settings.mouse_sensitivity

    def _build_cmd(self) -> TicCommand:
        s = self.defs.settings
        run = s.always_run != self._down(KeyboardButton.shift())      # Shift inverts running
        cmd = TicCommand(run=run)
        cmd.forward = float(self._letter("w") or self._down(KeyboardButton.up())) - float(self._letter("s") or self._down(KeyboardButton.down()))
        cmd.strafe = float(self._letter("d")) - float(self._letter("a"))
        cmd.turn = KEY_TURN_DEG * (float(self._down(KeyboardButton.left())) - float(self._down(KeyboardButton.right())))
        cmd.fire = self._down(MouseButton.one()) or self._down(KeyboardButton.control())
        cmd.use = self._letter("e") or self._down(KeyboardButton.space())
        for slot in range(1, 8):
            if self._letter(str(slot)):
                cmd.weapon = slot
        return cmd

    # --- frame ----------------------------------------------------------------------
    def _update(self, task):
        game = self.game
        mouse_turn = self._read_mouse()
        if self.paused:
            return task.cont
        if game.state == "playing" and game.player.alive:
            game.player.angle = (game.player.angle - mouse_turn) % 360     # the mouse turns instantly
        self.acc += min(ClockObject.getGlobalClock().getDt(), 0.25)
        enter = self._down(KeyboardButton.enter())
        while self.acc >= TIC_DT:
            self.acc -= TIC_DT
            cmd = self._build_cmd()
            game.tick(cmd)
            if game.state == "dead":
                self.dead_tics += 1
                self.hud.set_center("YOU DIED\npress E / Space")
                if self.dead_tics > RESTART_DELAY_TICS and (cmd.use or cmd.fire):
                    return self._restart(task)
        if game.state == "exit":
            nxt = game.level.next_map
            self.hud.set_center(self._stats_text(game, nxt))
            if enter and nxt:
                self.bus_carry = game.player.save_state()
                self._load_map(nxt, self.bus_carry)
            return task.cont
        self.renderer.update(self.acc / TIC_DT)
        self.hud.update(game)
        return task.cont

    def _restart(self, task):
        self._load_map(self.map_name, None)
        return task.cont

    @staticmethod
    def _stats_text(game, nxt) -> str:
        t = int(game.time_seconds)
        return (f"LEVEL COMPLETE\nKILLS {game.kills}/{game.total_kills}  ITEMS {game.items}/{game.total_items}\n"
                f"SECRETS {game.secrets}/{game.total_secrets}  TIME {t // 60}:{t % 60:02d}\n"
                + ("Enter — next level" if nxt else "The end. Esc, then F12 to quit"))
