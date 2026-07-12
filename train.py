import torch
import torch.nn as nn
import torch.optim as optim
from torchvision import datasets, transforms
from torch.utils.data import DataLoader
from model import Aegis

# 1. LOAD DATA
transform = transforms.ToTensor()

print("Loading data...")
train_data = datasets.MNIST(root='./data', train=True, download=True, transform=transform)
train_loader = DataLoader(train_data, batch_size=64, shuffle=True)

# 2. LOAD AEGIS
model = Aegis()
print("Aegis brain loaded!\n")

# 3. SET UP TRAINING
loss_fn   = nn.CrossEntropyLoss()
optimizer = optim.Adam(model.parameters(), lr=0.001)

# 4. TRAIN
epochs = 5

print("Training started...\n")
for epoch in range(epochs):
    model.train()
    total_loss = 0

    for images, labels in train_loader:
        optimizer.zero_grad()
        predictions = model(images)
        loss = loss_fn(predictions, labels)
        loss.backward()
        optimizer.step()
        total_loss += loss.item()

    print(f"Epoch {epoch+1}/5 — Loss: {total_loss/len(train_loader):.4f}")

# 5. SAVE TRAINED BRAIN
torch.save(model.state_dict(), 'aegis.pth')
print("\nAegis has been trained and saved to aegis.pth!")