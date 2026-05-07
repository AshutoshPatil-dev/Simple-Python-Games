from random import randint as ri

print("--- Welcome to the Number Guessing Game ---")
print("I am thinking of a number between 1 and 100.")

secret_number = ri(1, 100)
attempts = 0
max_attempts = 10

while attempts < max_attempts:
    guess = int(input("Enter your guess: "))
    attempts = attempts + 1
    
    if guess == secret_number:
        print(f"Correct! You guessed it in {attempts} tries.")
        break
    elif guess < secret_number:
        print("Lower! Try again.")
    else:
        print("Higher! Try again.")
        
    print(f"Remaining attempts: {max_attempts - attempts}")

if attempts == max_attempts and guess != secret_number:
    print(f"Game Over! The number was {secret_number}")
