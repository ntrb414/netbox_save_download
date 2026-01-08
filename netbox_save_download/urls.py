from django.urls import path
from . import view

urlpatterns = [
    path('', view.SaveDownloadHomeView.as_view(), name='home'),
    path('download/<int:pk>/', view.DownloadConfigView.as_view(), name='download_config'),
]
