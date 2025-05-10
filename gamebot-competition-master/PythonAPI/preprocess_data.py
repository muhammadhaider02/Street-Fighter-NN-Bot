import pandas as pd
import numpy as np
import os
import glob
import math
import argparse

def preprocess_game_data(input_file, output_file=None):
    """
    Preprocess the raw game data collected by controller.py to match the format used in training.
    
    Args:
        input_file: Path to the raw game data CSV file
        output_file: Path to save the processed data (default: GameDataProcessed.csv)
    """
    if output_file is None:
        output_file = "GameDataProcessed.csv"
    
    print(f"Loading data from {input_file}...")
    df = pd.read_csv(input_file)
    
    # Create new dataframe with required features
    processed_data = []
    
    print("Processing data...")
    for i, row in df.iterrows():
        # Calculate distance between players
        distance = math.sqrt((row['player_x'] - row['opponent_x'])**2 + 
                            (row['player_y'] - row['opponent_y'])**2)
        
        # Convert boolean values to integers
        has_round_started = 1 if row['has_round_started'] else 0
        is_round_over = 1 if row['is_round_over'] else 0
        
        player_jumping = 1 if row['player_jumping'] else 0
        player_crouching = 1 if row['player_crouching'] else 0
        player_in_move = 1 if row['player_in_move'] else 0
        
        opponent_jumping = 1 if row['opponent_jumping'] else 0
        opponent_crouching = 1 if row['opponent_crouching'] else 0
        opponent_in_move = 1 if row['opponent_in_move'] else 0
        
        # Create new row with processed data
        processed_row = {
            'player_x': row['player_x'],
            'player_y': row['player_y'],
            'opponent_x': row['opponent_x'],
            'opponent_y': row['opponent_y'],
            'distance': distance,
            'timer': row['timer'],
            'has_round_started': has_round_started,
            'is_round_over': is_round_over,
            'winner': row['winner'],
            'player_jumping': player_jumping,
            'player_crouching': player_crouching,
            'player_in_move': player_in_move,
            'player_move_id': row['player_move_id'],
            'opponent_jumping': opponent_jumping,
            'opponent_crouching': opponent_crouching,
            'opponent_in_move': opponent_in_move,
            'opponent_move_id': row['opponent_move_id'],
            'action_left': row['action_left'],
            'action_right': row['action_right'],
            'action_up': row['action_up'],
            'action_down': row['action_down'],
            'action_A': row['action_A'],
            'action_B': row['action_B'],
            'action_X': row['action_X'],
            'action_Y': row['action_Y'],
            'opponent_left': row['opponent_left'],
            'opponent_right': row['opponent_right'],
            'opponent_up': row['opponent_up'],
            'opponent_down': row['opponent_down'],
            'opponent_A': row['opponent_A'],
            'opponent_B': row['opponent_B'],
            'opponent_X': row['opponent_X'],
            'opponent_Y': row['opponent_Y']
        }
        
        processed_data.append(processed_row)
    
    # Create DataFrame from processed data
    processed_df = pd.DataFrame(processed_data)
    
    # Save to CSV
    processed_df.to_csv(output_file, index=False)
    print(f"Processed data saved to {output_file}")
    
    # Print summary statistics
    print("\nData Summary:")
    print(f"Total samples: {len(processed_df)}")
    print("\nButton Press Distribution:")
    for button in ['action_left', 'action_right', 'action_up', 'action_down', 
                  'action_A', 'action_B', 'action_X', 'action_Y']:
        press_percentage = processed_df[button].mean() * 100
        print(f"{button}: {press_percentage:.2f}% pressed")
    
    return processed_df

def combine_multiple_files(pattern, output_file):
    """
    Combine multiple game data files into a single processed file
    
    Args:
        pattern: Glob pattern to match input files (e.g. 'game_data_*.csv')
        output_file: Path to save the combined processed data
    """
    # Find all files matching the pattern
    input_files = glob.glob(pattern)
    
    if not input_files:
        print(f"No files found matching pattern: {pattern}")
        return
    
    print(f"Found {len(input_files)} files to process")
    
    all_processed_data = []
    
    # Process each file
    for i, file in enumerate(input_files):
        print(f"Processing file {i+1}/{len(input_files)}: {file}")
        # Process file but don't save yet
        df = preprocess_game_data(file, output_file=None)
        all_processed_data.append(df)
    
    # Combine all processed data
    combined_df = pd.concat(all_processed_data, ignore_index=True)
    
    # Save combined data
    combined_df.to_csv(output_file, index=False)
    print(f"Combined processed data saved to {output_file}")
    
    # Print summary statistics
    print("\nCombined Data Summary:")
    print(f"Total samples: {len(combined_df)}")
    print("\nButton Press Distribution:")
    for button in ['action_left', 'action_right', 'action_up', 'action_down', 
                  'action_A', 'action_B', 'action_X', 'action_Y']:
        press_percentage = combined_df[button].mean() * 100
        print(f"{button}: {press_percentage:.2f}% pressed")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Preprocess game data for neural network training')
    parser.add_argument('--input', type=str, help='Input file or glob pattern (e.g., "game_data_*.csv")')
    parser.add_argument('--output', type=str, default='GameDataProcessed.csv', 
                        help='Output file path (default: GameDataProcessed.csv)')
    parser.add_argument('--combine', action='store_true', 
                        help='Combine multiple files matching the input pattern')
    
    args = parser.parse_args()
    
    if args.input is None:
        # No args, use GUI dialog if available
        try:
            import tkinter as tk
            from tkinter import filedialog, messagebox
            
            root = tk.Tk()
            root.withdraw()
            
            input_path = filedialog.askopenfilename(
                title="Select Game Data File",
                filetypes=(("CSV files", "*.csv"), ("All files", "*.*"))
            )
            
            if input_path:
                preprocess_game_data(input_path, args.output)
            else:
                print("No file selected. Exiting.")
        except ImportError:
            print("Please specify an input file with --input")
    else:
        if args.combine:
            combine_multiple_files(args.input, args.output)
        else:
            preprocess_game_data(args.input, args.output) 