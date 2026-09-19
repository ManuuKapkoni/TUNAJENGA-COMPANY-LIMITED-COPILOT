from src.config import get_settings

settings = get_settings()

print ("GROK_API_KEY: ", settings.groq_api_key)
print ("GROK_MODEL: ",settings.groq_model)