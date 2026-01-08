from django.shortcuts import render
from django.views.generic import View

class SaveDownloadHomeView(View):
    def get(self, request):
        return render(request, 'netbox_save_download/home.html')
