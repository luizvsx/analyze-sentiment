import os
from pathlib import Path
from dotenv import load_dotenv

# Pasta raiz do projeto: fase_1_app/
BASE_DIR = Path(__file__).resolve().parent.parent

# Localização do .env
ENV_PATH = BASE_DIR / ".env"

# Carrega as variáveis de ambiente
load_dotenv(dotenv_path=ENV_PATH, override=False)

# Chave da API Gemini
API_KEY = os.getenv("GEMINI_API_KEY")

# Configuração do modo mock
MOCK_GEMINI_SERVICE = (
    os.getenv("MOCK_GEMINI_SERVICE", "False").strip().lower() == "true"
)

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
MONGODB_DATABASE = os.getenv("MONGODB_DATABASE", "local")
