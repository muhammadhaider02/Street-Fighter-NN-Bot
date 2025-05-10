# Street Fighter Neural Network Bot

This project implements a neural network-based bot for Street Fighter using a Multi-Layer Perceptron (MLP) model. The bot learns from gameplay data to predict optimal button presses based on the current game state, resulting in more adaptive and human-like gameplay.

## Project Structure

```
ROOT DIRECTORY
-------------
├── controller.py              # Main controller for rule-based data collection
├── nn_controller.py          # Neural network bot controller
├── nn_bot.py                 # Neural network bot implementation
├── train_model.py            # Model training script
├── preprocess_data.py        # Data preprocessing utilities
├── bot.py                    # Rule-based bot implementation
├── buttons.py                # Button definitions and utilities
├── command.py                # Command handling utilities
├── game_state.py             # Game state definitions
├── player.py                 # Player state definitions
├── requirements.txt          # Project dependencies
└── README.md                 # Project documentation

EXTRAS DIRECTORY
---------------
├── bot.py                    # Human gameplay data collection bot
├── controller.py             # Human gameplay data collection controller
└── Neural_Network_GameBot_Report.pdf  # Project documentation
```

## Features

- Neural network-based gameplay prediction
- Data collection from both rule-based and human gameplay
- Real-time game state processing
- Adaptive button press prediction
- Support for all game controls (movement and action buttons)
- Configurable activation thresholds for different buttons

## Requirements

- Python 3.8+
- TensorFlow 2.8.0+
- NumPy 1.21.0+
- Pandas 1.3.0+
- scikit-learn 0.24.2+
- joblib 1.1.0+
- matplotlib 3.4.3+
- seaborn 0.11.2+
- keyboard 0.13.5+

## Installation

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Data Collection

1. For rule-based data collection:
   - Use the `controller.py` in the main folder
   - This will generate data using the rule-based bot

2. For human gameplay data collection:
   - Replace the original `controller.py` and `bot.py` with those in the Extras folder
   - Play the game normally to collect data
   - The data will be saved in CSV format

3. Merge all collected data:
   - Combine all CSV files into a single dataset for training

### Model Training

1. Preprocess the data:
   ```bash
   python preprocess_data.py
   ```

2. Train the model:
   ```bash
   python train_model.py
   ```
   The trained model will be saved as `StreetFighterBotMLP.keras`

### Running the Bot

1. Start the neural network bot:
   ```bash
   python nn_controller.py
   ```

2. The bot will use:
   - The trained model (`StreetFighterBotMLP.keras`)
   - The feature scaler (`scaler.joblib`)
   - Real-time game state processing

## Model Architecture

The neural network uses a Multi-Layer Perceptron (MLP) architecture:

- Input layer: 16 neurons (game state features)
- Hidden layers: 64 neurons, 32 neurons
- Output layer: 8 neurons (one for each button)
- Activation functions: ReLU (hidden layers), Sigmoid (output layer)
- Loss function: Binary cross-entropy
- Optimizer: Adam

## Button Activation Thresholds

The bot uses different activation thresholds for different buttons:

- Movement buttons (left, right): 0.25
- Movement buttons (up, down): 0.25-0.35
- Action buttons (A, B): 0.15
- Action buttons (X, Y): 0.20

These thresholds can be adjusted in `nn_bot.py` to modify the bot's behavior.

## Performance

The model achieves:
- Average accuracy across all buttons: 73.42%
- Strong performance on movement predictions
- Good balance between aggression and defense
- Human-like gameplay patterns

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a new Pull Request

## Acknowledgments

- Thanks to all contributors who helped with data collection
- Special thanks to the game development community for inspiration
