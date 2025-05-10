import tensorflow as tf
import numpy as np
import joblib
import math
from command import Command
from buttons import Buttons

class NeuralBot:
    def __init__(self, model_path='StreetFighterBotMLP.keras', scaler_path='scaler.joblib'):
        """
        Initialize the Neural Network bot with the pre-trained model and scaler
        
        Args:
            model_path: Path to the saved Keras model
            scaler_path: Path to the saved scaler object
        """
        self.my_command = Command()
        self.buttons = Buttons()
        
        # Load the pre-trained model
        print(f"Loading model from {model_path}")
        try:
            self.model = tf.keras.models.load_model(model_path)
            print("Model loaded successfully")
        except Exception as e:
            print(f"Error loading model: {e}")
            raise
        
        # Load the scaler
        print(f"Loading scaler from {scaler_path}")
        try:
            self.scaler = joblib.load(scaler_path)
            print("Scaler loaded successfully")
        except Exception as e:
            print(f"Error loading scaler: {e}")
            raise
            
        # Define the feature names as used in training
        self.features = [
            'player_x', 'player_y', 'opponent_x', 'opponent_y', 'distance', 'timer',
            'has_round_started', 'is_round_over', 'player_jumping', 'player_crouching',
            'player_in_move', 'player_move_id', 'opponent_jumping', 'opponent_crouching',
            'opponent_in_move', 'opponent_move_id'
        ]
        
        # Define the target button names
        self.targets = [
            'action_left', 'action_right', 'action_up', 'action_down',
            'action_A', 'action_B', 'action_X', 'action_Y'
        ]
        
        # Per-button activation thresholds
        self.activation_thresholds = {
            'action_left': 0.25,    # Slightly lower to encourage use
            'action_right': 0.25,   # Slightly lower to encourage use
            'action_up': 0.35,      # Increase to reduce dominance
            'action_down': 0.25,    # Lower to balance with up
            'action_A': 0.15,       # Lower to boost
            'action_B': 0.15,       # Lower to boost
            'action_X': 0.20,       # Moderate threshold
            'action_Y': 0.20        # Moderate threshold
        }
        
        # Debug mode
        self.debug = False

    def fight(self, current_game_state, player):
        """
        Process the current game state and return commands based on neural network predictions
        
        Args:
            current_game_state: Current state of the game
            player: Player ID ('1' or '2')
            
        Returns:
            Command object with button presses
        """
        # Extract features based on player ID
        if player == "1":
            player_data = current_game_state.player1
            opponent_data = current_game_state.player2
        else:
            player_data = current_game_state.player2
            opponent_data = current_game_state.player1
        
        # Calculate distance between players
        distance = math.sqrt(
            (player_data.x_coord - opponent_data.x_coord) ** 2 + 
            (player_data.y_coord - opponent_data.y_coord) ** 2
        )
        
        # Prepare the feature vector
        X = [
            player_data.x_coord,                     # player_x
            player_data.y_coord,                     # player_y
            opponent_data.x_coord,                   # opponent_x
            opponent_data.y_coord,                   # opponent_y
            distance,                                # distance
            current_game_state.timer,                # timer
            1 if current_game_state.has_round_started else 0,  # has_round_started
            1 if current_game_state.is_round_over else 0,      # is_round_over
            1 if player_data.is_jumping else 0,      # player_jumping
            1 if player_data.is_crouching else 0,    # player_crouching
            1 if player_data.is_player_in_move else 0, # player_in_move
            player_data.move_id,                     # player_move_id
            1 if opponent_data.is_jumping else 0,    # opponent_jumping
            1 if opponent_data.is_crouching else 0,  # opponent_crouching
            1 if opponent_data.is_player_in_move else 0, # opponent_in_move
            opponent_data.move_id                    # opponent_move_id
        ]
        
        # Normalize the features using the saved scaler
        try:
            X_scaled = self.scaler.transform([X])
        except Exception as e:
            print(f"Error normalizing features: {e}")
            print(f"Feature vector: {X}")
            raise
        
        # Get model predictions
        try:
            predictions = self.model.predict(X_scaled, verbose=0)[0]
        except Exception as e:
            print(f"Error making predictions: {e}")
            raise
        
        if self.debug:
            # Print predictions for debugging
            for i, target in enumerate(self.targets):
                print(f"{target}: {predictions[i]:.4f}")
        
        # Apply per-button thresholds and convert to native Python types
        button_states = [
            1 if predictions[i] > self.activation_thresholds[target] else 0
            for i, target in enumerate(self.targets)
        ]
        button_states = [int(state) for state in button_states]  # Ensure Python int
        
        # Categorize buttons and enforce balance
        movement_buttons = button_states[:4]  # action_left, action_right, action_up, action_down
        action_buttons = button_states[4:]   # action_A, action_B, action_X, action_Y
        
        # Ensure at most one movement button is active
        movement_count = sum(1 for state in movement_buttons if state)
        if movement_count > 1:
            # Randomly select one movement button if multiple are active
            active_indices = [i for i, state in enumerate(movement_buttons) if state]
            if active_indices:
                chosen_index = np.random.choice(active_indices)
                movement_buttons = [1 if i == chosen_index else 0 for i in range(4)]
        
        # Ensure at least one action button is active if no movement
        if sum(movement_buttons) == 0 and sum(action_buttons) == 0:
            # Force at least one action button if no movement
            action_index = np.random.choice([i for i in range(4)]) + 4  # Random action (A, B, X, Y)
            action_buttons[action_index - 4] = 1
        
        # Combine balanced states
        button_states = movement_buttons + action_buttons
        
        # Set button states
        self.buttons.left = bool(button_states[0])
        self.buttons.right = bool(button_states[1])
        self.buttons.up = bool(button_states[2])
        self.buttons.down = bool(button_states[3])
        self.buttons.A = bool(button_states[4])
        self.buttons.B = bool(button_states[5])
        self.buttons.X = bool(button_states[6])
        self.buttons.Y = bool(button_states[7])
        
        # Assign buttons to the correct command based on player ID
        if player == "1":
            self.my_command.player_buttons = self.buttons
        else:
            self.my_command.player2_buttons = self.buttons
        
        return self.my_command

# For compatibility with the controller.py
Bot = NeuralBot