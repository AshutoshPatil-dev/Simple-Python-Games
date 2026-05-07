import random
import os

# ANSI Color Codes
GREEN = "\033[92m"
YELLOW = "\033[93m"
RESET = "\033[0m"
BOLD = "\033[1m"

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def get_feedback(guess, secret):
    """
    Returns a list of tuples (letter, color) for the guess.
    """
    feedback = [None] * 5
    secret_list = list(secret)
    guess_list = list(guess)
    
    # First pass: Find correct positions (Green)
    for i in range(5):
        if guess_list[i] == secret_list[i]:
            feedback[i] = (guess_list[i], GREEN)
            secret_list[i] = None # Mark as used
            guess_list[i] = None
            
    # Second pass: Find misplaced letters (Yellow)
    for i in range(5):
        if guess_list[i] is not None:
            if guess_list[i] in secret_list:
                feedback[i] = (guess_list[i], YELLOW)
                secret_list[secret_list.index(guess_list[i])] = None # Mark as used
            else:
                feedback[i] = (guess_list[i], RESET)
                
    return feedback

def print_board(guesses, secret):
    clear_screen()
    print(f"{BOLD}--- WORD GUESSING GAME ---{RESET}")
    print("Guess the 5-letter word in 6 tries.")
    print()
    
    for guess in guesses:
        feedback = get_feedback(guess, secret)
        line = ""
        for letter, color in feedback:
            line += f"{color} {letter.upper()} {RESET} "
        print(line)
        
    # Fill remaining empty slots
    for _ in range(6 - len(guesses)):
        print("_ " * 5)
    print()

def main():
    # Simple word list
    words = [
        "APPLE", "BEACH", "BRAIN", "BREAD", "BRUSH", "CHAIR", "CHEST", "CHORD",
        "CLICK", "CLOCK", "CLOUD", "DANCE", "DIARY", "DRINK", "DRIVE", "EARTH",
        "FEAST", "FIELD", "FRUIT", "GLASS", "GRAPE", "GREEN", "GHOST", "HEART",
        "HOUSE", "JUICE", "LIGHT", "LEMON", "MELON", "MONEY", "MUSIC", "NIGHT",
        "OCEAN", "PARTY", "PIANO", "PILOT", "PLANE", "PHONE", "PIZZA", "PLANT",
        "RADIO", "RIVER", "ROBOT", "SHIRT", "SHOES", "SMILE", "SNAKE", "SPACE",
        "SPOON", "STORM", "TABLE", "TIGER", "TOAST", "TOUCH", "TRAIN", "TRUCK",
        "VOICE", "WATER", "WATCH", "WHALE", "WORLD", "WRITE", "YOUTH", "ZEBRA"
    ]
    
    secret_word = random.choice(words).upper()
    guesses = []
    max_attempts = 6
    
    while len(guesses) < max_attempts:
        print_board(guesses, secret_word)
        
        guess = input(f"Attempt {len(guesses) + 1}/{max_attempts}. Enter a 5-letter word: ").upper()
        
        if len(guess) != 5:
            print("Please enter a 5-letter word.")
            input("Press Enter to continue...")
            continue
            
        guesses.append(guess)
        
        if guess == secret_word:
            print_board(guesses, secret_word)
            print(f"{GREEN}Congratulations! You guessed the word: {secret_word}{RESET}")
            break
    else:
        print_board(guesses, secret_word)
        print(f"Game Over! The word was: {secret_word}")

if __name__ == "__main__":
    main()
