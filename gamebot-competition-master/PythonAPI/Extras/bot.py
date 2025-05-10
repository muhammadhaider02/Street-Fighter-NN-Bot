from command import Command
import numpy as np
from buttons import Buttons
import csv
import os
import time
from collections import deque

class Bot:
    def __init__(self, enable_logging=True, log_frequency=1, buffer_size=50):
        # Original bot code
        self.fire_code = ["<", "!<", "v+<", "!v+!<", "v", "!v", "v+>", "!v+!>", ">+Y", "!>+!Y"]
        self.exe_code = 0
        self.start_fire = True
        self.remaining_code = []
        self.my_command = Command()
        self.buttn = Buttons()
        
        # Performance settings
        self.enable_logging = enable_logging
        self.log_frequency = log_frequency
        self.buffer_size = buffer_size
        
        # Data collection setup
        self.csv_file = "GameData.csv"
        self.create_csv_if_not_exists()
        self.frame_counter = 0
        self.session_id = int(time.time())  # Unique session ID based on timestamp
        
        # Match tracking
        self.current_match_id = 0
        self.match_frames = []
        self.last_health_p1 = 100
        self.last_health_p2 = 100
        self.match_ended = False
        self.winner = None
        self.last_timer = 0
        self.last_write_time = time.time()
        self.write_interval = 1.0  # Write to disk more frequently (every 1 second)
        
        # Track previous button states to detect changes
        self.prev_p1_buttons = Buttons()
        self.prev_p2_buttons = Buttons()
        
        # Reduce print statements
        self.verbose = False
        
        print(f"Bot initialized with logging {'enabled' if enable_logging else 'disabled'}, frequency: every {log_frequency} frame(s), buffer size: {buffer_size}")

    def create_csv_if_not_exists(self):
        """Create the CSV file with headers if it doesn't exist"""
        headers = [
            'session_id', 'match_id', 'frame', 'timestamp',
            'player_id', 'opponent_id', 
            'player_health', 'opponent_health',
            'player_x', 'player_y', 
            'opponent_x', 'opponent_y',
            'distance', 
            # Group these fields consecutively as requested
            'timer', 'has_round_started', 'is_round_over', 'winner',
            'player_jumping', 'player_crouching',
            'player_in_move', 'player_move_id',
            'opponent_jumping', 'opponent_crouching',
            'opponent_in_move', 'opponent_move_id',
            # Player actions
            'action_left', 'action_right', 'action_up', 'action_down',
            'action_A', 'action_B', 'action_X', 'action_Y', 
            'action_L', 'action_R', 'action_select', 'action_start',
            # Opponent actions (new)
            'opponent_left', 'opponent_right', 'opponent_up', 'opponent_down',
            'opponent_A', 'opponent_B', 'opponent_X', 'opponent_Y',
            'opponent_L', 'opponent_R', 'opponent_select', 'opponent_start'
        ]
        
        file_exists = os.path.isfile(self.csv_file)
        
        if not file_exists:
            with open(self.csv_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(headers)
                print(f"Created new data file: {self.csv_file}")
        else:
            print(f"Appending to existing data file: {self.csv_file}")

    def check_match_end(self, game_state):
        """Check if a match has ended and determine the winner"""
        # Get current state
        p1_health = game_state.player1.health
        p2_health = game_state.player2.health
        timer = game_state.timer
        
        # Check for match end conditions
        match_ended = False
        winner = None
        
        # Check if health dropped to zero or below
        if p1_health <= 0 and p2_health > 0:
            match_ended = True
            winner = 2  # Player 2 wins
        elif p2_health <= 0 and p1_health > 0:
            match_ended = True
            winner = 1  # Player 1 wins
        # Check if timer reached zero
        elif timer <= 0 and self.last_timer > 0:
            match_ended = True
            if p1_health > p2_health:
                winner = 1  # Player 1 wins
            elif p2_health > p1_health:
                winner = 2  # Player 2 wins
            else:
                winner = 0  # Draw
        # Check for round over flag
        elif game_state.is_round_over:
            match_ended = True
            if p1_health > p2_health:
                winner = 1
            elif p2_health > p1_health:
                winner = 2
            else:
                winner = 0
        # Check for health reset (new match started)
        elif (p1_health == 100 and self.last_health_p1 < 100) or (p2_health == 100 and self.last_health_p2 < 100):
            match_ended = True
            # Determine winner based on last health values
            if self.last_health_p1 <= 0:
                winner = 2
            elif self.last_health_p2 <= 0:
                winner = 1
            elif self.last_health_p1 > self.last_health_p2:
                winner = 1
            elif self.last_health_p2 > self.last_health_p1:
                winner = 2
            else:
                winner = 0
        
        # Update last health values
        self.last_health_p1 = p1_health
        self.last_health_p2 = p2_health
        self.last_timer = timer
        
        # If match ended, save the result and prepare for next match
        if match_ended:
            self.match_ended = True
            self.winner = winner
            
            # Update winner for all frames in this match
            for frame in self.match_frames:
                frame[16] = winner  # Set the winner field (index 16)
            
            # Save match data
            self.save_match_data()
            
            # Reset for next match
            self.current_match_id += 1
            self.match_frames = []
            print(f"Match {self.current_match_id-1} ended. Winner: Player {winner if winner > 0 else 'Draw'}")
        
        return match_ended, winner

    def update_button_states(self, player_id, game_state):
        """Update button states for both players to ensure we capture all actions"""
        # For player 1
        if player_id == "1":
            # Store current button states for player 1
            self.my_command.player_buttons = self.buttn
            
            # For player 2, we need to infer button states from game state
            # This is a simplification - in a real game, we'd need more sophisticated detection
            p2 = game_state.player2
            p2_buttons = Buttons()
            
            # Detect movement based on position changes
            if p2.x_coord > game_state.player2.x_coord:
                p2_buttons.left = True
            elif p2.x_coord < game_state.player2.x_coord:
                p2_buttons.right = True
                
            # Detect jumping/crouching
            if p2.is_jumping:
                p2_buttons.up = True
            if p2.is_crouching:
                p2_buttons.down = True
                
            # Detect attacks based on move_id
            if p2.is_player_in_move and p2.move_id > 0:
                # This is a simplification - different move IDs would map to different buttons
                if p2.move_id % 6 == 0:
                    p2_buttons.A = True
                elif p2.move_id % 6 == 1:
                    p2_buttons.B = True
                elif p2.move_id % 6 == 2:
                    p2_buttons.X = True
                elif p2.move_id % 6 == 3:
                    p2_buttons.Y = True
                elif p2.move_id % 6 == 4:
                    p2_buttons.L = True
                elif p2.move_id % 6 == 5:
                    p2_buttons.R = True
            
            self.my_command.player2_buttons = p2_buttons
        
        # For player 2
        else:
            # Store current button states for player 2
            self.my_command.player2_buttons = self.buttn
            
            # For player 1, we need to infer button states from game state
            p1 = game_state.player1
            p1_buttons = Buttons()
            
            # Detect movement based on position changes
            if p1.x_coord > game_state.player1.x_coord:
                p1_buttons.left = True
            elif p1.x_coord < game_state.player1.x_coord:
                p1_buttons.right = True
                
            # Detect jumping/crouching
            if p1.is_jumping:
                p1_buttons.up = True
            if p1.is_crouching:
                p1_buttons.down = True
                
            # Detect attacks based on move_id
            if p1.is_player_in_move and p1.move_id > 0:
                # This is a simplification - different move IDs would map to different buttons
                if p1.move_id % 6 == 0:
                    p1_buttons.A = True
                elif p1.move_id % 6 == 1:
                    p1_buttons.B = True
                elif p1.move_id % 6 == 2:
                    p1_buttons.X = True
                elif p1.move_id % 6 == 3:
                    p1_buttons.Y = True
                elif p1.move_id % 6 == 4:
                    p1_buttons.L = True
                elif p1.move_id % 6 == 5:
                    p1_buttons.R = True
            
            self.my_command.player_buttons = p1_buttons

    def save_game_data(self, game_state, player, buttons, is_human=False):
        """Save the current game state and action to CSV"""
        # Always increment frame counter
        self.frame_counter += 1
        
        # IMPORTANT: We're removing the log_frequency check to ensure ALL frames are logged
        # This ensures we don't miss any actions
            
        # Determine which player we are and which is the opponent
        if player == "1":
            my_player = game_state.player1
            opponent = game_state.player2
            player_buttons = buttons if is_human else self.my_command.player_buttons
            opponent_buttons = self.my_command.player2_buttons
        else:
            my_player = game_state.player2
            opponent = game_state.player1
            player_buttons = buttons if is_human else self.my_command.player2_buttons
            opponent_buttons = self.my_command.player_buttons
        
        # Calculate distance between players
        distance = abs(my_player.x_coord - opponent.x_coord)
        
        # Check if match has ended
        match_ended, current_winner = self.check_match_end(game_state)
        
        # Prepare data row
        data = [
            self.session_id,                      # session_id
            self.current_match_id,                # match_id
            self.frame_counter,                   # frame
            time.time(),                          # timestamp
            my_player.player_id,                  # player_id
            opponent.player_id,                   # opponent_id
            my_player.health,                     # player_health
            opponent.health,                      # opponent_health
            my_player.x_coord,                    # player_x
            my_player.y_coord,                    # player_y
            opponent.x_coord,                     # opponent_x
            opponent.y_coord,                     # opponent_y
            distance,                             # distance
            # Group these fields consecutively as requested
            game_state.timer,                     # timer
            int(game_state.has_round_started),    # has_round_started
            int(game_state.is_round_over),        # is_round_over
            -1,                                   # winner (placeholder, will be updated)
            int(my_player.is_jumping),            # player_jumping
            int(my_player.is_crouching),          # player_crouching
            int(my_player.is_player_in_move),     # player_in_move
            my_player.move_id,                    # player_move_id
            int(opponent.is_jumping),             # opponent_jumping
            int(opponent.is_crouching),           # opponent_crouching
            int(opponent.is_player_in_move),      # opponent_in_move
            opponent.move_id,                     # opponent_move_id
            # Player actions
            int(player_buttons.left),             # action_left
            int(player_buttons.right),            # action_right
            int(player_buttons.up),               # action_up
            int(player_buttons.down),             # action_down
            int(player_buttons.A),                # action_A
            int(player_buttons.B),                # action_B
            int(player_buttons.X),                # action_X
            int(player_buttons.Y),                # action_Y
            int(player_buttons.L),                # action_L
            int(player_buttons.R),                # action_R
            int(player_buttons.select),           # action_select
            int(player_buttons.start),            # action_start
            # Opponent actions
            int(opponent_buttons.left),           # opponent_left
            int(opponent_buttons.right),          # opponent_right
            int(opponent_buttons.up),             # opponent_up
            int(opponent_buttons.down),           # opponent_down
            int(opponent_buttons.A),              # opponent_A
            int(opponent_buttons.B),              # opponent_B
            int(opponent_buttons.X),              # opponent_X
            int(opponent_buttons.Y),              # opponent_Y
            int(opponent_buttons.L),              # opponent_L
            int(opponent_buttons.R),              # opponent_R
            int(opponent_buttons.select),         # opponent_select
            int(opponent_buttons.start)           # opponent_start
        ]
        
        # Store frame data for this match
        self.match_frames.append(data)
        
        # Write to disk more frequently to ensure data is saved
        current_time = time.time()
        if match_ended or len(self.match_frames) >= self.buffer_size or (current_time - self.last_write_time) >= self.write_interval:
            self.save_match_data(keep_last=0 if match_ended else self.buffer_size // 8)  # Keep fewer frames in memory
            self.last_write_time = current_time

    def save_match_data(self, keep_last=0):
        """Save all frames from the current match with the winner information"""
        if not self.match_frames:
            return
            
        try:
            # Append to CSV
            with open(self.csv_file, 'a', newline='') as f:
                writer = csv.writer(f)
                
                if keep_last > 0 and len(self.match_frames) > keep_last:
                    # Write all except the last 'keep_last' frames
                    writer.writerows(self.match_frames[:-keep_last])
                    # Keep only the last 'keep_last' frames in memory
                    self.match_frames = self.match_frames[-keep_last:]
                else:
                    # Write all frames
                    writer.writerows(self.match_frames)
                    # Clear the frames list
                    self.match_frames = []
                
            if self.verbose:
                print(f"Saved frames for match {self.current_match_id}")
        except Exception as e:
            print(f"Error saving match data: {e}")
        
        # Reset match ended flag if this was called due to match end
        if keep_last == 0:
            self.match_ended = False

    def flush_data(self):
        """Flush any remaining data to the CSV file"""
        if self.match_frames:
            print(f"Flushing {len(self.match_frames)} remaining frames to CSV...")
            try:
                with open(self.csv_file, 'a', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerows(self.match_frames)
                self.match_frames = []
                print("Data flushed successfully")
            except Exception as e:
                print(f"Error flushing data: {e}")

    def human_fight(self, current_game_state, player, human_buttons):
        """Handle human-controlled fighting"""
        # For human control of player 1
        if player == "1":
            # Set the command buttons to the human buttons
            self.my_command.player_buttons = human_buttons
            
            # For player 2, we need to update button states based on game state
            p2 = current_game_state.player2
            p2_buttons = Buttons()
            
            # Detect movement based on position changes and state
            if p2.is_player_in_move:
                if p2.x_coord < self.prev_p2_x if hasattr(self, 'prev_p2_x') else p2.x_coord:
                    p2_buttons.left = True
                elif p2.x_coord > self.prev_p2_x if hasattr(self, 'prev_p2_x') else p2.x_coord:
                    p2_buttons.right = True
                
            # Detect jumping/crouching
            p2_buttons.up = p2.is_jumping
            p2_buttons.down = p2.is_crouching
            
            # Detect attacks based on move_id
            if p2.is_player_in_move and p2.move_id > 0:
                # Simple mapping of move_id to buttons
                move_type = p2.move_id % 6
                if move_type == 1:
                    p2_buttons.A = True
                elif move_type == 2:
                    p2_buttons.B = True
                elif move_type == 3:
                    p2_buttons.X = True
                elif move_type == 4:
                    p2_buttons.Y = True
                elif move_type == 5:
                    p2_buttons.L = True
                else:
                    p2_buttons.R = True
            
            # Store for next frame comparison
            self.prev_p2_x = p2.x_coord
            self.prev_p2_y = p2.y_coord
            self.my_command.player2_buttons = p2_buttons
        else:
            # Set player 2 buttons
            self.my_command.player2_buttons = human_buttons
            
            # For player 1, we need to update button states based on game state
            p1 = current_game_state.player1
            p1_buttons = Buttons()
            
            # Detect movement based on position changes and state
            if p1.is_player_in_move:
                if p1.x_coord < self.prev_p1_x if hasattr(self, 'prev_p1_x') else p1.x_coord:
                    p1_buttons.left = True
                elif p1.x_coord > self.prev_p1_x if hasattr(self, 'prev_p1_x') else p1.x_coord:
                    p1_buttons.right = True
                
            # Detect jumping/crouching
            p1_buttons.up = p1.is_jumping
            p1_buttons.down = p1.is_crouching
            
            # Detect attacks based on move_id
            if p1.is_player_in_move and p1.move_id > 0:
                # Simple mapping of move_id to buttons
                move_type = p1.move_id % 6
                if move_type == 1:
                    p1_buttons.A = True
                elif move_type == 2:
                    p1_buttons.B = True
                elif move_type == 3:
                    p1_buttons.X = True
                elif move_type == 4:
                    p1_buttons.Y = True
                elif move_type == 5:
                    p1_buttons.L = True
                else:
                    p1_buttons.R = True
            
            # Store for next frame comparison
            self.prev_p1_x = p1.x_coord
            self.prev_p1_y = p1.y_coord
            self.my_command.player_buttons = p1_buttons
            
        # Save the game data
        self.save_game_data(current_game_state, player, human_buttons, is_human=True)
            
        return self.my_command

    def fight(self, current_game_state, player, human_buttons=None):
        """Main fight function with support for human control"""
        # If human_buttons is provided, use human control
        if human_buttons is not None:
            return self.human_fight(current_game_state, player, human_buttons)
        
        # Original bot logic
        if player == "1":
            if self.exe_code != 0:
                self.run_command([], current_game_state.player1)
            diff = current_game_state.player2.x_coord - current_game_state.player1.x_coord
            if diff > 60:
                toss = np.random.randint(3)
                if toss == 0:
                    self.run_command([">", "-", "!>", "v+>", "-", "!v+!>", "v", "-", "!v", "v+<", "-", "!v+!<", "<+Y", "-", "!<+!Y"], current_game_state.player1)
                elif toss == 1:
                    self.run_command([">+^+B", ">+^+B", "!>+!^+!B"], current_game_state.player1)
                else:  # fire
                    self.run_command(["<", "-", "!<", "v+<", "-", "!v+!<", "v", "-", "!v", "v+>", "-", "!v+!>", ">+Y", "-", "!>+!Y"], current_game_state.player1)
            elif diff < -60:
                toss = np.random.randint(3)
                if toss == 0:  # spinning
                    self.run_command(["<", "-", "!<", "v+<", "-", "!v+!<", "v", "-", "!v", "v+>", "-", "!v+!>", ">+Y", "-", "!>+!Y"], current_game_state.player1)
                elif toss == 1:
                    self.run_command(["<+^+B", "<+^+B", "!<+!^+!B"], current_game_state.player1)
                else:  # fire
                    self.run_command([">", "-", "!>", "v+>", "-", "!v+!>", "v", "-", "!v", "v+<", "-", "!v+!<", "<+Y", "-", "!<+!Y"], current_game_state.player1)
            else:
                toss = np.random.randint(2)
                if toss >= 1:
                    if diff > 0:
                        self.run_command(["<", "<", "!<"], current_game_state.player1)
                    else:
                        self.run_command([">", ">", "!>"], current_game_state.player1)
                else:
                    self.run_command(["v+R", "v+R", "v+R", "!v+!R"], current_game_state.player1)
            self.my_command.player_buttons = self.buttn
            
            # Update opponent button states based on game state
            self.update_button_states(player, current_game_state)
            
            # Save data after deciding on an action
            self.save_game_data(current_game_state, player, self.buttn)

        elif player == "2":
            if self.exe_code != 0:
                self.run_command([], current_game_state.player2)
            diff = current_game_state.player1.x_coord - current_game_state.player2.x_coord
            if diff > 60:
                toss = np.random.randint(3)
                if toss == 0:
                    self.run_command([">", "-", "!>", "v+>", "-", "!v+!>", "v", "-", "!v", "v+<", "-", "!v+!<", "<+Y", "-", "!<+!Y"], current_game_state.player2)
                elif toss == 1:
                    self.run_command([">+^+B", ">+^+B", "!>+!^+!B"], current_game_state.player2)
                else:
                    self.run_command(["<", "-", "!<", "v+<", "-", "!v+!<", "v", "-", "!v", "v+>", "-", "!v+!>", ">+Y", "-", "!>+!Y"], current_game_state.player2)
            elif diff < -60:
                toss = np.random.randint(3)
                if toss == 0:
                    self.run_command(["<", "-", "!<", "v+<", "-", "!v+!<", "v", "-", "!v", "v+>", "-", "!v+!>", ">+Y", "-", "!>+!Y"], current_game_state.player2)
                elif toss == 1:
                    self.run_command(["<+^+B", "<+^+B", "!<+!^+!B"], current_game_state.player2)
                else:
                    self.run_command([">", "-", "!>", "v+>", "-", "!v+!>", "v", "-", "!v", "v+<", "-", "!v+!<", "<+Y", "-", "!<+!Y"], current_game_state.player2)
            else:
                toss = np.random.randint(2)
                if toss >= 1:
                    if diff < 0:
                        self.run_command(["<", "<", "!<"], current_game_state.player2)
                    else:
                        self.run_command([">", ">", "!>"], current_game_state.player2)
                else:
                    self.run_command(["v+R", "v+R", "v+R", "!v+!R"], current_game_state.player2)
            self.my_command.player2_buttons = self.buttn
            
            # Update opponent button states based on game state
            self.update_button_states(player, current_game_state)
            
            # Save data after deciding on an action
            self.save_game_data(current_game_state, player, self.buttn)

        return self.my_command

    def run_command(self, com, player):
        # Original run_command logic with reduced print statements
        if self.exe_code-1 == len(self.fire_code):
            self.exe_code = 0
            self.start_fire = False
            if self.verbose:
                print("complete")

        elif len(self.remaining_code) == 0:
            self.fire_code = com
            self.exe_code += 1
            self.remaining_code = self.fire_code[0:]

        else:
            self.exe_code += 1
            if self.remaining_code[0] == "v+<":
                self.buttn.down = True
                self.buttn.left = True
                if self.verbose: print("v+<")
            elif self.remaining_code[0] == "!v+!<":
                self.buttn.down = False
                self.buttn.left = False
                if self.verbose: print("!v+!<")
            elif self.remaining_code[0] == "v+>":
                self.buttn.down = True
                self.buttn.right = True
                if self.verbose: print("v+>")
            elif self.remaining_code[0] == "!v+!>":
                self.buttn.down = False
                self.buttn.right = False
                if self.verbose: print("!v+!>")

            elif self.remaining_code[0] == ">+Y":
                self.buttn.Y = True
                self.buttn.right = True
                if self.verbose: print(">+Y")
            elif self.remaining_code[0] == "!>+!Y":
                self.buttn.Y = False
                self.buttn.right = False
                if self.verbose: print("!>+!Y")

            elif self.remaining_code[0] == "<+Y":
                self.buttn.Y = True
                self.buttn.left = True
                if self.verbose: print("<+Y")
            elif self.remaining_code[0] == "!<+!Y":
                self.buttn.Y = False
                self.buttn.left = False
                if self.verbose: print("!<+!Y")

            elif self.remaining_code[0] == ">+^+L":
                self.buttn.right = True
                self.buttn.up = True
                self.buttn.L = not (player.player_buttons.L)
                if self.verbose: print(">+^+L")
            elif self.remaining_code[0] == "!>+!^+!L":
                self.buttn.right = False
                self.buttn.up = False
                self.buttn.L = False
                if self.verbose: print("!>+!^+!L")

            elif self.remaining_code[0] == ">+^+Y":
                self.buttn.right = True
                self.buttn.up = True
                self.buttn.Y = not (player.player_buttons.Y)
                if self.verbose: print(">+^+Y")
            elif self.remaining_code[0] == "!>+!^+!Y":
                self.buttn.right = False
                self.buttn.up = False
                self.buttn.Y = False
                if self.verbose: print("!>+!^+!Y")

            elif self.remaining_code[0] == ">+^+R":
                self.buttn.right = True
                self.buttn.up = True
                self.buttn.R = not (player.player_buttons.R)
                if self.verbose: print(">+^+R")
            elif self.remaining_code[0] == "!>+!^+!R":
                self.buttn.right = False
                self.buttn.up = False
                self.buttn.R = False
                if self.verbose: print("!>+!^+!R")

            elif self.remaining_code[0] == ">+^+A":
                self.buttn.right = True
                self.buttn.up = True
                self.buttn.A = not (player.player_buttons.A)
                if self.verbose: print(">+^+A")
            elif self.remaining_code[0] == "!>+!^+!A":
                self.buttn.right = False
                self.buttn.up = False
                self.buttn.A = False
                if self.verbose: print("!>+!^+!A")

            elif self.remaining_code[0] == ">+^+B":
                self.buttn.right = True
                self.buttn.up = True
                self.buttn.B = not (player.player_buttons.B)
                if self.verbose: print(">+^+B")
            elif self.remaining_code[0] == "!>+!^+!B":
                self.buttn.right = False
                self.buttn.up = False
                self.buttn.B = False
                if self.verbose: print("!>+!^+!B")

            elif self.remaining_code[0] == "<+^+L":
                self.buttn.left = True
                self.buttn.up = True
                self.buttn.L = not (player.player_buttons.L)
                if self.verbose: print("<+^+L")
            elif self.remaining_code[0] == "!<+!^+!L":
                self.buttn.left = False
                self.buttn.up = False
                self.buttn.L = False
                if self.verbose: print("!<+!^+!L")

            elif self.remaining_code[0] == "<+^+Y":
                self.buttn.left = True
                self.buttn.up = True
                self.buttn.Y = not (player.player_buttons.Y)
                if self.verbose: print("<+^+Y")
            elif self.remaining_code[0] == "!<+!^+!Y":
                self.buttn.left = False
                self.buttn.up = False
                self.buttn.Y = False
                if self.verbose: print("!<+!^+!Y")

            elif self.remaining_code[0] == "<+^+R":
                self.buttn.left = True
                self.buttn.up = True
                self.buttn.R = not (player.player_buttons.R)
                if self.verbose: print("<+^+R")
            elif self.remaining_code[0] == "!<+!^+!R":
                self.buttn.left = False
                self.buttn.up = False
                self.buttn.R = False
                if self.verbose: print("!<+!^+!R")

            elif self.remaining_code[0] == "<+^+A":
                self.buttn.left = True
                self.buttn.up = True
                self.buttn.A = not (player.player_buttons.A)
                if self.verbose: print("<+^+A")
            elif self.remaining_code[0] == "!<+!^+!A":
                self.buttn.left = False
                self.buttn.up = False
                self.buttn.A = False
                if self.verbose: print("!<+!^+!A")

            elif self.remaining_code[0] == "<+^+B":
                self.buttn.left = True
                self.buttn.up = True
                self.buttn.B = not (player.player_buttons.B)
                if self.verbose: print("<+^+B")
            elif self.remaining_code[0] == "!<+!^+!B":
                self.buttn.left = False
                self.buttn.up = False
                self.buttn.B = False
                if self.verbose: print("!<+!^+!B")

            elif self.remaining_code[0] == "v+R":
                self.buttn.down = True
                self.buttn.R = not (player.player_buttons.R)
                if self.verbose: print("v+R")
            elif self.remaining_code[0] == "!v+!R":
                self.buttn.down = False
                self.buttn.R = False
                if self.verbose: print("!v+!R")

            else:
                if self.remaining_code[0] == "v":
                    self.buttn.down = True
                    if self.verbose: print("down")
                elif self.remaining_code[0] == "!v":
                    self.buttn.down = False
                    if self.verbose: print("Not down")
                elif self.remaining_code[0] == "<":
                    self.buttn.left = True
                    if self.verbose: print("left")
                elif self.remaining_code[0] == "!<":
                    self.buttn.left = False
                    if self.verbose: print("Not left")
                elif self.remaining_code[0] == ">":
                    self.buttn.right = True
                    if self.verbose: print("right")
                elif self.remaining_code[0] == "!>":
                    self.buttn.right = False
                    if self.verbose: print("Not right")
                elif self.remaining_code[0] == "^":
                    self.buttn.up = True
                    if self.verbose: print("up")
                elif self.remaining_code[0] == "!^":
                    self.buttn.up = False
                    if self.verbose: print("Not up")
                elif self.remaining_code[0] == "-":
                    # This is just a delay, do nothing
                    pass
            self.remaining_code = self.remaining_code[1:]
        return
