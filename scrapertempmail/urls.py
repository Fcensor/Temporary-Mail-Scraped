from django.urls import path
from . import views

urlpatterns = [
    path('inbox/', views.scrape_10minutemail, name='scrape_10minutemail'),
    path('email-content/', views.get_email_content, name='get_email_content'),  # Utilisez le bon nom de vue
    path('reset-email/', views.reset_email, name='get_email_content'),  # Utilisez le bon nom de vue
]
