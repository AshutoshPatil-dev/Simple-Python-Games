"""
🥷 Finger Ninja — Python Edition
Uses: pygame (rendering), mediapipe (hand tracking), opencv (webcam)

Controls:
  - Move your INDEX FINGER TIP to slice fruits
  - ✊ FIST  → Pause
  - 🖐 OPEN HAND → Resume
  - ESC → Quit
"""

import sys, math, random, time, threading
import pygame
import cv2
import numpy as np

try:
    import mediapipe as mp
    from mediapipe.tasks import python
    from mediapipe.tasks.python import vision
    import os, urllib.request
    task_path = "hand_landmarker.task"
    if not os.path.exists(task_path):
        url = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"
        print("Downloading hand tracking model...")
        urllib.request.urlretrieve(url, task_path)
    # hands_det will be created in the camera thread
    hands_det = None
except Exception as e:
    print("Hand tracking disabled:", e)
    mp = None
    hands_det = None

# ── Init ──────────────────────────────────────────────────────────────
pygame.init()
pygame.mixer.init(frequency=44100, size=-16, channels=1, buffer=512)

INFO   = pygame.display.Info()
W, H   = 1280, 720
screen = pygame.display.set_mode((W, H), pygame.RESIZABLE)
pygame.display.set_caption("🥷 Finger Ninja")
clock  = pygame.time.Clock()

# ── Fonts ─────────────────────────────────────────────────────────────
try:
    FONT_BIG   = pygame.font.SysFont("Arial Rounded MT Bold", 96, bold=True)
    FONT_MED   = pygame.font.SysFont("Arial Rounded MT Bold", 48, bold=True)
    FONT_SM    = pygame.font.SysFont("Arial Rounded MT Bold", 28)
    FONT_HUD   = pygame.font.SysFont("Arial Rounded MT Bold", 52, bold=True)
    FONT_COMBO = pygame.font.SysFont("Arial Rounded MT Bold", 36, bold=True)
    FONT_EMOJI = pygame.font.SysFont("Segoe UI Emoji", 60)
    FONT_EMOJI_SML = pygame.font.SysFont("Segoe UI Emoji", 32)
except:
    FONT_BIG   = pygame.font.Font(None, 96)
    FONT_MED   = pygame.font.Font(None, 48)
    FONT_SM    = pygame.font.Font(None, 28)
    FONT_HUD   = pygame.font.Font(None, 52)
    FONT_COMBO = pygame.font.Font(None, 36)
    FONT_EMOJI = pygame.font.Font(None, 60)
    FONT_EMOJI_SML = pygame.font.Font(None, 32)

# ── Colors ────────────────────────────────────────────────────────────
DARK       = (10,  10,  15)
NEON_GOLD  = (255, 215, 0)
NEON_CYAN  = (0,   234, 255)
NEON_GREEN = (57,  255, 20)
NEON_RED   = (255, 56,  96)
WHITE      = (255, 255, 255)
BLACK      = (0,   0,   0)

# ── Difficulty ────────────────────────────────────────────────────────
DIFFICULTIES = {
    "Easy":   dict(spawn_rate=2.5, max_fruits=6,  base_speed=220, bomb_chance=0.06),
    "Medium": dict(spawn_rate=1.6, max_fruits=8,  base_speed=320, bomb_chance=0.12),
    "Hard":   dict(spawn_rate=1.1, max_fruits=10, base_speed=420, bomb_chance=0.20),
}
difficulty   = "Easy"
diff         = DIFFICULTIES[difficulty]

# ── Fruit Types ───────────────────────────────────────────────────────
FRUIT_TYPES = [
    dict(emoji="🍎", name="apple",      color=(255, 59,  48),  splat=(255, 107, 107)),
    dict(emoji="🍊", name="orange",     color=(255, 149, 0),   splat=(255, 179, 71)),
    dict(emoji="🍋", name="lemon",      color=(255, 214, 10),  splat=(255, 229, 102)),
    dict(emoji="🍇", name="grapes",     color=(191, 90,  242), splat=(208, 128, 255)),
    dict(emoji="🍓", name="strawberry", color=(255, 45,  85),  splat=(255, 107, 133)),
    dict(emoji="🍉", name="watermelon", color=(48,  209, 88),  splat=(255, 107, 107)),
    dict(emoji="🥝", name="kiwi",       color=(52,  199, 89),  splat=(168, 230, 163)),
    dict(emoji="🍑", name="peach",      color=(255, 107, 157), splat=(255, 179, 200)),
]

# ── State ─────────────────────────────────────────────────────────────
STATE_MENU     = 0
STATE_PLAYING  = 1
STATE_PAUSED   = 2
STATE_GAMEOVER = 3
game_state     = STATE_MENU

score          = 0
lives          = 3
combo          = 0
combo_timer    = 0.0
fruits         = []
particles      = []
slice_trail    = []   # list of (x, y, timestamp)
finger_pos     = None
last_finger    = None
spawn_timer    = 0.0
shake_end      = 0.0
shake_amt      = 0.0

# Webcam surface (mirrored feed drawn on canvas)
webcam_surface = None
cam_ready      = False

# ── Sound ─────────────────────────────────────────────────────────────
def make_tone(freq=800, duration=0.15, wave='sawtooth', volume=0.3):
    sample_rate = 44100
    n = int(sample_rate * duration)
    t = np.linspace(0, duration, n, endpoint=False)
    if wave == 'sawtooth':
        samples = 2 * (t * freq - np.floor(t * freq + 0.5))
    else:
        samples = np.sin(2 * np.pi * freq * t)
    env = np.exp(-t / (duration * 0.6))
    samples = (samples * env * volume * 32767).astype(np.int16)
    stereo = np.column_stack([samples, samples])
    return pygame.sndarray.make_sound(stereo)

def make_noise(duration=0.35, volume=0.5):
    sample_rate = 44100
    n = int(sample_rate * duration)
    t = np.linspace(0, duration, n, endpoint=False)
    samples = (np.random.uniform(-1, 1, n) * np.exp(-t / 0.08) * volume * 32767).astype(np.int16)
    stereo = np.column_stack([samples, samples])
    return pygame.sndarray.make_sound(stereo)

try:
    SND_SLICE = make_tone(800, 0.15, 'sawtooth', 0.25)
    SND_BOMB  = make_noise(0.35, 0.5)
    SND_MISS  = make_tone(220, 0.3,  'sine',     0.25)
except:
    SND_SLICE = SND_BOMB = SND_MISS = None

def play(snd):
    try:
        if snd: snd.play()
    except: pass

# ── Emoji rendering helper ────────────────────────────────────────────
_emoji_cache = {}
def render_emoji(emoji, size=60):
    key = (emoji, size)
    if key not in _emoji_cache:
        try:
            f = pygame.font.SysFont("Segoe UI Emoji,Apple Color Emoji,Noto Color Emoji", size)
        except:
            f = pygame.font.Font(None, size)
        surf = f.render(emoji, True, WHITE)
        _emoji_cache[key] = surf
    return _emoji_cache[key]

# ── Fruit Class ───────────────────────────────────────────────────────
class Fruit:
    def __init__(self):
        global W, H
        self.is_bomb = random.random() < diff['bomb_chance']
        if self.is_bomb:
            self.ftype  = None
            self.emoji  = "💣"
            self.color  = (85, 85, 85)
            self.splat  = NEON_RED
        else:
            self.ftype  = random.choice(FRUIT_TYPES)
            self.emoji  = self.ftype['emoji']
            self.color  = self.ftype['color']
            self.splat  = self.ftype['splat']

        self.radius   = random.randint(30, 46)
        self.x        = random.randint(100, W - 100)
        self.y        = float(H + self.radius + 10)
        spd           = diff['base_speed'] + random.uniform(0, 120)
        angle         = -math.pi / 2 + random.uniform(-0.55, 0.55)
        self.vx       = math.cos(angle) * spd
        self.vy       = math.sin(angle) * spd * 1.35
        self.gravity  = 220 + random.uniform(0, 40)
        self.rot      = random.uniform(0, 360)
        self.rot_spd  = random.uniform(-90, 90)

        self.sliced    = False
        self.slice_age = 0.0
        self.slice_ang = 0.0
        self.half_off  = 0.0
        self.opacity   = 255

    def update(self, dt):
        if self.sliced:
            self.slice_age += dt
            self.half_off  += 180 * dt
            self.vy        += self.gravity * 2 * dt
            self.x         += self.vx * dt
            self.y         += self.vy * dt
            fade = max(0.0, 1.0 - self.slice_age / 0.5)
            self.opacity   = int(fade * 255)
            return
        self.vy  += self.gravity * dt
        self.x   += self.vx * dt
        self.y   += self.vy * dt
        self.rot += self.rot_spd * dt

    def off_screen(self):
        return (self.y > H + self.radius + 30
                or self.x < -150
                or self.x > W + 150)

    def draw(self, surf):
        alpha = self.opacity
        sz = self.radius * 2
        emoji_surf = render_emoji(self.emoji, sz)
        emoji_surf = emoji_surf.copy()

        if self.sliced:
            dx_a = math.cos(self.slice_ang + math.pi) * self.half_off
            dy_a = math.sin(self.slice_ang + math.pi) * self.half_off * 0.5
            dx_b = math.cos(self.slice_ang) * self.half_off
            dy_b = math.sin(self.slice_ang) * self.half_off * 0.3

            for dx, dy, clip_top in [(dx_a, dy_a, True), (dx_b, dy_b, False)]:
                cx = int(self.x + dx)
                cy = int(self.y + dy)
                half = emoji_surf.copy()
                half.set_alpha(alpha)
                clip_h = half.get_height() // 2
                if clip_top:
                    clip_rect = pygame.Rect(0, 0, half.get_width(), clip_h)
                else:
                    clip_rect = pygame.Rect(0, clip_h, half.get_width(), clip_h)
                clipped = pygame.Surface(half.get_size(), pygame.SRCALPHA)
                clipped.blit(half, (0, 0))
                mask = pygame.Surface(half.get_size(), pygame.SRCALPHA)
                mask.fill((0, 0, 0, 0))
                pygame.draw.rect(mask, (255, 255, 255, 255), clip_rect)
                clipped.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
                rect = clipped.get_rect(center=(cx, cy))
                surf.blit(clipped, rect)

            # Juice splat
            if self.slice_age < 0.25:
                t = self.slice_age / 0.25
                for i in range(6):
                    ang = (math.pi * 2 / 6) * i + self.slice_ang
                    r   = t * self.radius * 2
                    px  = int(self.x + math.cos(ang) * r)
                    py  = int(self.y + math.sin(ang) * r)
                    rad = max(1, int((1 - t) * 10))
                    a   = int((1 - t) * 0.7 * alpha)
                    col = (*self.splat, a)
                    s2  = pygame.Surface((rad * 2, rad * 2), pygame.SRCALPHA)
                    pygame.draw.circle(s2, col, (rad, rad), rad)
                    surf.blit(s2, (px - rad, py - rad))
        else:
            rotated = pygame.transform.rotate(emoji_surf, -self.rot)
            rotated.set_alpha(alpha)
            rect = rotated.get_rect(center=(int(self.x), int(self.y)))
            surf.blit(rotated, rect)

# ── Particle ──────────────────────────────────────────────────────────
class Particle:
    def __init__(self, x, y, color, ptype='juice', text='', combo=False, combo_val=0):
        self.x, self.y = float(x), float(y)
        self.color     = color
        self.ptype     = ptype
        self.text      = text
        self.is_combo  = combo
        self.combo_val = combo_val
        if ptype == 'score':
            spd = 60
        else:
            spd = random.uniform(100, 220)
        ang      = random.uniform(0, math.pi * 2)
        self.vx  = math.cos(ang) * spd
        self.vy  = math.sin(ang) * spd - (80 if ptype == 'score' else 0)
        self.life = 1.0
        self.decay = 0.7 if ptype == 'score' else random.uniform(1.2, 1.8)
        self.size  = 0 if ptype == 'score' else random.uniform(4, 10)

    def update(self, dt):
        self.x    += self.vx * dt
        self.y    += self.vy * dt
        self.vy   += 200 * dt
        self.life -= self.decay * dt

    def draw(self, surf):
        if self.life <= 0: return
        alpha = max(0, int(self.life * 255))
        if self.ptype == 'score':
            label  = f"COMBO x{self.combo_val}!" if self.is_combo else "+1"
            font   = FONT_COMBO if self.is_combo else FONT_SM
            color  = NEON_GOLD if self.is_combo else WHITE
            ts     = font.render(label, True, color)
            ts.set_alpha(alpha)
            surf.blit(ts, ts.get_rect(center=(int(self.x), int(self.y))))
        else:
            r   = max(1, int(self.size * self.life))
            col = (*self.color, alpha)
            s2  = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            pygame.draw.circle(s2, col, (r, r), r)
            surf.blit(s2, (int(self.x) - r, int(self.y) - r))

def spawn_particles(x, y, color, count=12):
    for _ in range(count):
        particles.append(Particle(x, y, color))

def spawn_score_particle(x, y, is_combo, combo_val):
    p = Particle(x, y, WHITE, ptype='score', combo=is_combo, combo_val=combo_val)
    p.vx = random.uniform(-30, 30)
    particles.append(p)

# ── Slice Trail ───────────────────────────────────────────────────────
TRAIL_LIFE = 0.20   # seconds

def add_trail(x, y):
    slice_trail.append((x, y, time.time()))

def draw_trail(surf):
    now = time.time()
    valid = [(x, y, t) for x, y, t in slice_trail if now - t < TRAIL_LIFE]
    slice_trail[:] = valid
    if len(valid) < 2: return
    for i in range(1, len(valid)):
        px, py, pt = valid[i - 1]
        cx, cy, ct = valid[i]
        age   = (now - ct) / TRAIL_LIFE
        t     = i / len(valid)
        alpha = max(0, int((1 - age) * t * 220))
        width = max(1, int(3 + t * 12))
        hue   = int(195 + t * 60)
        color = pygame.Color(0)
        color.hsva = (hue % 360, 100, 90, 100)
        col   = (color.r, color.g, color.b, alpha)
        # Draw with alpha via surface
        line_surf = pygame.Surface((W, H), pygame.SRCALPHA)
        pygame.draw.line(line_surf, col, (int(px), int(py)), (int(cx), int(cy)), width)
        surf.blit(line_surf, (0, 0))
    # Glow dot at tip
    if finger_pos:
        fx, fy = finger_pos
        pygame.draw.circle(surf, NEON_CYAN, (int(fx), int(fy)), 9)
        glow = pygame.Surface((40, 40), pygame.SRCALPHA)
        pygame.draw.circle(glow, (*NEON_CYAN, 80), (20, 20), 18)
        surf.blit(glow, (int(fx) - 20, int(fy) - 20))

# ── Collision ─────────────────────────────────────────────────────────
def segment_circle(p1, p2, cx, cy, r):
    dx, dy = p2[0] - p1[0], p2[1] - p1[1]
    fx, fy = p1[0] - cx,    p1[1] - cy
    a = dx * dx + dy * dy
    if a == 0: return False
    b = 2 * (fx * dx + fy * dy)
    c = fx * fx + fy * fy - r * r
    disc = b * b - 4 * a * c
    if disc < 0: return False
    disc = math.sqrt(disc)
    t1 = (-b - disc) / (2 * a)
    t2 = (-b + disc) / (2 * a)
    return (0 <= t1 <= 1) or (0 <= t2 <= 1)

def check_slice():
    global score, combo, combo_timer, lives
    if len(slice_trail) < 2: return
    recent = slice_trail[-3:]
    if len(recent) < 2: return
    for f in fruits:
        if f.sliced: continue
        for i in range(1, len(recent)):
            p1 = recent[i - 1][:2]
            p2 = recent[i][:2]
            if segment_circle(p1, p2, f.x, f.y, f.radius * 1.1):
                f.sliced = True
                dx, dy = p2[0] - p1[0], p2[1] - p1[1]
                f.slice_ang = math.atan2(dy, dx)
                if f.is_bomb:
                    handle_bomb(f.x, f.y)
                else:
                    handle_slice(f)
                break

def handle_slice(f):
    global score, combo, combo_timer
    score       += 1
    combo       += 1
    combo_timer  = 2.0
    spawn_particles(f.x, f.y, f.splat, 14)
    spawn_score_particle(f.x, f.y - f.radius, combo > 2, combo)
    play(SND_SLICE)
    screen_shake(10, 0.12)

def handle_bomb(x, y):
    global combo
    combo = 0
    spawn_particles(x, y, NEON_RED, 20)
    lose_life()
    play(SND_BOMB)
    screen_shake(16, 0.4)

def handle_miss():
    global combo
    combo = 0
    play(SND_MISS)
    lose_life()

def lose_life():
    global lives
    lives -= 1
    if lives <= 0:
        end_game()

def screen_shake(amt, dur):
    global shake_amt, shake_end
    shake_amt = amt
    shake_end = time.time() + dur

def get_shake():
    if time.time() > shake_end:
        return (0, 0)
    t = (shake_end - time.time()) / max(0.001, shake_end - (shake_end - shake_amt * 0.02))
    s = shake_amt * min(1, t)
    return (random.uniform(-s, s), random.uniform(-s, s))

# ── Gesture Detection ─────────────────────────────────────────────────
def is_fist(lm):
    tips = [8, 12, 16, 20]
    mcps = [5,  9, 13, 17]
    closed = sum(1 for t, m in zip(tips, mcps) if lm[t].y > lm[m].y)
    return closed >= 3

def is_open_hand(lm):
    tips = [8, 12, 16, 20]
    mcps = [5,  9, 13, 17]
    ext = sum(1 for t, m in zip(tips, mcps) if lm[t].y < lm[m].y - 0.03)
    return ext >= 3

gesture_fist_hold = 0
gesture_open_hold = 0
GESTURE_THRESH    = 10
mouse_down        = False

# ── Camera Thread ─────────────────────────────────────────────────────
# (hands_det is initialized in the imports section)

_cam_frame   = None
_cam_lm      = None
_cam_running = True
_cam_lock    = threading.Lock()

def camera_loop():
    global _cam_frame, _cam_lm, cam_ready, finger_pos, last_finger
    global gesture_fist_hold, gesture_open_hold, game_state, hands_det

    pass

    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    if not cap.isOpened():
        print("⚠️ ERROR: Could not open webcam! Please check if another app is using it or if Windows Privacy Settings are blocking Python from accessing the camera.")
    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    while _cam_running:
        ret, frame = cap.read()
        if not ret:
            time.sleep(0.03)
            continue
        # Mirror
        frame = cv2.flip(frame, 1)

        with _cam_lock:
            _cam_frame = frame.copy()

        pass

    cap.release()

def get_webcam_surface():
    with _cam_lock:
        if _cam_frame is None:
            return None
        frame = _cam_frame
    frame_rgb  = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    resized    = cv2.resize(frame_rgb, (W, H))
    surf       = pygame.surfarray.make_surface(resized.swapaxes(0, 1))
    return surf

# ── Game Flow ─────────────────────────────────────────────────────────
def reset_game():
    global score, lives, combo, combo_timer, fruits, particles, slice_trail, spawn_timer
    global finger_pos, last_finger
    score       = 0
    lives       = 3
    combo       = 0
    combo_timer = 0.0
    fruits      = []
    particles   = []
    slice_trail = []
    spawn_timer = 0.0

def end_game():
    global game_state
    game_state = STATE_GAMEOVER

# ── HUD Helpers ───────────────────────────────────────────────────────
def draw_glass_box(surf, rect, border_color=(255,255,255,38)):
    box = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    box.fill((255, 255, 255, 15))
    pygame.draw.rect(box, border_color, box.get_rect(), 2, border_radius=14)
    surf.blit(box, rect.topleft)

def draw_text_shadow(surf, text, font, color, cx, cy, shadow_color=(0,0,0), offset=3):
    sh = font.render(text, True, shadow_color)
    surf.blit(sh, sh.get_rect(center=(cx + offset, cy + offset)))
    ts = font.render(text, True, color)
    surf.blit(ts, ts.get_rect(center=(cx, cy)))

def draw_hud(surf):
    # Score
    r1 = pygame.Rect(20, 14, 160, 80)
    draw_glass_box(surf, r1)
    lbl = FONT_SM.render("SCORE", True, (255, 255, 255, 115))
    surf.blit(lbl, lbl.get_rect(centerx=r1.centerx, top=r1.top + 10))
    draw_text_shadow(surf, str(score), FONT_HUD, NEON_GOLD, r1.centerx, r1.centery + 14)

    # Lives
    r2 = pygame.Rect(W - 180, 14, 160, 80)
    draw_glass_box(surf, r2)
    lbl2 = FONT_SM.render("LIVES", True, (255, 255, 255, 115))
    surf.blit(lbl2, lbl2.get_rect(centerx=r2.centerx, top=r2.top + 10))
    hearts = "❤" * max(0, lives) + "♡" * max(0, 3 - lives)
    h_surf = FONT_EMOJI_SML.render(hearts, True, (255, 60, 80))
    surf.blit(h_surf, h_surf.get_rect(centerx=r2.centerx, centery=r2.centery + 16))

    # Difficulty badge
    badge = FONT_SM.render(difficulty, True, NEON_GREEN)
    bx = W // 2 - badge.get_width() // 2 - 10
    br = pygame.Rect(bx, 16, badge.get_width() + 20, 32)
    draw_glass_box(surf, br)
    surf.blit(badge, badge.get_rect(center=br.center))

    # Combo
    if combo_timer > 0 and combo > 2:
        ct = FONT_COMBO.render(f"✦ {combo}x COMBO! ✦", True, NEON_CYAN)
        surf.blit(ct, ct.get_rect(centerx=W // 2, top=110))

    # Gesture / mouse tip
    if mp is not None:
        tip_text = "✊ Fist = Pause  |  🖐 Open = Resume"
    else:
        tip_text = "Drag mouse to slice. Press P to pause/resume."
    tip = FONT_SM.render(tip_text, True, (255, 255, 255, 90))
    tip.set_alpha(90)
    surf.blit(tip, tip.get_rect(centerx=W // 2, bottom=H - 12))

def draw_overlay(surf, title, subtitle="", buttons=None):
    overlay = pygame.Surface((W, H), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 185))
    surf.blit(overlay, (0, 0))
    draw_text_shadow(surf, title, FONT_BIG, WHITE, W // 2, H // 2 - 160,
                     shadow_color=(80, 40, 0), offset=4)
    if subtitle:
        sub = FONT_SM.render(subtitle, True, (255, 255, 255, 170))
        sub.set_alpha(170)
        surf.blit(sub, sub.get_rect(centerx=W // 2, top=H // 2 - 80))
    if buttons:
        for i, (label, rect, color) in enumerate(buttons):
            pygame.draw.rect(surf, color, rect, border_radius=30)
            pygame.draw.rect(surf, WHITE, rect, 2, border_radius=30)
            bt = FONT_MED.render(label, True, BLACK if color == NEON_GOLD else WHITE)
            surf.blit(bt, bt.get_rect(center=rect.center))

def draw_menu(surf):
    draw_overlay(surf, "🥷 FINGER NINJA",
                 "Slice fruits with your index finger!  Avoid 💣  Don't let 3 fall.")
    # Difficulty buttons
    diff_names = list(DIFFICULTIES.keys())
    bw, bh = 150, 50
    total  = len(diff_names) * bw + (len(diff_names) - 1) * 14
    start  = W // 2 - total // 2
    for i, name in enumerate(diff_names):
        bx   = start + i * (bw + 14)
        rect = pygame.Rect(bx, H // 2 - 10, bw, bh)
        col  = NEON_GREEN if name == difficulty else (80, 80, 80)
        pygame.draw.rect(surf, col, rect, border_radius=25)
        pygame.draw.rect(surf, WHITE, rect, 2, border_radius=25)
        dt   = FONT_SM.render(name, True, BLACK if name == difficulty else WHITE)
        surf.blit(dt, dt.get_rect(center=rect.center))
    # Start button
    start_rect = pygame.Rect(W // 2 - 140, H // 2 + 70, 280, 60)
    pygame.draw.rect(surf, NEON_GOLD, start_rect, border_radius=30)
    st = FONT_MED.render("START GAME", True, BLACK)
    surf.blit(st, st.get_rect(center=start_rect.center))
    return start_rect, diff_names, [(start + i * (bw + 14), H // 2 - 10, bw, bh) for i in range(len(diff_names))]

def draw_gameover(surf):
    draw_overlay(surf, "GAME OVER")
    sc_surf = FONT_BIG.render(str(score), True, NEON_GOLD)
    surf.blit(sc_surf, sc_surf.get_rect(centerx=W // 2, top=H // 2 - 60))
    lbl = FONT_SM.render("FINAL SCORE", True, (255, 255, 255, 130))
    lbl.set_alpha(130)
    surf.blit(lbl, lbl.get_rect(centerx=W // 2, top=H // 2 + 40))
    again_rect = pygame.Rect(W // 2 - 160, H // 2 + 90, 320, 60)
    pygame.draw.rect(surf, NEON_GOLD, again_rect, border_radius=30)
    at = FONT_MED.render("PLAY AGAIN 🔄", True, BLACK)
    surf.blit(at, at.get_rect(center=again_rect.center))
    return again_rect

def draw_paused(surf):
    draw_overlay(surf, "⏸  PAUSED",
                 "Make an open hand gesture to resume")
    resume_rect = pygame.Rect(W // 2 - 120, H // 2 + 40, 240, 55)
    pygame.draw.rect(surf, NEON_GOLD, resume_rect, border_radius=28)
    rt = FONT_MED.render("RESUME", True, BLACK)
    surf.blit(rt, rt.get_rect(center=resume_rect.center))
    return resume_rect

def draw_background(surf):
    ws = get_webcam_surface()
    if ws:
        surf.blit(ws, (0, 0))
        dark = pygame.Surface((W, H), pygame.SRCALPHA)
        dark.fill((0, 0, 0, 72))
        surf.blit(dark, (0, 0))
    else:
        surf.fill(DARK)

# ── Main ──────────────────────────────────────────────────────────────
def main():
    global game_state, difficulty, diff, score, lives, combo, combo_timer
    global fruits, particles, slice_trail, spawn_timer, W, H, finger_pos, mouse_down
    global _cam_frame, last_finger, gesture_fist_hold, gesture_open_hold

    hands_det = None
    if mp is not None:
        try:
            from mediapipe.tasks import python
            from mediapipe.tasks.python import vision
            base_options = python.BaseOptions(model_asset_path="hand_landmarker.task")
            options = vision.HandLandmarkerOptions(base_options=base_options, num_hands=1)
            hands_det = vision.HandLandmarker.create_from_options(options)
        except Exception as e:
            print("Failed to init HandLandmarker:", e)

    cam_thread = threading.Thread(target=camera_loop, daemon=True)
    cam_thread.start()
    time.sleep(0.8)  # let camera init

    dt = 0.0
    start_rect = None
    diff_rects = []
    diff_names = []
    again_rect = None
    resume_rect = None

    while True:
        dt = clock.tick(60) / 1000.0
        dt = min(dt, 0.05)  # cap for window-drag spikes

        # ── Events ───────────────────────────────────────────────────
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                global _cam_running
                _cam_running = False
                pygame.quit(); sys.exit()

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    _cam_running = False
                    pygame.quit(); sys.exit()
                if event.key == pygame.K_p and game_state == STATE_PLAYING:
                    game_state = STATE_PAUSED
                if event.key == pygame.K_p and game_state == STATE_PAUSED:
                    game_state = STATE_PLAYING
                    slice_trail.clear()

            if event.type == pygame.VIDEORESIZE:
                W, H = event.w, event.h

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mouse_down = True
                mx, my = event.pos
                if game_state == STATE_MENU:
                    if start_rect and start_rect.collidepoint(mx, my):
                        reset_game()
                        game_state = STATE_PLAYING
                    for i, (bx, by, bw, bh) in enumerate(diff_rects):
                        if pygame.Rect(bx, by, bw, bh).collidepoint(mx, my):
                            difficulty = diff_names[i]
                            diff = DIFFICULTIES[difficulty]
                elif game_state == STATE_GAMEOVER:
                    if again_rect and again_rect.collidepoint(mx, my):
                        reset_game()
                        game_state = STATE_PLAYING
                elif game_state == STATE_PAUSED:
                    if resume_rect and resume_rect.collidepoint(mx, my):
                        game_state = STATE_PLAYING
                        slice_trail.clear()

            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                mouse_down = False

            if event.type == pygame.MOUSEMOTION and mouse_down and game_state == STATE_PLAYING:
                mx, my = event.pos
                finger_pos = (mx, my)
                add_trail(mx, my)

        # ── Update ───────────────────────────────────────────────────
        if hands_det is not None:
            with _cam_lock:
                frame_to_process = _cam_frame.copy() if _cam_frame is not None else None
            
            if frame_to_process is not None:
                rgb = cv2.cvtColor(frame_to_process, cv2.COLOR_BGR2RGB)
                mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
                res = hands_det.detect(mp_image)

                if res.hand_landmarks:
                    lm = res.hand_landmarks[0]
                    cx = lm[8].x * W
                    cy = lm[8].y * H

                    last_finger = finger_pos if finger_pos else (cx, cy)
                    finger_pos  = (cx, cy)

                    if game_state == STATE_PLAYING:
                        add_trail(cx, cy)

                    if is_fist(lm):
                        gesture_fist_hold += 1
                        gesture_open_hold  = 0
                        if gesture_fist_hold == GESTURE_THRESH and game_state == STATE_PLAYING:
                            game_state = STATE_PAUSED
                    else:
                        gesture_fist_hold = 0

                    if is_open_hand(lm):
                        gesture_open_hold += 1
                        gesture_fist_hold  = 0
                        if gesture_open_hold == GESTURE_THRESH:
                            if game_state == STATE_PAUSED:
                                game_state = STATE_PLAYING
                                slice_trail.clear()
                            elif game_state == STATE_GAMEOVER:
                                reset_game()
                                game_state = STATE_PLAYING
                                slice_trail.clear()
                    else:
                        gesture_open_hold = 0
                else:
                    finger_pos        = None
                    gesture_fist_hold = 0
                    gesture_open_hold = 0
        if game_state == STATE_PLAYING:
            # Combo timer
            if combo_timer > 0:
                combo_timer -= dt
            else:
                combo = 0

            # Spawn fruits
            spawn_timer += dt
            active = [f for f in fruits if not f.sliced]
            if spawn_timer >= diff['spawn_rate'] and len(active) < diff['max_fruits']:
                fruits.append(Fruit())
                spawn_timer = 0.0

            # Update fruits
            for f in fruits:
                f.update(dt)

            # Missed fruits
            missed = 0
            new_fruits = []
            for f in fruits:
                if not f.sliced and f.off_screen():
                    if not f.is_bomb:
                        missed += 1
                elif f.sliced and f.opacity <= 0:
                    pass
                else:
                    new_fruits.append(f)
            fruits = new_fruits
            for _ in range(missed):
                handle_miss()

            # Slice check
            check_slice()

            # Update particles
            for p in particles:
                p.update(dt)
            particles[:] = [p for p in particles if p.life > 0]

        # ── Draw ─────────────────────────────────────────────────────
        draw_background(screen)

        if game_state == STATE_PLAYING:
            sx, sy = get_shake()
            game_surf = pygame.Surface((W, H), pygame.SRCALPHA)
            for f in fruits:
                f.draw(game_surf)
            for p in particles:
                p.draw(game_surf)
            draw_trail(game_surf)
            screen.blit(game_surf, (int(sx), int(sy)))
            draw_hud(screen)

        elif game_state == STATE_MENU:
            start_rect, diff_names, diff_rects = draw_menu(screen)

        elif game_state == STATE_PAUSED:
            for f in fruits:
                f.draw(screen)
            draw_hud(screen)
            resume_rect = draw_paused(screen)

        elif game_state == STATE_GAMEOVER:
            again_rect = draw_gameover(screen)

        pygame.display.flip()

if __name__ == "__main__":
    main()