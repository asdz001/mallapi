# mall_settings/views/site_settings.py

from django.shortcuts import render, redirect
from ..models import SiteSetting
from ..forms import SiteSettingForm

def site_settings_view(request):
    """
    🔧 쇼핑몰 기본 설정 페이지 뷰

    - 관리자 설정값을 DB에 저장 및 수정
    - 처음 접근 시 SiteSetting이 없으면 자동 생성
    - 이미지 미리보기를 위해 context에 site_settings 객체도 함께 전달
    """
    
    # ✅ DB에 SiteSetting 객체가 1개만 존재하는 구조
    setting = SiteSetting.objects.first()

    # 🔍 만약 아직 생성되지 않은 경우 기본 인스턴스를 만들어준다
    if not setting:
        setting = SiteSetting.objects.create()

    # ✅ POST 요청: 저장 처리
    if request.method == 'POST':
        form = SiteSettingForm(request.POST, request.FILES, instance=setting)
        if form.is_valid():
            form.save()
            return redirect('/dashboard/settings/site/') # 저장 후 다시 설정 페이지로 이동

    # ✅ GET 요청: 폼 데이터 표시
    else:
        form = SiteSettingForm(instance=setting)

    return render(request, 'dashboard/settings/site_settings.html', {
        'form': form,                   # 설정 폼
        'site_settings': setting,       # 이미지 미리보기 등을 위한 객체
    })
