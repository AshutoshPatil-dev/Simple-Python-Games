import random
import os
import sys
import time

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

# --- Terminal Colors ---
BG_GREEN = "\033[42m"
BG_YELLOW = "\033[43m"
BG_GREY = "\033[100m"
FG_BLACK = "\033[30m"
FG_WHITE = "\033[37m"
FG_GREEN = "\033[92m"
FG_YELLOW = "\033[93m"
FG_RED = "\033[91m"
FG_CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"

# --- Dictionaries ---
WORDS_EASY = [
    "APPLE", "BEACH", "BRAIN", "BREAD", "BRUSH", "CHAIR", "CHEST", "CHORD",
    "CLICK", "CLOCK", "CLOUD", "DANCE", "DIARY", "DRINK", "DRIVE", "EARTH",
    "FEAST", "FIELD", "FRUIT", "GLASS", "GRAPE", "GREEN", "GHOST", "HEART",
    "HOUSE", "JUICE", "LIGHT", "LEMON", "MELON", "MONEY", "MUSIC", "NIGHT",
    "OCEAN", "PARTY", "PIANO", "PILOT", "PLANE", "PHONE", "PIZZA", "PLANT",
    "RADIO", "RIVER", "ROBOT", "SHIRT", "SHOES", "SMILE", "SNAKE", "SPACE",
    "SPOON", "STORM", "TABLE", "TIGER", "TOAST", "TOUCH", "TRAIN", "TRUCK",
    "VOICE", "WATER", "WATCH", "WHALE", "WORLD", "WRITE", "YOUTH", "ZEBRA"
]

WORDS_MEDIUM = [
    "ACTION", "ANIMAL", "ANSWER", "BOTTLE", "BRANCH", "BREATH", "BRIDGE",
    "CAMERA", "CANCER", "CASTLE", "CHANCE", "CHANGE", "CHARGE", "CHOICE",
    "CHURCH", "CIRCLE", "CLIENT", "CLOSET", "COFFEE", "CORNER", "COURSE",
    "CREDIT", "DANGER", "DEGREE", "DESIGN", "DESIRE", "DETAIL", "DINNER",
    "DOCTOR", "DOLLAR", "DOMAIN", "DOUBLE", "DRIVER", "EFFORT", "ENERGY",
    "ENGINE", "ESTATE", "EXPERT", "FAMILY", "FARMER", "FATHER", "FELLOW",
    "FIGURE", "FLIGHT", "FLOWER", "FOREST", "FRIEND", "FUTURE", "GARDEN"
]

WORDS_HARD = [
    "ABSOLUTE", "ACADEMIC", "ACCIDENT", "ACCURACY", "ACTIVITY", "ADDITION", "ADEQUATE",
    "ADVANCED", "ADVISORY", "ADVOCATE", "AIRCRAFT", "ALLIANCE", "ALTHOUGH", "ALUMINUM",
    "ANALYSIS", "ANNOUNCE", "ANYTHING", "ANYWHERE", "APPARENT", "APPROACH", "APPROVAL",
    "ARGUMENT", "ARTISTIC", "ASSEMBLY", "ASSESSED", "ASSIGNED", "ATHLETIC", "ATTITUDE",
    "AUDIENCE", "BACHELOR", "BACTERIA", "BASEBALL", "BASEMENT", "BATHROOM", "BOUNDARY",
    "BROCHURE", "BULLETIN", "BUSINESS", "CALCULUS", "CAMPAIGN", "CAPACITY", "CATEGORY",
    "CAUTIOUS", "CHAMPION", "CHECKOUT", "CIRCULAR", "CIVILIAN", "CLEARING", "CLINICAL",
    "CLOTHING", "COLLAPSE", "COLONIAL", "COLORFUL", "COMBINED", "COMEDIAN", "COMMANDS",
    "COMMERCE", "COMPLAIN", "COMPLETE", "COMPUTER", "CONCLUDE", "CONCRETE", "CONFLICT",
    "CONSIDER", "CONSTANT", "CONSUMER", "CONTINUE", "CONTRACT", "CONTRARY", "CONTRAST",
    "CONVINCE", "CORRIDOR", "COVERAGE", "CREATION", "CREATIVE", "CRIMINAL", "CRITICAL",
    "CRITIQUE", "CULTURAL", "CURRENCY", "CUSTOMER", "DATABASE", "DAUGHTER", "DAYLIGHT",
    "DEADLINE", "DECISION", "DECREASE", "DEDICATE", "DEFENDER", "DELEGATE", "DELIVERY",
    "DESCRIBE", "DESIGNER", "DETAILED", "DIALOGUE", "DIRECTOR", "DISASTER", "DISCOVER"
]

# --- Core Functions ---
def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def get_feedback(guess, secret):
    feedback = ["absent"] * len(secret)
    secret_list = list(secret)
    guess_list = list(guess)
    
    # Correct pass
    for i in range(len(secret)):
        if guess_list[i] == secret_list[i]:
            feedback[i] = "correct"
            secret_list[i] = None
            guess_list[i] = None
    
    # Present pass
    for i in range(len(secret)):
        if guess_list[i] is not None and guess_list[i] in secret_list:
            feedback[i] = "present"
            secret_list[secret_list.index(guess_list[i])] = None

    return feedback

def draw_header():
    print(f"{BOLD}{FG_CYAN}")
    print(" ╔══════════════════════════════════════════════╗")
    print(" ║                    WORDLY                    ║")
    print(" ╚══════════════════════════════════════════════╝")
    print(f"{RESET}")

def draw_keyboard(keyboard_state):
    rows = [
        "QWERTYUIOP",
        "ASDFGHJKL",
        "ZXCVBNM"
    ]

    print("\n" + " " * 4 + "Keyboard Status:")
    for row_idx, row in enumerate(rows):
        padding = " " * (row_idx * 2 + 4)
        line = padding
        for char in row:
            state = keyboard_state.get(char, "tbd")
            if state == "correct":
                color = f"{BG_GREEN}{FG_BLACK}"
            elif state == "present":
                color = f"{BG_YELLOW}{FG_BLACK}"
            elif state == "absent":
                color = f"{BG_GREY}{FG_WHITE}"
            else:
                color = ""
            
            line += f"{color} {char} {RESET} "
        print(line)
    print()

def draw_grid(guesses, current_attempt, max_attempts, secret_word):
    word_len = len(secret_word)
    
    # Box drawing characters
    TOP = "┌" + ("───┬" * (word_len - 1)) + "───┐"
    MID = "├" + ("───┼" * (word_len - 1)) + "───┤"
    BOT = "└" + ("───┴" * (word_len - 1)) + "───┘"
    
    padding = " " * ((48 - (word_len * 4 + 1)) // 2)
    
    print(padding + TOP)
    for i in range(max_attempts):
        if i < len(guesses):
            guess = guesses[i]
            feedback = get_feedback(guess, secret_word)
            line = "│"
            for j in range(word_len):
                char = guess[j]
                if feedback[j] == "correct":
                    line += f"{BG_GREEN}{FG_BLACK} {char} {RESET}│"
                elif feedback[j] == "present":
                    line += f"{BG_YELLOW}{FG_BLACK} {char} {RESET}│"
                else:
                    line += f"{BG_GREY}{FG_WHITE} {char} {RESET}│"
            print(padding + line)
        else:
            line = "│" + ("   │" * word_len)
            print(padding + line)
            
        if i < max_attempts - 1:
            print(padding + MID)
            
    print(padding + BOT)

def print_rules():
    clear_screen()
    draw_header()
    print(f"{BOLD}HOW TO PLAY:{RESET}\n")
    print(f"1. Choose a difficulty level.")
    print(f"2. Guess the hidden word within the allowed attempts.")
    print(f"3. After each guess, the color of the tiles will change to show how close your guess was to the word.\n")
    print(f"  {BG_GREEN}{FG_BLACK} A {RESET} : The letter is in the word and in the correct spot.")
    print(f"  {BG_YELLOW}{FG_BLACK} B {RESET} : The letter is in the word but in the wrong spot.")
    print(f"  {BG_GREY}{FG_WHITE} C {RESET} : The letter is not in the word in any spot.\n")
    print(f"{BOLD}DIFFICULTIES:{RESET}")
    print(f"  EASY   : 5 letters, 6 attempts")
    print(f"  MEDIUM : 6 letters, 6 attempts")
    print(f"  HARD   : 8 letters, 7 attempts\n")
    input("Press ENTER to return to the main menu...")

def select_difficulty():
    while True:
        clear_screen()
        draw_header()
        print(f" {BOLD}Select Difficulty:{RESET}")
        print("  1. Easy   (5 Letters, 6 Attempts)")
        print("  2. Medium (6 Letters, 6 Attempts)")
        print("  3. Hard   (8 Letters, 7 Attempts)")
        print("  4. How to Play")
        print("  5. Quit\n")
        choice = input("Enter your choice (1-5): ").strip()
        
        if choice == '1': return 'easy', WORDS_EASY, 5, 6
        elif choice == '2': return 'medium', WORDS_MEDIUM, 6, 6
        elif choice == '3': return 'hard', WORDS_HARD, 8, 7
        elif choice == '4': print_rules()
        elif choice == '5': sys.exit(0)
        else:
            print(f"{FG_RED}Invalid choice. Please try again.{RESET}")
            time.sleep(1)

def play_game():
    # Make terminal support ANSI sequences on Windows
    if os.name == 'nt':
        os.system('color')
        
    while True:
        diff_name, words_list, word_len, max_attempts = select_difficulty()
        secret_word = random.choice(words_list)
        guesses = []
        keyboard_state = {}
        
        while len(guesses) < max_attempts:
            clear_screen()
            draw_header()
            
            diff_color = FG_GREEN if diff_name == 'easy' else FG_YELLOW if diff_name == 'medium' else FG_RED
            print(f" {BOLD}Difficulty: {diff_color}{diff_name.upper()}{RESET} | {BOLD}Attempt: {len(guesses)+1}/{max_attempts}{RESET}")
            print(f" {BOLD}Word Length: {word_len} letters{RESET}")
            if diff_name == 'easy':
                print(f" {BOLD}{FG_CYAN}Hint: The word starts with '{secret_word[0]}'{RESET}\n")
            else:
                print()
            
            draw_grid(guesses, len(guesses), max_attempts, secret_word)
            draw_keyboard(keyboard_state)
            
            guess = input(f"\n{BOLD}Enter your guess:{RESET} ").strip().upper()
            
            if len(guess) != word_len:
                print(f"{FG_RED}Your guess must be exactly {word_len} letters long!{RESET}")
                time.sleep(1.5)
                continue
                
            if not guess.isalpha():
                print(f"{FG_RED}Your guess must contain only letters!{RESET}")
                time.sleep(1.5)
                continue
                
            guesses.append(guess)
            
            # Update keyboard state
            feedback = get_feedback(guess, secret_word)
            for i, char in enumerate(guess):
                current_state = keyboard_state.get(char, "tbd")
                new_state = feedback[i]
                
                # State precedence: correct > present > absent
                if new_state == "correct":
                    keyboard_state[char] = "correct"
                elif new_state == "present" and current_state != "correct":
                    keyboard_state[char] = "present"
                elif new_state == "absent" and current_state not in ["correct", "present"]:
                    keyboard_state[char] = "absent"
            
            if guess == secret_word:
                clear_screen()
                draw_header()
                print(f"\n {BOLD}Attempt: {len(guesses)}/{max_attempts}{RESET}\n")
                draw_grid(guesses, len(guesses), max_attempts, secret_word)
                draw_keyboard(keyboard_state)
                print(f"\n{FG_GREEN}🎉 GENIUS! You guessed the word correctly in {len(guesses)} attempts! 🎉{RESET}")
                break
        else:
            clear_screen()
            draw_header()
            print(f"\n {BOLD}Attempt: {max_attempts}/{max_attempts}{RESET}\n")
            draw_grid(guesses, len(guesses), max_attempts, secret_word)
            draw_keyboard(keyboard_state)
            print(f"\n{FG_RED}💀 GAME OVER! The word was {BOLD}{secret_word}{RESET}{FG_RED}.💀{RESET}")
            
        print("\n" + "-" * 48)
        replay = input(f"{BOLD}Do you want to play again? (y/n): {RESET}").strip().lower()
        if replay != 'y':
            print(f"\n{FG_CYAN}Thanks for playing! Goodbye.{RESET}")
            sys.exit(0)

if __name__ == "__main__":
    play_game()
