#!/usr/bin/env python3
"""
╔══════════════════════════════════════╗
║   DUNGEON OF ETERNAL DARKNESS        ║
║   A Terminal Roguelike Adventure     ║
╚══════════════════════════════════════╝
Controls: WASD / Arrow Keys to move
          . or SPACE to wait
          i = inventory   g = grab item
          d = drop item   > = descend stairs
          q = quit        ? = help
"""

import curses
import random
import math
import sys
from collections import deque

# ─────────────────────────────────────────
#  CONSTANTS
# ─────────────────────────────────────────
MAP_W, MAP_H     = 80, 40
PANEL_H          = 8
MIN_ROOM, MAX_ROOM = 6, 14
MAX_ROOMS        = 18
MAX_FLOOR        = 7
FOV_RADIUS       = 10

# Color pair IDs
C_WALL    = 1
C_FLOOR   = 2
C_PLAYER  = 3
C_ENEMY   = 4
C_ITEM    = 5
C_STAIRS  = 6
C_UI      = 7
C_DAMAGE  = 8
C_HEAL    = 9
C_EXPLORED= 10
C_BOSS    = 11
C_GOLD    = 12
C_DARK    = 13

# ─────────────────────────────────────────
#  UTILITY
# ─────────────────────────────────────────
def clamp(v, lo, hi): return max(lo, min(hi, v))
def dist(a, b): return math.sqrt((a[0]-b[0])**2 + (a[1]-b[1])**2)

# ─────────────────────────────────────────
#  TILE
# ─────────────────────────────────────────
class Tile:
    __slots__ = ('wall','explored','visible')
    def __init__(self, wall=True):
        self.wall     = wall
        self.explored = False
        self.visible  = False

# ─────────────────────────────────────────
#  ITEMS
# ─────────────────────────────────────────
ITEM_DEFS = {
    'health_potion':  {'name':'Health Potion',   'char':'!', 'color':C_HEAL,  'weight':1},
    'mana_potion':    {'name':'Mana Potion',      'char':'!', 'color':C_ITEM,  'weight':1},
    'sword':          {'name':'Iron Sword',       'char':'/', 'color':C_ITEM,  'weight':3},
    'great_sword':    {'name':'Great Sword',      'char':'/', 'color':C_BOSS,  'weight':5},
    'shield':         {'name':'Wooden Shield',    'char':'[', 'color':C_ITEM,  'weight':3},
    'iron_shield':    {'name':'Iron Shield',      'char':'[', 'color':C_BOSS,  'weight':4},
    'leather_armor':  {'name':'Leather Armor',    'char':']', 'color':C_ITEM,  'weight':4},
    'chain_mail':     {'name':'Chain Mail',       'char':']', 'color':C_BOSS,  'weight':6},
    'fire_scroll':    {'name':'Fire Scroll',      'char':'?', 'color':C_DAMAGE,'weight':1},
    'lightning_scroll':{'name':'Lightning Scroll','char':'?', 'color':C_ITEM,  'weight':1},
    'gold_coin':      {'name':'Gold Coins',       'char':'$', 'color':C_GOLD,  'weight':0},
}

ITEM_EFFECTS = {
    'health_potion':   {'heal': 30},
    'mana_potion':     {'mana': 20},
    'sword':           {'atk': 4},
    'great_sword':     {'atk': 9},
    'shield':          {'def': 3},
    'iron_shield':     {'def': 6},
    'leather_armor':   {'def': 4},
    'chain_mail':      {'def': 8},
    'fire_scroll':     {'damage': 25, 'radius': 3},
    'lightning_scroll':{'damage': 40, 'radius': 1},
    'gold_coin':       {'gold': 10},
}

class Item:
    def __init__(self, kind, x, y, amount=1):
        self.kind   = kind
        self.x, self.y = x, y
        self.amount = amount
        d = ITEM_DEFS[kind]
        self.name  = d['name']
        self.char  = d['char']
        self.color = d['color']
        if kind == 'gold_coin':
            self.name = f"{amount} Gold"

# ─────────────────────────────────────────
#  ENTITIES
# ─────────────────────────────────────────
ENEMY_DEFS = {
    'rat':    {'name':'Rat',       'char':'r','color':C_ENEMY,'hp':8, 'atk':3,'def':0,'xp':5, 'speed':1},
    'goblin': {'name':'Goblin',    'char':'g','color':C_ENEMY,'hp':16,'atk':5,'def':1,'xp':12,'speed':1},
    'orc':    {'name':'Orc',       'char':'o','color':C_ENEMY,'hp':28,'atk':8,'def':3,'xp':25,'speed':1},
    'troll':  {'name':'Troll',     'char':'T','color':C_ENEMY,'hp':45,'atk':12,'def':5,'xp':50,'speed':1,'regen':1},
    'vampire':{'name':'Vampire',   'char':'V','color':C_BOSS, 'hp':35,'atk':10,'def':4,'xp':60,'speed':2,'drain':3},
    'dragon': {'name':'Dragon',    'char':'D','color':C_BOSS, 'hp':80,'atk':18,'def':8,'xp':120,'speed':1,'breath':15},
    'lich':   {'name':'LICH KING', 'char':'L','color':C_BOSS, 'hp':150,'atk':22,'def':12,'xp':500,'speed':1,'curse':True,'boss':True},
}

FLOOR_ENEMIES = {
    1: ['rat','rat','goblin'],
    2: ['rat','goblin','goblin','orc'],
    3: ['goblin','orc','orc'],
    4: ['orc','orc','troll'],
    5: ['orc','troll','troll','vampire'],
    6: ['troll','vampire','dragon'],
    7: ['dragon','dragon','lich'],
}

class Entity:
    def __init__(self, kind, x, y):
        self.kind = kind
        self.x, self.y = x, y
        d = ENEMY_DEFS[kind]
        self.name    = d['name']
        self.char    = d['char']
        self.color   = d['color']
        self.max_hp  = d['hp']
        self.hp      = d['hp']
        self.atk     = d['atk']
        self.defense = d['def']
        self.xp      = d['xp']
        self.speed   = d.get('speed',1)
        self.regen   = d.get('regen',0)
        self.drain   = d.get('drain',0)
        self.breath  = d.get('breath',0)
        self.boss    = d.get('boss',False)
        self.curse   = d.get('curse',False)
        self.turn_acc= 0
        self.path    = []
        self.stunned = 0

    def alive(self): return self.hp > 0

# ─────────────────────────────────────────
#  PLAYER
# ─────────────────────────────────────────
class Player:
    def __init__(self, x, y):
        self.x, self.y  = x, y
        self.char        = '●'
        self.max_hp      = 80
        self.hp          = 80
        self.max_mp      = 30
        self.mp          = 30
        self.base_atk    = 6
        self.base_def    = 2
        self.level       = 1
        self.xp          = 0
        self.xp_next     = 30
        self.gold        = 0
        self.inventory   = []
        self.equipped    = {'weapon': None, 'armor': None, 'shield': None}
        self.floor       = 1
        self.kills       = 0
        self.cursed      = 0   # turns remaining
        self.steps       = 0

    @property
    def atk(self):
        bonus = 0
        if self.equipped['weapon']:
            bonus += ITEM_EFFECTS[self.equipped['weapon']].get('atk',0)
        if self.cursed > 0: bonus = max(0, bonus - 4)
        return self.base_atk + bonus

    @property
    def defense(self):
        bonus = 0
        for slot in ('armor','shield'):
            if self.equipped[slot]:
                bonus += ITEM_EFFECTS[self.equipped[slot]].get('def',0)
        return self.base_def + bonus

    def gain_xp(self, amount):
        self.xp += amount
        leveled = []
        while self.xp >= self.xp_next:
            self.xp    -= self.xp_next
            self.level += 1
            self.xp_next = int(self.xp_next * 1.6)
            self.max_hp += 12
            self.hp     = min(self.hp + 20, self.max_hp)
            self.max_mp += 5
            self.base_atk += 1
            self.base_def += 1
            leveled.append(self.level)
        return leveled

    def equip(self, item_kind):
        fx = ITEM_EFFECTS.get(item_kind, {})
        if 'atk' in fx:    slot = 'weapon'
        elif 'def' in fx:
            if item_kind in ('shield','iron_shield'): slot = 'shield'
            else: slot = 'armor'
        else: return False
        self.equipped[slot] = item_kind
        return True

# ─────────────────────────────────────────
#  MAP GENERATOR
# ─────────────────────────────────────────
class Room:
    def __init__(self, x, y, w, h):
        self.x1, self.y1 = x, y
        self.x2, self.y2 = x+w, y+h
    def center(self): return ((self.x1+self.x2)//2, (self.y1+self.y2)//2)
    def intersects(self, other):
        return self.x1 <= other.x2+1 and self.x2 >= other.x1-1 \
           and self.y1 <= other.y2+1 and self.y2 >= other.y1-1

def generate_map(floor_num):
    tiles = [[Tile(True) for _ in range(MAP_H)] for _ in range(MAP_W)]
    rooms = []

    def carve(x1,y1,x2,y2):
        for x in range(x1, x2):
            for y in range(y1, y2):
                if 0 <= x < MAP_W and 0 <= y < MAP_H:
                    tiles[x][y].wall = False

    def h_tunnel(x1,x2,y):
        carve(min(x1,x2), y, max(x1,x2)+1, y+1)
    def v_tunnel(x,y1,y2):
        carve(x, min(y1,y2), x+1, max(y1,y2)+1)

    attempts = 0
    while len(rooms) < MAX_ROOMS and attempts < 300:
        attempts += 1
        w = random.randint(MIN_ROOM, MAX_ROOM)
        h = random.randint(MIN_ROOM-1, MAX_ROOM-1)
        x = random.randint(1, MAP_W - w - 2)
        y = random.randint(1, MAP_H - h - 2)
        r = Room(x, y, w, h)
        if any(r.intersects(other) for other in rooms): continue
        carve(r.x1, r.y1, r.x2, r.y2)
        if rooms:
            prev_cx, prev_cy = rooms[-1].center()
            cx, cy = r.center()
            if random.random() < 0.5:
                h_tunnel(prev_cx, cx, prev_cy)
                v_tunnel(cx, prev_cy, cy)
            else:
                v_tunnel(prev_cx, prev_cy, cy)
                h_tunnel(prev_cx, cx, cy)
        rooms.append(r)

    # Stairs
    sx, sy = rooms[-1].center()
    stairs = (sx, sy)

    # Populate entities
    entities = []
    enemy_pool = FLOOR_ENEMIES.get(floor_num, FLOOR_ENEMIES[6])
    num_enemies = 3 + floor_num * 2
    boss_placed = False

    for room in rooms[1:]:
        n = random.randint(0, 3)
        for _ in range(n):
            if len(entities) >= num_enemies: break
            kind = random.choice(enemy_pool)
            # Place boss on last floor in last room
            if floor_num == MAX_FLOOR and not boss_placed and room == rooms[-1]:
                kind = 'lich'
                boss_placed = True
            ex = random.randint(room.x1+1, room.x2-1)
            ey = random.randint(room.y1+1, room.y2-1)
            if not tiles[ex][ey].wall and (ex,ey) != stairs:
                entities.append(Entity(kind, ex, ey))
        if len(entities) >= num_enemies: break

    if floor_num == MAX_FLOOR and not boss_placed:
        lx, ly = rooms[-1].center()
        entities.append(Entity('lich', lx-1, ly))
        boss_placed = True

    # Items
    items = []
    item_chances = [
        ('health_potion', 35),
        ('mana_potion', 15),
        ('gold_coin', 25),
        ('sword', 8 if floor_num < 4 else 3),
        ('great_sword', 3 if floor_num >= 4 else 0),
        ('shield', 6 if floor_num < 3 else 2),
        ('iron_shield', 4 if floor_num >= 3 else 0),
        ('leather_armor', 5 if floor_num < 4 else 2),
        ('chain_mail', 4 if floor_num >= 4 else 0),
        ('fire_scroll', 5 if floor_num >= 2 else 0),
        ('lightning_scroll', 4 if floor_num >= 3 else 0),
    ]
    total_weight = sum(w for _,w in item_chances if w > 0)
    num_items = 3 + floor_num
    for room in rooms[1:]:
        if random.random() < 0.6:
            roll = random.randint(1, total_weight)
            acc = 0
            chosen = 'health_potion'
            for kind, w in item_chances:
                if w <= 0: continue
                acc += w
                if roll <= acc:
                    chosen = kind
                    break
            ix = random.randint(room.x1+1, room.x2-1)
            iy = random.randint(room.y1+1, room.y2-1)
            if not tiles[ix][iy].wall:
                amount = random.randint(5,25)*floor_num if chosen=='gold_coin' else 1
                items.append(Item(chosen, ix, iy, amount))

    start = rooms[0].center()
    return tiles, rooms, entities, items, stairs, start

# ─────────────────────────────────────────
#  FOV (Shadowcasting)
# ─────────────────────────────────────────
def compute_fov(tiles, px, py, radius):
    for col in tiles:
        for t in col:
            t.visible = False
    tiles[px][py].visible   = True
    tiles[px][py].explored  = True

    for octant in range(8):
        _cast_light(tiles, px, py, radius, 1, 1.0, 0.0, octant)

TRANSFORMS = [
    (1,0,0,-1),(0,1,-1,0),(-1,0,0,-1),(0,-1,-1,0),
    (-1,0,0,1),(0,-1,1,0),(1,0,0,1),(0,1,1,0),
]

def _cast_light(tiles, cx, cy, radius, row, start_slope, end_slope, octant):
    if start_slope < end_slope: return
    xx,xy,yx,yy = TRANSFORMS[octant]
    next_start = start_slope
    blocked = False
    for j in range(row, radius+1):
        if blocked: break
        dy = -j
        for dx in range(-j, 1):
            lslope = (dx - 0.5) / (dy + 0.5)
            rslope = (dx + 0.5) / (dy - 0.5)
            if start_slope < rslope: continue
            if end_slope > lslope: break
            ax = cx + dx*xx + dy*xy
            ay = cy + dx*yx + dy*yy
            if 0 <= ax < MAP_W and 0 <= ay < MAP_H:
                if dist((cx,cy),(ax,ay)) <= radius:
                    tiles[ax][ay].visible  = True
                    tiles[ax][ay].explored = True
            is_wall = not(0 <= ax < MAP_W and 0 <= ay < MAP_H) or tiles[ax][ay].wall
            if blocked:
                if is_wall: next_start = rslope
                else:
                    blocked = False
                    start_slope = next_start
            else:
                if is_wall and j < radius:
                    blocked = True
                    _cast_light(tiles, cx, cy, radius, j+1, start_slope, lslope, octant)
                    next_start = rslope
    blocked = True

# ─────────────────────────────────────────
#  PATHFINDING (BFS)
# ─────────────────────────────────────────
def bfs_path(tiles, sx, sy, ex, ey, entities, max_dist=15):
    if dist((sx,sy),(ex,ey)) > max_dist: return []
    blocked = {(e.x,e.y) for e in entities if e.alive() and (e.x,e.y)!=(ex,ey)}
    visited = {(sx,sy)}
    parent  = {(sx,sy): None}
    q = deque([(sx,sy)])
    while q:
        x,y = q.popleft()
        if (x,y) == (ex,ey):
            path = []
            node = (ex,ey)
            while parent[node]: path.append(node); node = parent[node]
            return list(reversed(path))
        for dx,dy in [(-1,0),(1,0),(0,-1),(0,1)]:
            nx,ny = x+dx,y+dy
            if 0<=nx<MAP_W and 0<=ny<MAP_H and not tiles[nx][ny].wall \
               and (nx,ny) not in visited and (nx,ny) not in blocked:
                visited.add((nx,ny)); parent[(nx,ny)] = (x,y); q.append((nx,ny))
    return []

# ─────────────────────────────────────────
#  COMBAT
# ─────────────────────────────────────────
def calc_damage(atk, defense):
    dmg = atk - defense//2
    dmg = max(1, dmg + random.randint(-2, 3))
    return dmg

# ─────────────────────────────────────────
#  GAME ENGINE
# ─────────────────────────────────────────
class Game:
    def __init__(self, stdscr):
        self.scr     = stdscr
        self.messages= deque(maxlen=7)
        self.running = True
        self.won     = False
        self.turn    = 0
        self.mode    = 'play'   # 'play','inventory','help','dead','win'
        self.inv_sel = 0
        self._init_colors()
        self._new_game()

    def _init_colors(self):
        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(C_WALL,    curses.COLOR_WHITE,   -1)
        curses.init_pair(C_FLOOR,   curses.COLOR_WHITE,   -1)
        curses.init_pair(C_PLAYER,  curses.COLOR_CYAN,    -1)
        curses.init_pair(C_ENEMY,   curses.COLOR_RED,     -1)
        curses.init_pair(C_ITEM,    curses.COLOR_YELLOW,  -1)
        curses.init_pair(C_STAIRS,  curses.COLOR_MAGENTA, -1)
        curses.init_pair(C_UI,      curses.COLOR_WHITE,   -1)
        curses.init_pair(C_DAMAGE,  curses.COLOR_RED,     -1)
        curses.init_pair(C_HEAL,    curses.COLOR_GREEN,   -1)
        curses.init_pair(C_EXPLORED,curses.COLOR_WHITE,   -1)
        curses.init_pair(C_BOSS,    curses.COLOR_MAGENTA, -1)
        curses.init_pair(C_GOLD,    curses.COLOR_YELLOW,  -1)
        curses.init_pair(C_DARK,    curses.COLOR_BLACK,   -1)

    def _new_game(self):
        self.player  = None
        self._load_floor(1, is_start=True)

    def _load_floor(self, floor_num, is_start=False):
        self.tiles, self.rooms, self.entities, self.items, self.stairs, start = \
            generate_map(floor_num)
        if is_start:
            self.player = Player(start[0], start[1])
        else:
            self.player.x, self.player.y = start
            self.player.floor = floor_num
        compute_fov(self.tiles, self.player.x, self.player.y, FOV_RADIUS)
        if is_start:
            self.msg("Welcome to the Dungeon of Eternal Darkness!", C_HEAL)
            self.msg("Find the LICH KING on floor 7 and destroy him!", C_BOSS)
        else:
            self.msg(f"You descend to floor {floor_num}. The air grows colder...", C_ITEM)
            if floor_num == MAX_FLOOR:
                self.msg("You sense an overwhelming evil presence nearby...", C_BOSS)

    def msg(self, text, color=C_UI):
        self.messages.append((text, color))

    # ── INPUT ──────────────────────────────
    def handle_input(self):
        key = self.scr.getch()
        if self.mode == 'play':
            return self._play_input(key)
        elif self.mode == 'inventory':
            return self._inv_input(key)
        elif self.mode in ('dead','win'):
            if key in (ord('q'), ord('Q'), 27): self.running = False
            elif key == ord('r'): self._new_game(); self.mode = 'play'
            return False
        elif self.mode == 'help':
            self.mode = 'play'
            return False
        return False

    def _play_input(self, key):
        p = self.player
        dx, dy = 0, 0
        acted = False

        if   key in (ord('w'), curses.KEY_UP):    dx, dy =  0,-1; acted=True
        elif key in (ord('s'), curses.KEY_DOWN):   dx, dy =  0, 1; acted=True
        elif key in (ord('a'), curses.KEY_LEFT):   dx, dy = -1, 0; acted=True
        elif key in (ord('d'), curses.KEY_RIGHT):  dx, dy =  1, 0; acted=True
        elif key in (ord('y'),):                   dx, dy = -1,-1; acted=True
        elif key in (ord('u'),):                   dx, dy =  1,-1; acted=True
        elif key in (ord('b'),):                   dx, dy = -1, 1; acted=True
        elif key in (ord('n'),):                   dx, dy =  1, 1; acted=True
        elif key in (ord('.'), ord(' ')):           acted=True  # wait
        elif key == ord('i'):  self.mode='inventory'; return False
        elif key == ord('g'):  self._grab(); return False
        elif key == ord('>'):  self._try_descend(); return False
        elif key == ord('?'):  self.mode='help'; return False
        elif key in (ord('q'),ord('Q')): self.running=False; return False

        if acted and (dx or dy):
            self._try_move(dx, dy)
        elif acted:
            p.hp = min(p.max_hp, p.hp + 1)  # wait = minor regen
        return acted

    def _try_move(self, dx, dy):
        p = self.player
        nx, ny = p.x + dx, p.y + dy
        if not (0 <= nx < MAP_W and 0 <= ny < MAP_H): return
        if self.tiles[nx][ny].wall: return

        # Attack enemy?
        for e in self.entities:
            if e.alive() and e.x == nx and e.y == ny:
                self._player_attack(e)
                return

        p.x, p.y = nx, ny
        p.steps += 1
        if p.cursed > 0: p.cursed -= 1

        # Auto-heal
        if p.steps % 10 == 0 and p.hp < p.max_hp:
            p.hp = min(p.max_hp, p.hp + 2)

        compute_fov(self.tiles, p.x, p.y, FOV_RADIUS)

    def _player_attack(self, enemy):
        p = self.player
        dmg = calc_damage(p.atk, enemy.defense)
        enemy.hp -= dmg
        self.msg(f"You hit {enemy.name} for {dmg} damage!", C_DAMAGE)
        if not enemy.alive():
            lvls = p.gain_xp(enemy.xp)
            p.kills += 1
            self.msg(f"{enemy.name} dies! +{enemy.xp} XP", C_ITEM)
            for lv in lvls:
                self.msg(f"★ LEVEL UP! You are now level {lv}! ★", C_BOSS)
            if enemy.boss:
                self.won = True
                self.mode = 'win'

    def _enemy_turn(self):
        p = self.player
        for e in self.entities:
            if not e.alive(): continue
            if e.stunned > 0:
                e.stunned -= 1
                continue
            if e.regen and e.hp < e.max_hp:
                e.hp = min(e.max_hp, e.hp + e.regen)

            see_player = self.tiles[e.x][e.y].visible
            d = dist((e.x,e.y),(p.x,p.y))

            if d <= 1.5:  # Adjacent: attack
                dmg = calc_damage(e.atk, p.defense)
                p.hp -= dmg
                if e.drain:
                    p.hp -= e.drain
                    e.hp  = min(e.max_hp, e.hp + e.drain)
                    self.msg(f"{e.name} drains your life for {dmg+e.drain}!", C_DAMAGE)
                elif e.breath and random.random() < 0.3:
                    p.hp -= e.breath
                    self.msg(f"{e.name} breathes fire for {dmg+e.breath}!", C_DAMAGE)
                elif e.curse and random.random() < 0.25:
                    p.cursed = 15
                    self.msg(f"{e.name} curses you! Your attacks weaken!", C_BOSS)
                    self.msg(f"{e.name} hits you for {dmg}!", C_DAMAGE)
                else:
                    self.msg(f"{e.name} hits you for {dmg}!", C_DAMAGE)

                if p.hp <= 0:
                    p.hp = 0
                    self.mode = 'dead'
                    return

            elif see_player or d < 8:  # Chase
                path = bfs_path(self.tiles, e.x, e.y, p.x, p.y, self.entities)
                if path:
                    tx, ty = path[0]
                    occupied = any(o.alive() and o.x==tx and o.y==ty for o in self.entities if o is not e)
                    if not occupied:
                        e.x, e.y = tx, ty
                        if e.speed == 2 and len(path) > 1:
                            tx2, ty2 = path[1] if len(path)>1 else (tx,ty)
                            occ2 = any(o.alive() and o.x==tx2 and o.y==ty2 for o in self.entities if o is not e)
                            if not occ2 and (tx2,ty2)!=(p.x,p.y):
                                e.x,e.y=tx2,ty2

    def _grab(self):
        p = self.player
        for item in self.items[:]:
            if item.x == p.x and item.y == p.y:
                if item.kind == 'gold_coin':
                    p.gold += item.amount
                    self.msg(f"Picked up {item.name}!", C_GOLD)
                    self.items.remove(item)
                elif len(p.inventory) < 12:
                    p.inventory.append(item)
                    self.items.remove(item)
                    self.msg(f"Picked up {item.name}.", C_ITEM)
                else:
                    self.msg("Your inventory is full (12 items max)!", C_DAMAGE)
                return
        self.msg("Nothing to pick up here.", C_UI)

    def _try_descend(self):
        p = self.player
        if (p.x, p.y) == self.stairs:
            if p.floor >= MAX_FLOOR:
                self.msg("You cannot go deeper. Face your destiny here!", C_BOSS)
            else:
                self._load_floor(p.floor + 1)
        else:
            self.msg("There are no stairs here.", C_UI)

    def _use_item(self, idx):
        p = self.player
        if idx >= len(p.inventory): return
        item = p.inventory[idx]
        fx = ITEM_EFFECTS.get(item.kind, {})

        if 'heal' in fx:
            healed = min(fx['heal'], p.max_hp - p.hp)
            p.hp += healed
            self.msg(f"You drink the potion. Healed {healed} HP!", C_HEAL)
            p.inventory.pop(idx)
        elif 'mana' in fx:
            gained = min(fx['mana'], p.max_mp - p.mp)
            p.mp += gained
            self.msg(f"You drink the mana potion. +{gained} MP!", C_ITEM)
            p.inventory.pop(idx)
        elif 'damage' in fx:
            radius  = fx.get('radius', 1)
            damage  = fx['damage']
            targets = [e for e in self.entities if e.alive() and dist((p.x,p.y),(e.x,e.y)) <= FOV_RADIUS
                       and self.tiles[e.x][e.y].visible]
            if not targets:
                self.msg("No visible enemies to target!", C_UI)
                return
            # Hit closest enemy (and splash)
            targets.sort(key=lambda e: dist((p.x,p.y),(e.x,e.y)))
            hit = []
            for e in self.entities:
                if e.alive() and dist((targets[0].x,targets[0].y),(e.x,e.y)) <= radius:
                    e.hp -= damage
                    hit.append(e.name)
                    if not e.alive():
                        lvls = p.gain_xp(e.xp); p.kills+=1
                        for lv in lvls: self.msg(f"★ LEVEL UP! Level {lv}! ★", C_BOSS)
            self.msg(f"Scroll ignites! {', '.join(hit)} take {damage} damage!", C_DAMAGE)
            p.inventory.pop(idx)
        elif 'atk' in fx or 'def' in fx:
            if p.equip(item.kind):
                p.inventory.pop(idx)
                self.msg(f"You equip {item.name}.", C_ITEM)
            else:
                self.msg(f"Can't equip that.", C_UI)
        self.inv_sel = min(self.inv_sel, max(0, len(p.inventory)-1))

    def _drop_item(self, idx):
        p = self.player
        if idx >= len(p.inventory): return
        item = p.inventory.pop(idx)
        item.x, item.y = p.x, p.y
        self.items.append(item)
        self.msg(f"Dropped {item.name}.", C_UI)
        self.inv_sel = min(self.inv_sel, max(0, len(p.inventory)-1))

    def _inv_input(self, key):
        p = self.player
        n = len(p.inventory)
        if key in (ord('i'), 27, ord('q')): self.mode = 'play'
        elif key == curses.KEY_UP:   self.inv_sel = (self.inv_sel-1)%max(1,n)
        elif key == curses.KEY_DOWN: self.inv_sel = (self.inv_sel+1)%max(1,n)
        elif key in (ord('\n'), ord('u'), ord('e'), curses.KEY_ENTER):
            self._use_item(self.inv_sel)
        elif key == ord('d'):
            self._drop_item(self.inv_sel)
        return False

    # ── TICK ───────────────────────────────
    def tick(self):
        self.turn += 1
        self._enemy_turn()
        self.entities = [e for e in self.entities if e.alive() or True]

    # ── RENDER ─────────────────────────────
    def render(self):
        self.scr.erase()
        h, w = self.scr.getmaxyx()
        if self.mode == 'dead':
            self._render_death(h, w); return
        if self.mode == 'win':
            self._render_win(h, w); return
        if self.mode == 'help':
            self._render_help(h, w); return
        if self.mode == 'inventory':
            self._render_inventory(h, w); return

        # Map
        p = self.player
        view_x = clamp(p.x - w//2, 0, max(0, MAP_W - w))
        view_y = clamp(p.y - (h - PANEL_H)//2, 0, max(0, MAP_H - (h - PANEL_H)))

        for sx in range(min(w, MAP_W)):
            for sy in range(min(h - PANEL_H, MAP_H)):
                mx, my = sx + view_x, sy + view_y
                if not (0 <= mx < MAP_W and 0 <= my < MAP_H): continue
                tile = self.tiles[mx][my]
                if not tile.explored: continue

                if tile.visible:
                    if tile.wall:
                        self._draw(sy, sx, '▓', curses.color_pair(C_WALL) | curses.A_DIM)
                    else:
                        self._draw(sy, sx, ' ', curses.color_pair(C_FLOOR) | curses.A_DIM)
                else:
                    ch = '▓' if tile.wall else ' '
                    self._draw(sy, sx, ch, curses.color_pair(C_EXPLORED) | curses.A_DIM)

        # Stairs
        sx2, sy2 = self.stairs[0]-view_x, self.stairs[1]-view_y
        if 0<=sx2<w and 0<=sy2<h-PANEL_H and self.tiles[self.stairs[0]][self.stairs[1]].visible:
            self._draw(sy2, sx2, '▼', curses.color_pair(C_STAIRS) | curses.A_BOLD)

        # Items
        for item in self.items:
            ix, iy = item.x - view_x, item.y - view_y
            if 0<=ix<w and 0<=iy<h-PANEL_H and self.tiles[item.x][item.y].visible:
                self._draw(iy, ix, item.char, curses.color_pair(item.color) | curses.A_BOLD)

        # Entities
        for e in self.entities:
            if not e.alive(): continue
            ex, ey = e.x - view_x, e.y - view_y
            if 0<=ex<w and 0<=ey<h-PANEL_H and self.tiles[e.x][e.y].visible:
                attr = curses.color_pair(e.color) | curses.A_BOLD
                if e.boss: attr |= curses.A_BLINK
                self._draw(ey, ex, e.char, attr)

        # Player
        px, py = p.x - view_x, p.y - view_y
        if 0<=px<w and 0<=py<h-PANEL_H:
            self._draw(py, px, '●', curses.color_pair(C_PLAYER) | curses.A_BOLD)

        # HUD
        self._render_hud(h, w)
        self.scr.refresh()

    def _draw(self, y, x, ch, attr):
        try:
            self.scr.addch(y, x, ch, attr)
        except curses.error:
            pass

    def _draw_str(self, y, x, s, attr=0):
        try:
            self.scr.addstr(y, x, s, attr)
        except curses.error:
            pass

    def _render_hud(self, h, w):
        p   = self.player
        top = h - PANEL_H

        # Separator
        self._draw_str(top, 0, '─' * w, curses.color_pair(C_WALL) | curses.A_DIM)
        top += 1

        # HP / MP bars
        def bar(val, mx, width=20):
            filled = int(val / mx * width) if mx else 0
            return '█' * filled + '░' * (width - filled)

        hp_col = C_HEAL if p.hp > p.max_hp*0.5 else (C_ITEM if p.hp > p.max_hp*0.25 else C_DAMAGE)
        self._draw_str(top, 0, f" HP [{bar(p.hp,p.max_hp)}] {p.hp:>3}/{p.max_hp:<3}", curses.color_pair(hp_col))
        self._draw_str(top, 36, f"MP [{bar(p.mp,p.max_mp,12)}] {p.mp}/{p.max_mp}", curses.color_pair(C_ITEM))
        if p.cursed > 0:
            self._draw_str(top, 62, f"  ☠ CURSED ({p.cursed})", curses.color_pair(C_BOSS) | curses.A_BOLD)

        top += 1
        wp  = p.equipped.get('weapon') or '—'
        arm = p.equipped.get('armor')  or p.equipped.get('shield') or '—'
        if isinstance(wp, str) and wp != '—':  wp  = ITEM_DEFS[wp]['name']
        if isinstance(arm, str) and arm != '—': arm = ITEM_DEFS[arm]['name']
        self._draw_str(top, 0,
            f" Lv:{p.level}  XP:{p.xp}/{p.xp_next}  ATK:{p.atk}  DEF:{p.defense}"
            f"  Gold:{p.gold}  Floor:{p.floor}/{MAX_FLOOR}  Kills:{p.kills}",
            curses.color_pair(C_UI))
        top += 1
        self._draw_str(top, 0, f" Weapon: {wp[:22]}   Armor: {arm[:22]}", curses.color_pair(C_ITEM))
        top += 1

        # Messages
        msgs = list(self.messages)
        for i, (txt, col) in enumerate(msgs[-4:]):
            fade = curses.A_DIM if i < len(msgs)-4 else 0
            self._draw_str(top + i, 1, txt[:w-2], curses.color_pair(col) | fade)

        # Mini status bar
        self._draw_str(h-1, 0,
            " [WASD]Move [i]Inv [g]Grab [>]Stairs [.]Wait [?]Help [q]Quit",
            curses.color_pair(C_WALL) | curses.A_DIM)

    def _render_inventory(self, h, w):
        p  = self.player
        bw = min(50, w - 4)
        bh = min(22, h - 4)
        bx = (w - bw) // 2
        by = (h - bh) // 2

        # Draw box
        self._draw_str(by, bx, '┌' + '─'*(bw-2) + '┐', curses.color_pair(C_UI) | curses.A_BOLD)
        for row in range(1, bh-1):
            self._draw_str(by+row, bx, '│' + ' '*(bw-2) + '│', curses.color_pair(C_UI))
        self._draw_str(by+bh-1, bx, '└' + '─'*(bw-2) + '┘', curses.color_pair(C_UI) | curses.A_BOLD)

        title = "  ══ INVENTORY ══  "
        self._draw_str(by, bx+2, title, curses.color_pair(C_BOSS) | curses.A_BOLD)
        self._draw_str(by+1, bx+2, f"Gold: {p.gold}  Items: {len(p.inventory)}/12",
                       curses.color_pair(C_GOLD))

        if not p.inventory:
            self._draw_str(by+3, bx+4, "(Empty inventory)", curses.color_pair(C_WALL))
        else:
            for i, item in enumerate(p.inventory[:bh-6]):
                attr = curses.color_pair(item.color)
                prefix = '▶ ' if i == self.inv_sel else '  '
                if i == self.inv_sel: attr |= curses.A_BOLD | curses.A_REVERSE
                equipped = ''
                for slot, kind in p.equipped.items():
                    if kind == item.kind: equipped = f' [E:{slot}]'
                self._draw_str(by+3+i, bx+2, f"{prefix}{i+1}. {item.name}{equipped}"[:bw-4], attr)

        y2 = by + bh - 3
        self._draw_str(y2,   bx+2, "[Enter/U] Use/Equip  [D] Drop  [I/ESC] Close",
                       curses.color_pair(C_WALL) | curses.A_DIM)
        self.scr.refresh()

    def _render_death(self, h, w):
        p = self.player
        lines = [
            "",
            "  ██████╗ ███████╗ █████╗ ██████╗ ",
            "  ██╔══██╗██╔════╝██╔══██╗██╔══██╗",
            "  ██║  ██║█████╗  ███████║██║  ██║",
            "  ██║  ██║██╔══╝  ██╔══██║██║  ██║",
            "  ██████╔╝███████╗██║  ██║██████╔╝",
            "  ╚═════╝ ╚══════╝╚═╝  ╚═╝╚═════╝ ",
            "",
            f"  You perished on Floor {p.floor} at Level {p.level}",
            f"  Kills: {p.kills}   Gold collected: {p.gold}",
            f"  Turns survived: {self.turn}",
            "",
            "  [R] Play Again     [Q] Quit",
        ]
        sy = (h - len(lines)) // 2
        for i, line in enumerate(lines):
            attr = curses.color_pair(C_DAMAGE) | curses.A_BOLD
            self._draw_str(sy+i, max(0,(w-len(line))//2), line, attr)
        self.scr.refresh()

    def _render_win(self, h, w):
        p = self.player
        lines = [
            "",
            " ██╗   ██╗██╗ ██████╗████████╗ ██████╗ ██████╗ ██╗",
            " ██║   ██║██║██╔════╝╚══██╔══╝██╔═══██╗██╔══██╗██║",
            " ██║   ██║██║██║        ██║   ██║   ██║██████╔╝██║",
            " ╚██╗ ██╔╝██║██║        ██║   ██║   ██║██╔══██╗╚═╝",
            "  ╚████╔╝ ██║╚██████╗   ██║   ╚██████╔╝██║  ██║██╗",
            "   ╚═══╝  ╚═╝ ╚═════╝   ╚═╝    ╚═════╝ ╚═╝  ╚═╝╚═╝",
            "",
            " The Lich King has fallen! Light returns to the dungeon!",
            "",
            f" Final Level: {p.level}    Kills: {p.kills}    Gold: {p.gold}",
            f" Turns taken: {self.turn}",
            "",
            " [R] Play Again     [Q] Quit",
        ]
        sy = (h - len(lines)) // 2
        for i, line in enumerate(lines):
            attr = curses.color_pair(C_BOSS) | curses.A_BOLD
            if i == 0 or i >= len(lines)-3:
                attr = curses.color_pair(C_HEAL) | curses.A_BOLD
            self._draw_str(sy+i, max(0,(w-len(line))//2), line, attr)
        self.scr.refresh()

    def _render_help(self, h, w):
        lines = [
            "╔══════════════════════════════════════╗",
            "║         DUNGEON OF ETERNAL DARKNESS         ║",
            "╠══════════════════════════════════════╣",
            "║  WASD / Arrow keys  — Move           ║",
            "║  Y U B N            — Diagonal move  ║",
            "║  . or SPACE         — Wait one turn   ║",
            "║  g                  — Grab item       ║",
            "║  i                  — Open inventory  ║",
            "║  > (on stairs)      — Descend floor   ║",
            "║  q                  — Quit game       ║",
            "╠══════════════════════════════════════╣",
            "║  SYMBOLS:                            ║",
            "║  ●  = You     ▓  = Wall      = Floor ║",
            "║  ▼  = Stairs  !  = Potion ?  = Scroll║",
            "║  /  = Weapon  [  = Shield ]  = Armor ║",
            "║  $  = Gold                           ║",
            "╠══════════════════════════════════════╣",
            "║  TIPS:                               ║",
            "║  • Equip weapons/armor from inventory║",
            "║  • Wait to slowly regenerate HP      ║",
            "║  • The LICH waits on floor 7...      ║",
            "╚══════════════════════════════════════╝",
            "",
            "         Press any key to continue",
        ]
        sy = (h - len(lines)) // 2
        for i, line in enumerate(lines):
            attr = curses.color_pair(C_UI)
            if i in (0,1,2,len(lines)-3): attr = curses.color_pair(C_BOSS) | curses.A_BOLD
            self._draw_str(sy+i, max(0,(w-len(line))//2), line, attr)
        self.scr.refresh()

    # ── MAIN LOOP ──────────────────────────
    def run(self):
        curses.curs_set(0)
        self.scr.nodelay(False)
        self.scr.timeout(100)

        self.render()
        while self.running:
            acted = self.handle_input()
            if acted and self.mode == 'play':
                if self.mode != 'dead' and self.mode != 'win':
                    self.tick()
            self.render()

# ─────────────────────────────────────────
#  ENTRY
# ─────────────────────────────────────────
def main(stdscr):
    game = Game(stdscr)
    game.run()

if __name__ == '__main__':
    try:
        curses.wrapper(main)
    except KeyboardInterrupt:
        pass
    print("\nThanks for playing Dungeon of Eternal Darkness!")
    print("May the light guide your path.\n")
