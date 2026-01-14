from django.urls import path
from . import view

app_name = 'netbox_save_download'

urlpatterns = [
    path('', view.SaveDownloadHomeView.as_view(), name='home'),
    path('download/<str:ip>/', view.DownloadConfigView.as_view(), name='download_config'),
    path('read_ip_file/', view.ReadIPFileView.as_view(), name='read_ip_file'),
]
