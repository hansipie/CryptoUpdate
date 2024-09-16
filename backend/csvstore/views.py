
import logging
from django.shortcuts import render
from django.http import HttpResponseRedirect
from .forms import UploadFileForm
from .core import handle_uploaded_file

logger = logging.getLogger(__name__)

def upload(request):
    if request.method == 'POST':
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            logger.debug(f"Le formulaire est valide : {form.cleaned_data}")
            handle_uploaded_file(request.FILES['file'])
            return HttpResponseRedirect('/csvstore/success/url/')
    else:
        form = UploadFileForm()
    return render(request, 'upload.html', {'form': form})

def success(request):
    return render(request, 'success.html')
