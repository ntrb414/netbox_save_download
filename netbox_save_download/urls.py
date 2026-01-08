from django.urls import path
from . import view

urlpatterns = [
    path('', view.SaveDownloadHomeView.as_view(), name='home'),
]
