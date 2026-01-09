from django.urls import path
from . import view

urlpatterns = [
    path('', view.SaveDownloadHomeView.as_view(), name='home'),
    path('download/<str:ip>/', view.DownloadConfigView.as_view(), name='download_config'),
]
