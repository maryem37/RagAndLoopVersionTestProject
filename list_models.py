import os
from google.genai import Client

# Charge la clé depuis l'environnement
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GEMINI_API_KEY n'est pas défini !")

# Initialise le client
client = Client(api_key=api_key)

# Modèle que tu veux tester
model_name = "gemini-2.5-flash"

# Appel simple pour générer du texte
response = client.models.generate_content(
    model=model_name,
    contents="Bonjour ! Peux‑tu me répondre juste avec 'API OK' ?"
)

print("Réponse du modèle :")
print(response.text)
