# notifier/urls.py

from django.urls import path
from .views import NotifyTelegramView

urlpatterns = [
    path('notify/', NotifyTelegramView.as_view()),
]
