import torch
from torchvision import datasets, transforms
from torch.utils.data import DataLoader
from model import Aegis

# 1. LOAD TEST DATA
transform = transforms.ToTensor()

print("Loading test data...")
test_data = datasets.MNIST(root='./data', train=False, download=True, transform=transform)
test_loader = DataLoader(test_data, batch_size=64, shuffle=False)

# 2. LOAD TRAINED AEGIS
model = Aegis()
model.load_state_dict(torch.load('aegis.pth'))
model.eval()
print("Aegis brain loaded!\n")

# 3. TEST
correct = 0
total = 0

with torch.no_grad():
    for images, labels in test_loader:
        predictions = model(images)
        predicted_digits = predictions.argmax(dim=1)
        correct += (predicted_digits == labels).sum().item()
        total += labels.size(0)

accuracy = 100 * correct / total
print(f"Aegis got {correct} out of {total} correct")
print(f"Accuracy: {accuracy:.2f}%")