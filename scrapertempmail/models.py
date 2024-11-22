from django.db import models

class SessionInfo(models.Model):
    phpsessid = models.CharField(max_length=255, unique=True)
    email = models.EmailField()
    ip_address = models.GenericIPAddressField()
    start_time = models.DateTimeField(auto_now_add=True)
    count = models.IntegerField(default=1)


class EmailMessage(models.Model):
    session = models.ForeignKey('SessionInfo', on_delete=models.CASCADE)
    sender = models.CharField(max_length=255)
    subject = models.CharField(max_length=255)
    date = models.CharField(max_length=255)
    link = models.URLField(null=True, blank=True)
    content = models.TextField(null=True, blank=True)  # Champ pour le contenu brut de l'email
