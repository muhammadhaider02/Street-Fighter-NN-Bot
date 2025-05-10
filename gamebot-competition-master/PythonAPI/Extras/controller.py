import socket
import json
import sys
import keyboard
from game_state import GameState
from bot import Bot
from buttons import Buttons
import time
import signal

def connect(port):
    # For making a connection with the game
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(("127.0.0.1", port))
    server_socket.listen(5)
    (client_socket, _) = server_socket.accept()
    print("Connected to game!")
    return client_socket

def send(client_socket, command):
    # This function will send your updated command to Bizhawk so that game reacts according to your command.
    command_dict = command.object_to_dict()
    pay_load = json.dumps(command_dict).encode()
    client_socket.sendall(pay_load)

def receive(client_socket):
    # Receive the game state and return game state
    pay_load = client_socket.recv(4096)
    input_dict = json.loads(pay_load.decode())
    game_state = GameState(input_dict)
    return game_state

class HumanController:
    def __init__(self, player_id, enable_logging=True, log_frequency=1, buffer_size=50):
        self.player_id = player_id
        self.human_buttons = Buttons()
        self.bot = Bot(enable_logging=enable_logging, log_frequency=log_frequency, buffer_size=buffer_size)
        self.setup_keyboard_listeners()
        print(f"Human control mode activated for Player {player_id}")
        print("Controls: Arrow keys for movement, Z=A, X=B, A=X, S=Y, Q=L, W=R")

    def setup_keyboard_listeners(self):
        """Set up keyboard listeners for human control"""
        # Map keyboard keys to button states
        self.key_mapping = {
            'left': 'left arrow',
            'right': 'right arrow',
            'up': 'up arrow',
            'down': 'down arrow',
            'A': 'z',
            'B': 'x',
            'X': 'a',
            'Y': 's',
            'L': 'q',
            'R': 'w',
            'select': 'tab',
            'start': 'enter'
        }
        
        # Set up keyboard hooks
        for button, key in self.key_mapping.items():
            keyboard.on_press_key(key, lambda e, button=button: self.on_key_press(e, button))
            keyboard.on_release_key(key, lambda e, button=button: self.on_key_release(e, button))

    def on_key_press(self, event, button):
        """Handle key press events"""
        setattr(self.human_buttons, button, True)

    def on_key_release(self, event, button):
        """Handle key release events"""
        setattr(self.human_buttons, button, False)

    def get_command(self, current_game_state):
        """Get command based on human input"""
        return self.bot.fight(current_game_state, self.player_id, self.human_buttons)

    def cleanup(self):
        """Clean up keyboard hooks"""
        keyboard.unhook_all()

# Signal handler for graceful shutdown
def signal_handler(sig, frame):
    print("Received signal to terminate. Flushing data...")
    if 'bot' in globals():
        bot.flush_data()
    if 'human_controller' in globals() and human_controller:
        human_controller.bot.flush_data()
    print("Data flushed. Exiting.")
    sys.exit(0)

def main():
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    mode = 1  # Default: Bot vs Bot
    player_id = sys.argv[1]
    
    # Default logging settings
    enable_logging = True
    log_frequency = 1  # Always log every frame
    buffer_size = 50  # Default buffer size
    
    # Check for human control mode
    if len(sys.argv) > 2 and sys.argv[2] == 'human':
        mode = 3  # Human control mode
    
    # Check for performance mode - now we'll log every frame but optimize writing
    if len(sys.argv) > 2 and sys.argv[2] == 'performance':
        buffer_size = 100  # Smaller buffer size to write more frequently
        print(f"Performance mode: Logging every frame with optimized disk writes")
    elif len(sys.argv) > 3 and sys.argv[3] == 'performance':
        buffer_size = 100  # Smaller buffer size to write more frequently
        print(f"Performance mode: Logging every frame with optimized disk writes")
    
    # Connect to the game
    if player_id == '1':
        client_socket = connect(9999)
    elif player_id == '2':
        client_socket = connect(10000)
    else:
        print("Invalid player ID. Use 1 or 2.")
        return
    
    # Initialize bot and human controller if needed
    global bot, human_controller
    bot = Bot(enable_logging=enable_logging, log_frequency=log_frequency, buffer_size=buffer_size)
    human_controller = None
    if mode == 3:
        human_controller = HumanController(player_id, enable_logging=enable_logging, log_frequency=log_frequency, buffer_size=buffer_size)
    
    try:
        current_game_state = None
        frame_count = 0
        last_time = time.time()
        fps_update_interval = 5.0  # Update FPS every 5 seconds
        last_flush_time = time.time()
        flush_interval = 10.0  # Flush data every 10 seconds
        
        while (current_game_state is None) or (not current_game_state.is_round_over):
            # Receive game state
            current_game_state = receive(client_socket)
            
            # Get command based on mode
            if mode == 3:  # Human control
                bot_command = human_controller.get_command(current_game_state)
            else:  # Bot control
                bot_command = bot.fight(current_game_state, player_id)
            
            # Send command to game
            send(client_socket, bot_command)
            
            # FPS calculation
            frame_count += 1
            current_time = time.time()
            elapsed = current_time - last_time
            if elapsed >= fps_update_interval:
                fps = frame_count / elapsed
                print(f"FPS: {fps:.2f}")
                frame_count = 0
                last_time = current_time
            
            # Periodic data flush to ensure data is saved even during long sessions
            if current_time - last_flush_time >= flush_interval:
                print("Performing periodic data flush...")
                if mode == 3:
                    human_controller.bot.flush_data()
                else:
                    bot.flush_data()
                last_flush_time = current_time
    
    except KeyboardInterrupt:
        print("Controller stopped by user")
    
    except Exception as e:
        print(f"Error in main loop: {e}")
    
    finally:
        # Clean up
        if human_controller:
            human_controller.cleanup()
        
        # Make sure to flush any remaining data to CSV
        print("Flushing final data to CSV...")
        if mode == 3:
            human_controller.bot.flush_data()
        else:
            bot.flush_data()
            
        client_socket.close()
        print("Connection closed")

if __name__ == '__main__':
    main()