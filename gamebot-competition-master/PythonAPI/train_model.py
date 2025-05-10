# Import necessary libraries
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report
from sklearn.utils.class_weight import compute_class_weight
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, Dropout
from tensorflow.keras.callbacks import EarlyStopping
from tensorflow.keras import regularizers
import joblib

# Step 1: Load and prepare the data
training_file_path = 'X:/6th Semester/Artificial Intelligence/AI Project/gamebot-competition-master/PythonAPI/GameDataUpdated.csv'
training_df = pd.read_csv(training_file_path)

# Define features and targets
features = [
    'player_x', 'player_y', 'opponent_x', 'opponent_y', 'distance', 'timer',
    'has_round_started', 'is_round_over', 'player_jumping', 'player_crouching',
    'player_in_move', 'player_move_id', 'opponent_jumping', 'opponent_crouching',
    'opponent_in_move', 'opponent_move_id'
]
targets = [
    'action_left', 'action_right', 'action_up', 'action_down',
    'action_A', 'action_B', 'action_X', 'action_Y'
]

# Extract features and targets
X = training_df[features].values
y = training_df[targets].values

# Step 2: Check class distribution
print("Class Distribution (Proportion of 'Pressed' for each action):")
print(training_df[targets].sum() / len(training_df))

# Step 3: Normalize the features and save the scaler
scaler = StandardScaler()
X = scaler.fit_transform(X)
joblib.dump(scaler, 'scaler.joblib')
print("Scaler saved as scaler.joblib")

# Step 4: Split the data
X_train, X_temp, y_train, y_temp = train_test_split(X, y, test_size=0.3, random_state=42)
X_val, X_test, y_val, y_test = train_test_split(X_temp, y_temp, test_size=0.5, random_state=42)

# Step 5: Manually oversample minority classes with adjusted factors
# Identify rows where rare buttons are pressed
minority_mask = (
    (y_train[:, targets.index('action_up')] == 1) |
    (y_train[:, targets.index('action_down')] == 1) |
    (y_train[:, targets.index('action_A')] == 1) |
    (y_train[:, targets.index('action_B')] == 1) |
    (y_train[:, targets.index('action_X')] == 1) |
    (y_train[:, targets.index('action_Y')] == 1)
)
minority_indices = np.where(minority_mask)[0]
minority_X = X_train[minority_indices]
minority_y = y_train[minority_indices]

# Oversample with adjusted factors
oversample_factors = {
    'action_up': 4,      # Reduce to decrease dominance
    'action_down': 6,    # Increase to balance with up
    'action_left': 6,    # Increase to balance with up
    'action_right': 6,   # Increase to balance with up
    'action_A': 12,      # Slightly increase to boost
    'action_B': 12,      # Slightly increase to boost
    'action_X': 8,       # Slightly increase to boost
    'action_Y': 8        # Slightly increase to boost
}
X_train_oversampled = X_train.copy()
y_train_oversampled = y_train.copy()
for target, factor in oversample_factors.items():
    indices = np.where(y_train[:, targets.index(target)] == 1)[0]
    X_target = X_train[indices]
    y_target = y_train[indices]
    X_train_oversampled = np.vstack([X_train_oversampled] + [X_target] * (factor - 1))
    y_train_oversampled = np.vstack([y_train_oversampled] + [y_target] * (factor - 1))

# Step 6: Compute class weights with custom multipliers
class_weights_dict = {}
weight_multipliers = {
    'action_left': 0.8,    # Moderate weight
    'action_right': 0.8,   # Moderate weight
    'action_up': 0.5,      # Reduce to decrease dominance
    'action_down': 1.2,    # Increase to balance with up
    'action_A': 3.5,       # Slightly increase to boost
    'action_B': 3.5,       # Slightly increase to boost
    'action_X': 1.8,       # Slightly increase to boost
    'action_Y': 1.8        # Slightly increase to boost
}

for i, target in enumerate(targets):
    classes = np.unique(y_train_oversampled[:, i])
    if len(classes) > 1:
        weights = compute_class_weight('balanced', classes=classes, y=y_train_oversampled[:, i])
        weights = weights / weights[0]  # Normalize "Not Pressed" to 1
        multiplier = weight_multipliers[target]
        class_weights_dict[i] = {cls: min(weight * multiplier, 5.0) for cls, weight in zip(classes, weights)}
    else:
        class_weights_dict[i] = {classes[0]: 1.0}

# Step 7: Create sample weights
sample_weights = np.ones(len(y_train_oversampled))
for j in range(len(y_train_oversampled)):
    max_weight = 1.0
    for i in range(y_train_oversampled.shape[1]):
        if len(class_weights_dict[i]) > 1:
            max_weight = max(max_weight, class_weights_dict[i].get(int(y_train_oversampled[j, i]), 1.0))
    sample_weights[j] = max_weight

# Step 8: Build the MLP model
model = Sequential([
    Dense(64, activation='relu', input_shape=(len(features),), kernel_initializer='he_normal',
          kernel_regularizer=regularizers.l2(0.01)),
    Dropout(0.5),
    Dense(32, activation='relu', kernel_initializer='he_normal',
          kernel_regularizer=regularizers.l2(0.01)),
    Dropout(0.5),
    Dense(16, activation='relu', kernel_initializer='he_normal',
          kernel_regularizer=regularizers.l2(0.01)),
    Dense(len(targets), activation='sigmoid', kernel_initializer='glorot_normal')
])

# Step 9: Compile the model
model.compile(optimizer=tf.keras.optimizers.Adam(learning_rate=0.001), 
              loss='binary_crossentropy', 
              metrics=['accuracy'])

# Step 10: Train the model
early_stopping = EarlyStopping(monitor='val_loss', patience=5, restore_best_weights=True)
history = model.fit(
    X_train_oversampled, y_train_oversampled,
    validation_data=(X_val, y_val),
    epochs=100,
    batch_size=32,
    sample_weight=sample_weights,
    callbacks=[early_stopping],
    verbose=1
)

# Step 11: Evaluate the model
y_pred_probs = model.predict(X_test)
y_pred_binary = (y_pred_probs > 0.2).astype(int)

print("\nClassification Report for Each Button:")
for i, target in enumerate(targets):
    classes = np.unique(y_test[:, i])
    target_names = [f'Not {target}' if c == 0 else target for c in classes]
    print(f"\n{target}:")
    print(classification_report(y_test[:, i], y_pred_binary[:, i], 
                               labels=classes, target_names=target_names, 
                               zero_division=0))

accuracies = [np.mean(y_test[:, i] == y_pred_binary[:, i]) for i in range(y_test.shape[1])]
average_accuracy = np.mean(accuracies)
print(f"\nAverage Accuracy Across All Buttons: {average_accuracy:.4f}")

# Step 12: Save the model
model.save('ShadowFightBotMLP.keras')
print("Model saved as ShadowFightBotMLP.keras")