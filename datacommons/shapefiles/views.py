from django.contrib.auth.decorators import login_required
from datacommons.importable.views import upload as upload_view, preview as preview_view
from .forms import ShapefileUploadForm, ShapefilePreviewForm

@login_required
def upload(request):
    return upload_view(request, ShapefileUploadForm, 'shapefile/upload.html', 'shapefile-preview', filetype="Shapefile")

@login_required
def preview(request):
    return preview_view(request, ShapefilePreviewForm, 'shapefile/preview.html')
