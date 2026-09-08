# download_gliner.py
from gliner import GLiNER

# This will download the model to Hugging Face cache
# (~400-500MB download)
model = GLiNER.from_pretrained("urchade/gliner_medium-v2.1")

print("✅ Model downloaded and loaded successfully!")
print(f"Model loaded from: {model.model.config._name_or_path}")