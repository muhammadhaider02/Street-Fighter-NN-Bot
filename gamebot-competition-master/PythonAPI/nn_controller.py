import socket
import json
from game_state import GameState
import sys
from nn_bot import NeuralBot
import csv
import os
import time

def connect(port):
    #For making a connection with the game
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(("127.0.0.1", port))
    server_socket.listen(5)
    (client_socket, _) = server_socket.accept()
    print("Connected to game!")
    return client_socket

def send(client_socket, command):
    #This function will send your updated command to Bizhawk so that game reacts according to your command.
    command_dict = command.object_to_dict()
    pay_load = json.dumps(command_dict).encode()
    client_socket.sendall(pay_load)

def receive(client_socket):
    #receive the game state and return game state
    pay_load = client_socket.recv(4096)
    input_dict = json.loads(pay_load.decode())
    game_state = GameState(input_dict)

    return game_state

def main():
    # Check command line arguments
    if len(sys.argv) < 2:
        print("Usage: python nn_controller.py <player_id> [model_path] [scaler_path]")
        print("Example: python nn_controller.py 1 ShadowFightBotMLP.keras scaler.joblib")
        sys.exit(1)
        
    # Process command line arguments
    player_id = sys.argv[1]
    
    # Validate player_id - must be '1' or '2'
    if player_id not in ['1', '2']:
        print("Error: Player ID must be '1' (Left Side) or '2' (Right Side)")
        print("Usage: python nn_controller.py <player_id> [model_path] [scaler_path]")
        sys.exit(1)
    
    model_path = sys.argv[2] if len(sys.argv) > 2 else 'ShadowFightBotMLP.keras'
    scaler_path = sys.argv[3] if len(sys.argv) > 3 else 'scaler.joblib'
    
    # Check if model and scaler files exist
    if not os.path.exists(model_path):
        print(f"Error: Model file '{model_path}' not found")
        sys.exit(1)
        
    if not os.path.exists(scaler_path):
        print(f"Error: Scaler file '{scaler_path}' not found")
        sys.exit(1)
    
    # Set up the connection
    if player_id == '1':
        print("Initializing bot for Player 1 (Left Side)")
        client_socket = connect(9999)
    else:  # player_id == '2'
        print("Initializing bot for Player 2 (Right Side)")
        client_socket = connect(10000)
    
    # Initialize the neural network bot
    print(f"Loading neural network model from {model_path}...")
    bot = NeuralBot(model_path=model_path, scaler_path=scaler_path)
    
    # Game loop
    current_game_state = None
    print("Starting game with Neural Network bot...")
    
    try:
        while (current_game_state is None) or (not current_game_state.is_round_over):
            # Receive game state
            current_game_state = receive(client_socket)
            
            # Get bot command based on neural network predictions
            bot_command = bot.fight(current_game_state, player_id)
            
            # Send command to the game
            send(client_socket, bot_command)
        
        print("Round over. Neural Network bot finished playing.")
    except KeyboardInterrupt:
        print("\nGame interrupted by user. Exiting...")
    except Exception as e:
        print(f"Error during gameplay: {e}")

if __name__ == '__main__':
   main() 