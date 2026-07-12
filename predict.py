import torch
from torchvision import transforms
from PIL import Image
import sys
from model import Aegis

# 1. LOAD TRAINED AEGIS
model = Aegis()
model.load_state_dict(torch.load('aegis.pth'))
model.eval()

# 2. LOAD YOUR IMAGE
def predict(image_path):
    transform = transforms.Compose([
        transforms.Grayscale(),           # Make sure it's black & white
        transforms.Resize((28, 28)),      # Resize to 28x28 pixels
        transforms.ToTensor()             # Convert to numbers
    ])

    image = Image.open(image_path)
    image = transform(image).unsqueeze(0)  # Add batch dimension

    # 3. PREDICT
    with torch.no_grad():
        output = model(image)
        predicted = output.argmax(dim=1).item()
        confidence = torch.softmax(output, dim=1).max().item() * 100

    print(f"\nAegis thinks this is the number: {predicted}")
    print(f"Confidence: {confidence:.2f}%")

# Run it
if len(sys.argv) < 2:
    print("Usage: python predict.py your_image.png")
else:
    predict(sys.argv[1])