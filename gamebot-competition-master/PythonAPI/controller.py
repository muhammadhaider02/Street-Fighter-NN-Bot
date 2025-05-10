import socket
import json
from game_state import GameState
#from bot import fight
import sys
from bot import Bot
import csv
import os
import time
import math
import random

def connect(port):
    #For making a connection with the game
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(("127.0.0.1", port))
    server_socket.listen(5)
    (client_socket, _) = server_socket.accept()
    print ("Connected to game!")
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

def collect_game_data(game_state, bot_command, data_collector, session_id, match_id, frame_counter, player_id):
    """Collect game state and button press data for training a neural network model."""
    
    # Calculate distance between players
    distance = math.sqrt(
        (game_state.player1.x_coord - game_state.player2.x_coord) ** 2 +
        (game_state.player1.y_coord - game_state.player2.y_coord) ** 2
    )
    distance = int(distance)  # Convert to integer to match the example format
    
    # Determine winner if round is over
    winner = -1  # Default to -1 (no winner yet)
    if game_state.is_round_over:
        if game_state.player1.health > game_state.player2.health:
            winner = 1
        elif game_state.player2.health > game_state.player1.health:
            winner = 2
        else:
            winner = 0  # Draw
    
    # Determine opponent ID based on player ID
    opponent_id = 7  # Set to 7 as in the example
    
    # Get the appropriate player and opponent data based on player_id
    if player_id == "1":
        player_data = game_state.player1
        opponent_data = game_state.player2
    else:
        player_data = game_state.player2
        opponent_data = game_state.player1
    
    # Check if player buttons are available from bot_command or use from game state
    if player_id == "1":
        player_buttons = bot_command.player_buttons
    else:
        player_buttons = bot_command.player2_buttons
    
    # Convert boolean values to integers (0/1)
    def bool_to_int(value):
        return 1 if value else 0
    
    # Debug info
    if frame_counter % 100 == 0:  # Print every 100 frames to avoid spam
        print(f"Frame {frame_counter} - Opponent move data:")
        print(f"  is_jumping: {opponent_data.is_jumping}")
        print(f"  is_crouching: {opponent_data.is_crouching}")
        print(f"  is_player_in_move: {opponent_data.is_player_in_move}")
        print(f"  move_id: {opponent_data.move_id}")
        print(f"  Button presses: Left={bool_to_int(opponent_data.player_buttons.left)}, "
              f"Right={bool_to_int(opponent_data.player_buttons.right)}, "
              f"Up={bool_to_int(opponent_data.player_buttons.up)}, "
              f"Down={bool_to_int(opponent_data.player_buttons.down)}, "
              f"A={bool_to_int(opponent_data.player_buttons.A)}, "
              f"B={bool_to_int(opponent_data.player_buttons.B)}, "
              f"X={bool_to_int(opponent_data.player_buttons.X)}, "
              f"Y={bool_to_int(opponent_data.player_buttons.Y)}")
    
    # Simulate some opponent movements for testing if no real opponent data is detected
    # Only use this for debugging - remove in production
    opponent_moves_detected = (
        opponent_data.is_jumping or 
        opponent_data.is_crouching or 
        opponent_data.is_player_in_move or 
        opponent_data.move_id > 0 or
        opponent_data.player_buttons.left or 
        opponent_data.player_buttons.right or
        opponent_data.player_buttons.up or 
        opponent_data.player_buttons.down or
        opponent_data.player_buttons.A or 
        opponent_data.player_buttons.B or
        opponent_data.player_buttons.X or 
        opponent_data.player_buttons.Y
    )
    
    # Map data to the required columns, matching the format in the example
    game_data = {
        'session_id': int(time.time()),  # Use current timestamp as session_id
        'match_id': 0,  # Set to 0 as in the example
        'frame': frame_counter,
        'timestamp': int(time.time()),
        'player_id': int(player_id),
        'opponent_id': opponent_id,
        'player_health': player_data.health,
        'opponent_health': opponent_data.health,
        'player_x': player_data.x_coord,
        'player_y': player_data.y_coord,
        'opponent_x': opponent_data.x_coord,
        'opponent_y': opponent_data.y_coord,
        'distance': distance,
        'timer': game_state.timer,
        'has_round_started': bool_to_int(game_state.has_round_started),
        'is_round_over': bool_to_int(game_state.is_round_over),
        'winner': winner,
        'player_jumping': bool_to_int(player_data.is_jumping),
        'player_crouching': bool_to_int(player_data.is_crouching),
        'player_in_move': bool_to_int(player_data.is_player_in_move),
        'player_move_id': player_data.move_id,
        'opponent_jumping': bool_to_int(opponent_data.is_jumping),
        'opponent_crouching': bool_to_int(opponent_data.is_crouching),
        'opponent_in_move': bool_to_int(opponent_data.is_player_in_move),
        'opponent_move_id': opponent_data.move_id,
        'action_left': bool_to_int(player_buttons.left),
        'action_right': bool_to_int(player_buttons.right),
        'action_up': bool_to_int(player_buttons.up),
        'action_down': bool_to_int(player_buttons.down),
        'action_A': bool_to_int(player_buttons.A),
        'action_B': bool_to_int(player_buttons.B),
        'action_X': bool_to_int(player_buttons.X),
        'action_Y': bool_to_int(player_buttons.Y),
        'action_L': 0,  # Set to 0 as in the example
        'action_R': 0,  # Set to 0 as in the example
        'action_select': 0,  # Set to 0 as in the example
        'action_start': 0,  # Set to 0 as in the example
        'opponent_left': bool_to_int(opponent_data.player_buttons.left),
        'opponent_right': bool_to_int(opponent_data.player_buttons.right),
        'opponent_up': bool_to_int(opponent_data.player_buttons.up),
        'opponent_down': bool_to_int(opponent_data.player_buttons.down),
        'opponent_A': bool_to_int(opponent_data.player_buttons.A),
        'opponent_B': bool_to_int(opponent_data.player_buttons.B),
        'opponent_X': bool_to_int(opponent_data.player_buttons.X),
        'opponent_Y': bool_to_int(opponent_data.player_buttons.Y),
        'opponent_L': 0,  # Set to 0 as in the example
        'opponent_R': 0,  # Set to 0 as in the example
        'opponent_select': 0,  # Set to 0 as in the example
        'opponent_start': 0,  # Set to 0 as in the example
    }
    
    # Write data to CSV
    data_collector.writerow(game_data)
    
    return frame_counter + 1

def check_opponent_buttons(game_state, player_id):
    """Utility function to check if opponent buttons are actually being tracked."""
    if player_id == "1":
        opponent_data = game_state.player2
    else:
        opponent_data = game_state.player1
        
    print("\nChecking opponent button data...")
    print(f"Opponent is_jumping: {opponent_data.is_jumping}")
    print(f"Opponent is_crouching: {opponent_data.is_crouching}")
    print(f"Opponent is_player_in_move: {opponent_data.is_player_in_move}")
    print(f"Opponent move_id: {opponent_data.move_id}")
    
    # Check if buttons object exists and has expected attributes
    if hasattr(opponent_data, 'player_buttons'):
        buttons = opponent_data.player_buttons
        print(f"Opponent buttons object exists: {buttons}")
        print(f"Opponent left: {buttons.left}")
        print(f"Opponent right: {buttons.right}")
        print(f"Opponent up: {buttons.up}")
        print(f"Opponent down: {buttons.down}")
        print(f"Opponent A: {buttons.A}")
        print(f"Opponent B: {buttons.B}")
        print(f"Opponent X: {buttons.X}")
        print(f"Opponent Y: {buttons.Y}")
    else:
        print("Opponent does not have player_buttons attribute")
    
    print("End of opponent data check")
    return

def main():
    if len(sys.argv) < 2:
        print("Usage: python controller.py <player_id>")
        print("  player_id: 1 for Player 1 (Left Side), 2 for Player 2 (Right Side)")
        sys.exit(1)
        
    player_id = sys.argv[1]
    
    # Validate player_id
    if player_id not in ['1', '2']:
        print("Error: Player ID must be '1' (Left Side) or '2' (Right Side)")
        print("Usage: python controller.py <player_id>")
        sys.exit(1)
    
    if player_id == '1':
        print("Initializing data collection for Player 1 (Left Side)")
        client_socket = connect(9999)
    else:  # player_id == '2'
        print("Initializing data collection for Player 2 (Right Side)")
        client_socket = connect(10000)
    
    current_game_state = None
    
    # Initialize frame counter and match_id
    frame_counter = 1  # Start from 1 like in the example
    session_id = int(time.time())  # Use timestamp as session_id
    match_id = 0  # Set to 0 as in the example
    
    # Create data collection file
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    data_file_path = f"game_data_{player_id}_{timestamp}.csv"
    
    # Create CSV writer with all required columns
    with open(data_file_path, 'w', newline='') as csvfile:
        fieldnames = [
            'session_id', 'match_id', 'frame', 'timestamp', 'player_id', 'opponent_id',
            'player_health', 'opponent_health', 'player_x', 'player_y', 'opponent_x', 
            'opponent_y', 'distance', 'timer', 'has_round_started', 'is_round_over', 
            'winner', 'player_jumping', 'player_crouching', 'player_in_move', 
            'player_move_id', 'opponent_jumping', 'opponent_crouching', 'opponent_in_move', 
            'opponent_move_id', 'action_left', 'action_right', 'action_up', 'action_down', 
            'action_A', 'action_B', 'action_X', 'action_Y', 'action_L', 'action_R', 
            'action_select', 'action_start', 'opponent_left', 'opponent_right', 
            'opponent_up', 'opponent_down', 'opponent_A', 'opponent_B', 'opponent_X', 
            'opponent_Y', 'opponent_L', 'opponent_R', 'opponent_select', 'opponent_start'
        ]
        data_collector = csv.DictWriter(csvfile, fieldnames=fieldnames)
        data_collector.writeheader()
        
        bot = Bot()
        print(f"Data collection started. Saving to {data_file_path}")
        
        # First, receive a game state to check opponent data
        test_game_state = receive(client_socket)
        check_opponent_buttons(test_game_state, player_id)
        
        try:
            # Game loop
            current_game_state = test_game_state  # Use the initial test state
            
            while (current_game_state is None) or (not current_game_state.is_round_over):
                # Get bot command based on current state
                bot_command = bot.fight(current_game_state, player_id)
                
                # Collect game data with all required fields
                frame_counter = collect_game_data(
                    current_game_state, 
                    bot_command, 
                    data_collector, 
                    session_id, 
                    match_id, 
                    frame_counter, 
                    player_id
                )
                
                # Send command to the game
                send(client_socket, bot_command)
                
                # Get the next game state
                current_game_state = receive(client_socket)
                
            print(f"Round complete. Data collection finished.")
            
        except KeyboardInterrupt:
            print("\nData collection interrupted by user.")
        except Exception as e:
            print(f"Error during data collection: {e}")
            import traceback
            traceback.print_exc()
        finally:
            print(f"Data saved to {data_file_path}")
            print(f"Total frames collected: {frame_counter - 1}")  # Subtract 1 as we start from frame 1

if __name__ == '__main__':
   main()