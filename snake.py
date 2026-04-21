import os
import random

# 1. SETUP
width = 25
height = 12
snake = [[5, 5], [5, 4], [5, 3]] 
direction = "d" 
food = [random.randint(1, height-2), random.randint(1, width-2)]
score = 0

def get_snake_char(i, current_dir):
    if i == 0: 
        if current_dir == "w": return "^ "
        if current_dir == "s": return "v "
        if current_dir == "a": return "< "
        if current_dir == "d": return "> "
    
    curr = snake[i]
    prev = snake[i-1]
    
    if i == len(snake) - 1:
        return "║ " if prev[0] != curr[0] else "══"
    
    nxt = snake[i+1]
    d1 = (prev[0] - curr[0], prev[1] - curr[1])
    d2 = (nxt[0] - curr[0], nxt[1] - curr[1])
    
    if d1[0] == 0 and d2[0] == 0: return "══"
    if d1[1] == 0 and d2[1] == 0: return "║ "
    
    if (d1 == (0, 1) and d2 == (1, 0)) or (d1 == (1, 0) and d2 == (0, 1)): return "╔═"
    if (d1 == (0, -1) and d2 == (1, 0)) or (d1 == (1, 0) and d2 == (0, -1)): return "╗ "
    if (d1 == (0, 1) and d2 == (-1, 0)) or (d1 == (-1, 0) and d2 == (0, 1)): return "╚═"
    if (d1 == (0, -1) and d2 == (-1, 0)) or (d1 == (-1, 0) and d2 == (0, -1)): return "╝ "
    
    return "o "

def draw():
    os.system('cls' if os.name == 'nt' else 'clear')
    print(f"--- ARCADE SNAKE --- Score: {score}")
    
    # Grid of 2-character strings
    grid = [["  " for _ in range(width)] for _ in range(height)]
    
    # Draw Border (Using 2-char strings for everything)
    for x in range(width):
        grid[0][x] = "══"
        grid[height-1][x] = "══"
    for y in range(height):
        grid[y][0] = "║ "
        grid[y][width-1] = " ║" # Space then pipe to fill 2 cols
        
    grid[0][0] = "╔═"
    grid[0][width-1] = "═╗"
    grid[height-1][0] = "╚═"
    grid[height-1][width-1] = "═╝"
    
    grid[food[0]][food[1]] = "🍎"
    
    for i in range(len(snake)):
        y, x = snake[i]
        if 0 <= y < height and 0 <= x < width:
            grid[y][x] = get_snake_char(i, direction)
            
    for row in grid:
        print("".join(row))

# 2. MAIN LOOP
while True:
    draw()
    move = input("Move (WASD): ").lower()
    if move in ["w", "a", "s", "d"]:
        if (move == "w" and direction != "s") or \
           (move == "s" and direction != "w") or \
           (move == "a" and direction != "d") or \
           (move == "d" and direction != "a"):
            direction = move
    elif move == "q": break

    head = snake[0].copy()
    if direction == "w": head[0] -= 1
    elif direction == "s": head[0] += 1
    elif direction == "a": head[1] -= 1
    elif direction == "d": head[1] += 1

    # COLLISION CHECK (Strictly on the border cells)
    if head[0] <= 0 or head[0] >= height-1 or head[1] <= 0 or head[1] >= width-1 or head in snake:
        draw() # Show the final position
        print("\n!!! COLLISION !!! GAME OVER")
        break

    snake.insert(0, head)
    if head == food:
        score += 1
        while True:
            new_food = [random.randint(1, height-2), random.randint(1, width-2)]
            if new_food not in snake:
                food = new_food
                break
    else:
        snake.pop()
