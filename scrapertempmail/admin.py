from django.contrib import admin
from .models import SessionInfo, EmailMessage

# Enregistrement simple des modèles
admin.site.register(SessionInfo)
admin.site.register(EmailMessage)
