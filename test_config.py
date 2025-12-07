from server.config import settings
print(f"Loaded Settings: {settings.APP_NAME} in {settings.ENV} mode")
print(f"CORS: {settings.CORS_ORIGINS}")
print(f"Media Dir: {settings.MEDIA_DIR}")
