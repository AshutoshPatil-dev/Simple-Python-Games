import random
import os

# 1. SETUP THE WORLD
width = 10
height = 5
player_x = 1
player_y = 1
exit_x = 8
exit_y = 3
score = 0

def clear():
    os.system('cls' if os.name == 'nt' else 'clear')

# 2. MAIN GAME LOOP
while True:
    clear()
    print(f"--- QUEST GAME --- Score: {score}")
    print("Use WASD + Enter to move. Goal: reach X")
    
    # 3. DRAW THE MAP (Basic Nested Loops)
    for y in range(height):
        row = ""
        for x in range(width):
            if x == player_x and y == player_y:
                row += "P " # Player
            elif x == exit_x and y == exit_y:
                row += "X " # Exit
            elif x == 0 or x == width-1 or y == 0 or y == height-1:
                row += "# " # Wall
            else:
                row += ". " # Ground
        print(row)

    # 4. GET INPUT (Basic input() function)
    move = input("Move: ").lower()

    # 5. LOGIC (Simple If/Else)
    if move == "w": player_y -= 1
    elif move == "s": player_y += 1
    elif move == "a": player_x -= 1
    elif move == "d": player_x += 1
    elif move == "q": break

    # Check for Win
    if player_x == exit_x and player_y == exit_y:
        print("YOU WON!")
        break
