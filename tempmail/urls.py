from django.contrib import admin
from django.urls import path, include  # Ajouter include pour inclure les URLs des applications

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('scrapertempmail.urls')),  # Inclure les URLs de l'application 'scraper'
]
