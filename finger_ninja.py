import pygame
import cv2
import mediapipe as mp
import random
import sys
import math

# Initialize Pygame
pygame.init()

# Setup Screen
WIDTH, HEIGHT = 1000, 700
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Finger Ninja")

# Colors
WHITE = (255, 255, 255)
BLACK = (10, 10, 15)
RED = (255, 56, 96)
YELLOW = (255, 215, 0)
CYAN = (0, 234, 255)
GREEN = (57, 255, 20)
GRAY = (100, 100, 100)

# Fonts
try:
    font = pygame.font.SysFont('Arial', 32, bold=True)
    large_font = pygame.font.SysFont('Arial', 72, bold=True)
except:
    font = pygame.font.Font(None, 32)
    large_font = pygame.font.Font(None, 72)

# Mediapipe setup for hand tracking
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(
    max_num_hands=1,
    min_detection_confidence=0.7,
    min_tracking_confidence=0.7
)

# OpenCV Camera
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("Warning: Could not open webcam.")

# Game Classes
class Fruit:
    def __init__(self):
        self.radius = random.randint(30, 45)
        self.x = random.randint(100, WIDTH - 100)
        self.y = HEIGHT + self.radius
        
        # Determine velocity to throw towards the middle
        target_x = WIDTH / 2
        self.vx = (target_x - self.x) / random.uniform(50, 100) + random.uniform(-2, 2)
        self.vy = random.uniform(-16, -20)
        
        # 0: Apple, 1: Banana, 2: Watermelon, 3: Bomb
        self.type = random.choice([0, 1, 2, 3])
        if self.type == 0:
            self.color = RED
            self.score_val = 10
        elif self.type == 1:
            self.color = YELLOW
            self.score_val = 10
        elif self.type == 2:
            self.color = GREEN
            self.score_val = 20
        elif self.type == 3:
            self.color = GRAY # Bomb
            self.score_val = 0
            self.radius = 35
            
        self.sliced = False
        self.gravity = 0.25

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vy += self.gravity

    def draw(self, surface):
        if self.type == 3: # Draw Bomb
            pygame.draw.circle(surface, self.color, (int(self.x), int(self.y)), self.radius)
            # Fuse
            pygame.draw.line(surface, YELLOW, (int(self.x), int(self.y) - self.radius), (int(self.x) + 15, int(self.y) - self.radius - 15), 4)
            pygame.draw.circle(surface, RED, (int(self.x) + 15, int(self.y) - self.radius - 15), 5)
        else:
            pygame.draw.circle(surface, self.color, (int(self.x), int(self.y)), self.radius)

class Particle:
    def __init__(self, x, y, color):
        self.x = x
        self.y = y
        self.vx = random.uniform(-5, 5)
        self.vy = random.uniform(-5, 5)
        self.radius = random.randint(3, 8)
        self.color = color
        self.life = 255

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vy += 0.2
        self.life -= 10
        self.radius = max(0, self.radius - 0.2)

    def draw(self, surface):
        if self.life > 0 and self.radius > 0:
            surf = pygame.Surface((int(self.radius * 2), int(self.radius * 2)), pygame.SRCALPHA)
            pygame.draw.circle(surf, (*self.color, max(0, int(self.life))), (int(self.radius), int(self.radius)), int(self.radius))
            surface.blit(surf, (int(self.x - self.radius), int(self.y - self.radius)))

def check_slice(x1, y1, x2, y2, cx, cy, r):
    ac_x = cx - x1
    ac_y = cy - y1
    ab_x = x2 - x1
    ab_y = y2 - y1
    ab_length_sq = ab_x**2 + ab_y**2
    if ab_length_sq == 0: return False
    t = (ac_x * ab_x + ac_y * ab_y) / ab_length_sq
    if t < 0:
        closest_x, closest_y = x1, y1
    elif t > 1:
        closest_x, closest_y = x2, y2
    else:
        closest_x = x1 + t * ab_x
        closest_y = y1 + t * ab_y
    dist_sq = (cx - closest_x)**2 + (cy - closest_y)**2
    return dist_sq <= r**2

# Game state
score = 0
lives = 3
fruits = []
particles = []
blade_trail = []
game_over = False

clock = pygame.time.Clock()
spawn_timer = 0
running = True

while running:
    # 1. Event Handling
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False
            if event.key == pygame.K_r and game_over:
                # Reset game
                score = 0
                lives = 3
                fruits.clear()
                particles.clear()
                blade_trail.clear()
                game_over = False

    # 2. Camera & Hand Tracking
    success, image = cap.read()
    current_finger_pos = None
    if success:
        image = cv2.flip(image, 1) # Selfie view
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        results = hands.process(image_rgb)
        
        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                # Index finger tip is landmark 8
                index_finger = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP]
                x = int(index_finger.x * WIDTH)
                y = int(index_finger.y * HEIGHT)
                current_finger_pos = (x, y)
                break # only process one hand

    # 3. Game Logic Update
    if not game_over:
        # Spawn fruits
        spawn_timer += 1
        spawn_rate = max(20, 60 - (score // 50)) # Gets faster as score increases
        if spawn_timer >= spawn_rate:
            fruits.append(Fruit())
            spawn_timer = 0
            if random.random() < 0.3: # 30% chance for multi-spawn
                fruits.append(Fruit())

        # Update Trail
        if current_finger_pos:
            blade_trail.append(current_finger_pos)
            if len(blade_trail) > 15: # Maximum blade length
                blade_trail.pop(0)
        else:
            if len(blade_trail) > 0:
                blade_trail.pop(0) # Shrink trail gracefully

        # Slicing logic
        if len(blade_trail) > 1:
            pt1 = blade_trail[-2]
            pt2 = blade_trail[-1]
            
            for fruit in fruits[:]:
                if not fruit.sliced:
                    if check_slice(pt1[0], pt1[1], pt2[0], pt2[1], fruit.x, fruit.y, fruit.radius):
                        fruit.sliced = True
                        if fruit.type == 3: # Bomb
                            lives = 0
                            # Bomb explosion particles
                            for _ in range(30):
                                particles.append(Particle(fruit.x, fruit.y, RED))
                                particles.append(Particle(fruit.x, fruit.y, YELLOW))
                        else:
                            score += fruit.score_val
                            # Fruit splat particles
                            for _ in range(15):
                                particles.append(Particle(fruit.x, fruit.y, fruit.color))
                        fruits.remove(fruit)

        # Update Fruits
        for fruit in fruits[:]:
            fruit.update()
            if fruit.y > HEIGHT + fruit.radius:
                if not fruit.sliced and fruit.type != 3:
                    lives -= 1
                fruits.remove(fruit)

        # Update Particles
        for p in particles[:]:
            p.update()
            if p.life <= 0:
                particles.remove(p)

        if lives <= 0:
            game_over = True

    # 4. Rendering
    screen.fill(BLACK) # Background

    # Draw Particles
    for p in particles:
        p.draw(screen)

    # Draw Fruits
    for fruit in fruits:
        fruit.draw(screen)

    # Draw Blade Trail
    if len(blade_trail) > 1:
        pygame.draw.lines(screen, CYAN, False, blade_trail, 6)
        pygame.draw.lines(screen, WHITE, False, blade_trail, 2) # Inner core

    # Draw UI
    score_surf = font.render(f"Score: {score}", True, WHITE)
    # Using 'X' for lives if emoji isn't supported in default font
    lives_surf = font.render(f"Lives: {lives}", True, RED) 
    screen.blit(score_surf, (20, 20))
    screen.blit(lives_surf, (WIDTH - lives_surf.get_width() - 20, 20))

    if game_over:
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        screen.blit(overlay, (0, 0))
        
        go_surf = large_font.render("GAME OVER", True, RED)
        restart_surf = font.render("Press 'R' to Restart", True, WHITE)
        
        screen.blit(go_surf, (WIDTH//2 - go_surf.get_width()//2, HEIGHT//2 - 60))
        screen.blit(restart_surf, (WIDTH//2 - restart_surf.get_width()//2, HEIGHT//2 + 40))

    pygame.display.flip()
    clock.tick(60)

cap.release()
pygame.quit()
sys.exit()
