import os
# Force DeepXDE to use your newly installed PyTorch engine
os.environ["DDE_BACKEND"] = "pytorch"

import deepxde as dde
import torch

print("\n--- 🔬 Physics Stack Verification 🔬 ---")
print(f"DeepXDE Version: {dde.__version__}")
print(f"PyTorch Version: {torch.__version__}")
print(f"Active Backend : {dde.backend.backend_name}")
print("---------------------------------------\n")
