import torch.nn as nn

class Aegis(nn.Module):
    def __init__(self):
        super().__init__()
        self.network = nn.Sequential(
            nn.Flatten(),           # 28x28 image → 784 numbers
            nn.Linear(784, 128),    # Layer 1
            nn.ReLU(),
            nn.Linear(128, 64),     # Layer 2
            nn.ReLU(),
            nn.Linear(64, 10)       # Output: 10 digits (0-9)
        )

    def forward(self, x):
        return self.network(x)