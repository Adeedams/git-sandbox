import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

# Set random seeds so your results are reproducible every time
torch.manual_seed(42)
np.random.seed(42)

# ==========================================
# 1. LOAD & SPLIT THE 27-RUN FEA DATASET
# ==========================================
df = pd.read_csv("bga_doe_dataset.csv")

X = df[["h_fr4_mm", "h_si_mm", "uf_modulus_MPa"]].values
y = df[["warpage_um", "max_solder_stress_MPa"]].values

# Hold back 6 unseen runs (~22%) to test real generalization
X_train_raw, X_test_raw, y_train_raw, y_test_raw = train_test_split(
    X, y, test_size=6, random_state=42
)

# ==========================================
# 2. NORMALIZE INPUTS & OUTPUTS
# ==========================================
scaler_X = StandardScaler()
scaler_y = StandardScaler()

X_train = torch.tensor(scaler_X.fit_transform(X_train_raw), dtype=torch.float32)
y_train = torch.tensor(scaler_y.fit_transform(y_train_raw), dtype=torch.float32)

X_test = torch.tensor(scaler_X.transform(X_test_raw), dtype=torch.float32)
y_test = torch.tensor(scaler_y.transform(y_test_raw), dtype=torch.float32)

# ==========================================
# 3. DEFINE THE PYTORCH NEURAL NETWORK
# ==========================================
model = nn.Sequential(
    nn.Linear(3, 32),   # 3 inputs: h_fr4, h_si, uf_modulus
    nn.ReLU(),
    nn.Linear(32, 32),  # Hidden physics interaction layer
    nn.ReLU(),
    nn.Linear(32, 2),   # 2 outputs: warpage_um, max_solder_stress_MPa
)

criterion = nn.MSELoss()
optimizer = torch.optim.Adam(model.parameters(), lr=0.01)
# ==========================================
# 4. TRAIN THE SURROGATE MODEL (800 Epochs)
# ==========================================
epochs = 800
train_losses = []

for epoch in range(1, epochs + 1):
    model.train()
    optimizer.zero_grad()

    predictions = model(X_train)
    loss = criterion(predictions, y_train)
    loss.backward()
    optimizer.step()

    train_losses.append(loss.item())
    if epoch % 200 == 0:
        print(f"Epoch {epoch:03d}/{epochs} | Scaled Training MSE Loss: {loss.item():.5f}")

# ==========================================
# 5. EVALUATE ON 6 UNSEEN TEST DESIGNS
# ==========================================
model.eval()
with torch.no_grad():
    y_test_pred_scaled = model(X_test).numpy()
    y_test_pred = scaler_y.inverse_transform(y_test_pred_scaled)

warpage_mae = np.mean(np.abs(y_test_raw[:, 0] - y_test_pred[:, 0]))
stress_mae = np.mean(np.abs(y_test_raw[:, 1] - y_test_pred[:, 1]))

print("\n--- UNSEEN TEST SET ACCURACY (6 Held-Out FEA Runs) ---")
print(f"Mean Absolute Error (Warpage):      {warpage_mae:.2f} microns")
print(f"Mean Absolute Error (Solder Stress): {stress_mae:.2f} MPa\n")

print(f"{'h_fr4':<6} | {'h_si':<6} | {'E_uf':<8} | {'FEA Warp':<10} | {'AI Warp':<10} | {'FEA Stress':<11} | {'AI Stress'}")
print("-" * 74)
for inp, actual, pred in zip(X_test_raw, y_test_raw, y_test_pred):
    print(
        f"{inp[0]:<6.2f} | {inp[1]:<6.2f} | {inp[2]:<8.0f} | "
        f"{actual[0]:<10.2f} | {pred[0]:<10.2f} | {actual[1]:<11.1f} | {pred[1]:.1f}"
    )

# ==========================================
# 6. INSTANT PREDICTION ON A BRAND-NEW DESIGN
# ==========================================
new_design = np.array([[0.75, 0.20, 11000.0]])  # Never simulated in CalculiX!
new_design_scaled = torch.tensor(scaler_X.transform(new_design), dtype=torch.float32)

with torch.no_grad():
    new_pred = scaler_y.inverse_transform(model(new_design_scaled).numpy())[0]

print("\n--- INSTANT AI INFERENCE (< 1 millisecond) ---")
print(f"New Design (h_fr4=0.75mm, h_si=0.20mm, E_uf=11000 MPa):")
print(f"Predicted Warpage:      {new_pred[0]:.2f} microns")
print(f"Predicted Solder Stress: {new_pred[1]:.1f} MPa")

# ==========================================
# 7. SAVE PARITY PLOT (Actual FEA vs. AI Surrogate)
# ==========================================
with torch.no_grad():
    all_pred = scaler_y.inverse_transform(model(torch.tensor(scaler_X.transform(X), dtype=torch.float32)).numpy())

fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))

# Left Panel: Warpage Parity
axes[0].scatter(y[:, 0], all_pred[:, 0], color="#1f77b4", label="Training Data (21 runs)", alpha=0.8)
axes[0].scatter(y_test_raw[:, 0], y_test_pred[:, 0], color="#d62728", s=70, label="Unseen Test Data (6 runs)")
lims_w = [min(y[:, 0]) - 3, max(y[:, 0]) + 3]
axes[0].plot(lims_w, lims_w, "k--", lw=1.2, label="Perfect 1:1 Match")
axes[0].set_title("Package Warpage: 3D FEA vs. PyTorch AI")
axes[0].set_xlabel("Actual CalculiX Warpage (microns)")
axes[0].set_ylabel("PyTorch Predicted Warpage (microns)")
axes[0].legend()
axes[0].grid(True, alpha=0.3)

# Right Panel: Solder Stress Parity
axes[1].scatter(y[:, 1], all_pred[:, 1], color="#2ca02c", label="Training Data (21 runs)", alpha=0.8)
axes[1].scatter(y_test_raw[:, 1], y_test_pred[:, 1], color="#d62728", s=70, label="Unseen Test Data (6 runs)")
lims_s = [min(y[:, 1]) - 3, max(y[:, 1]) + 3]
axes[1].plot(lims_s, lims_s, "k--", lw=1.2, label="Perfect 1:1 Match")
axes[1].set_title("Max Solder Stress: 3D FEA vs. PyTorch AI")
axes[1].set_xlabel("Actual CalculiX Stress (MPa)")
axes[1].set_ylabel("PyTorch Predicted Stress (MPa)")
axes[1].legend()
axes[1].grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig("surrogate_accuracy.png", dpi=200)
print("\nSaved parity plot to surrogate_accuracy.png!")
