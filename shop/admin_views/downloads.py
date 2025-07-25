import os
from django.http import FileResponse, Http404
from django.conf import settings


def download_rawproduct_sample(request):
    file_path = os.path.join(settings.BASE_DIR, 'resources', 'rawproduct_sample.xlsx')
    if not os.path.exists(file_path):
        raise Http404("샘플파일이 존재하지 않습니다.")
    return FileResponse(open(file_path, 'rb'), as_attachment=True, filename='rawproduct_sample.xlsx')


def download_product_sample(request):
    file_path = os.path.join(settings.BASE_DIR, 'resources', 'product_sample.xlsx')
    if not os.path.exists(file_path):
        raise Http404("샘플파일이 존재하지 않습니다.")
    return FileResponse(open(file_path, 'rb'), as_attachment=True, filename='product_sample.xlsx')
