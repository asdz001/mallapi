# shop_product/views/product_add.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.contrib import messages
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.utils.translation import gettext_lazy as _
from shop.models import Product
from pricing.models import Retailer, FixedCountry, CountryAlias
from dictionary.models import CategoryLevel1, CategoryLevel2, CategoryLevel3, CategoryLevel4 ,Brand
import pandas as pd
import json
import os
from PIL import Image
from io import BytesIO
import requests

# ========================================
# 🔧 상품등록 설정
# ========================================

# 📋 등록 방식 선택
REGISTER_TYPES = [
    ('manual', _('일반등록')),
    ('excel', _('엑셀등록')),
]

# 📂 이미지 업로드 설정
IMAGE_UPLOAD_SETTINGS = {
    'max_size': 5 * 1024 * 1024,  # 5MB
    'allowed_formats': ['JPEG', 'JPG', 'PNG', 'WEBP'],
    'max_width': 2000,
    'max_height': 2000,
    'upload_path': 'products/images/',
}

# 📊 엑셀 업로드 설정
EXCEL_SETTINGS = {
    'max_size': 10 * 1024 * 1024,  # 10MB
    'allowed_extensions': ['.xlsx', '.xls'],
    'max_rows': 1000,  # 한번에 최대 1000개 상품
}

# 📋 Product 모델 필수/선택 필드 정의 (업데이트된 요구사항 기준)
PRODUCT_FIELD_CONFIG = {
    # 필수 필드
    'required_fields': ['external_product_id', 'product_name', 'sku'],
    
    # 토글 선택 필드 (관계 테이블에서 선택)
    'toggle_fields': {
        'retailer': {'name': '부띠끄', 'model': Retailer, 'field': 'name'},
        'brand_name': {'name': '브랜드', 'model': Brand, 'field': 'name'},  # 브랜드 모델 확인 필요
        'gender': {'name': '성별', 'model': CategoryLevel1, 'field': 'name'},
        'category1': {'name': '카테고리1', 'model': CategoryLevel2, 'field': 'name'},
        'category2': {'name': '카테고리2', 'model': CategoryLevel3, 'field': 'name'},
    },
    
    # 텍스트 필드
    'text_fields': [
        'external_product_id',  # 고유상품 ID (필수)
        'product_name',         # 상품명 (필수)
        'sku',                 # SKU (필수)
        'season',              # 시즌
        'color',               # 색상명
        'origin',              # 원산지
        'material',            # 소재
        'description',         # 설명
        'status',              # 상태
    ],
    
    # 가격 필드 (숫자)
    'price_fields': [
        'price_org',              # COST
        'discount_rate',          # 할인율(%)
        'price_retail',           # 소비자가(euro)
        'manual_price_krw',       # 수동 원화가
        'manual_retail_price_krw', # 수동 소비자가
    ],
    
    # 이미지 필드 (URL) - 최대 4개로 수정
    'image_fields': [f'image_url_{i}' for i in range(1, 5)],  # image_url_1 ~ image_url_4
    
    # 자동 생성 필드 (수정 불가)
    'auto_fields': ['created_at', 'updated_at', 'calculated_price_krw'],
}

# ========================================
# 🔧 유틸리티 함수들
# ========================================

def validate_image_file(file):
    """이미지 파일 검증"""
    if file.size > IMAGE_UPLOAD_SETTINGS['max_size']:
        return False, _('이미지 크기는 5MB 이하여야 합니다.')
    
    try:
        img = Image.open(file)
        if img.format not in IMAGE_UPLOAD_SETTINGS['allowed_formats']:
            return False, _('지원하지 않는 이미지 형식입니다.')
        
        width, height = img.size
        if width > IMAGE_UPLOAD_SETTINGS['max_width'] or height > IMAGE_UPLOAD_SETTINGS['max_height']:
            return False, _('이미지 크기는 2000x2000px 이하여야 합니다.')
        
        return True, None
    except Exception:
        return False, _('유효하지 않은 이미지 파일입니다.')

def process_image_upload(image_file):
    """이미지 업로드 처리 및 최적화"""
    try:
        # 이미지 검증
        is_valid, error_msg = validate_image_file(image_file)
        if not is_valid:
            return None, error_msg
        
        # 이미지 최적화 (필요시 리사이즈)
        img = Image.open(image_file)
        
        # 큰 이미지는 리사이즈
        max_size = (1200, 1200)
        if img.size[0] > max_size[0] or img.size[1] > max_size[1]:
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
        
        # 저장
        output = BytesIO()
        img.save(output, format='JPEG', quality=85, optimize=True)
        output.seek(0)
        
        # 파일명 생성
        file_name = f"product_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        file_path = default_storage.save(
            IMAGE_UPLOAD_SETTINGS['upload_path'] + file_name,
            ContentFile(output.getvalue())
        )
        
        return default_storage.url(file_path), None
        
    except Exception as e:
        return None, f'이미지 처리 중 오류 발생: {str(e)}'

# ========================================
# 🔧 메인 뷰 함수들
# ========================================

@staff_member_required
def product_add(request):
    """상품 등록 페이지 - GET/POST 모두 처리"""
    
    # ✅ POST 요청 처리 추가 (핵심 수정사항)
    if request.method == 'POST':
        print("🔍 POST 요청 수신됨")  # 디버깅용
        
        register_type = request.POST.get('register_type', 'manual')
        print(f"📝 등록 타입: {register_type}")  # 디버깅용
        
        if register_type == 'manual':
            return handle_manual_register(request)
        elif register_type == 'excel':
            return handle_excel_register(request)
        else:
            messages.error(request, '잘못된 등록 방식입니다.')
            return redirect('dashboard:product_add')
    
    # ✅ GET 요청 처리 (기존 코드)
    context = {
        'retailer_options': Retailer.objects.all().order_by('name'),
        'brand_options': Brand.objects.all().order_by('name'),
        'gender_options': CategoryLevel1.objects.all().order_by('name'),
        'category1_options': CategoryLevel2.objects.all().order_by('name'),
        'category2_options': CategoryLevel3.objects.all().order_by('name'),
        'origin_options': FixedCountry.objects.all().order_by('name'),
    }
    
    print(f"📊 컨텍스트 데이터:")  # 디버깅용
    print(f"   - 거래처: {context['retailer_options'].count()}개")
    print(f"   - 브랜드: {context['brand_options'].count()}개")
    print(f"   - 원산지: {context['origin_options'].count()}개")
    
    return render(request, 'dashboard/product_add.html', context)

def handle_manual_register(request):
    """일반등록 처리 - 업데이트된 필드 구조 기준"""
    try:
        print("🚀 일반등록 처리 시작")  # 디버깅용
        
        # 🔍 옵션 사전 검증
        option_errors = validate_product_options(request)
        if option_errors:
            for error in option_errors:
                messages.error(request, error)
            return redirect('dashboard:product_add')
        
        # 🔍 필수 필드 먼저 검증
        required_data = {}
        for field in PRODUCT_FIELD_CONFIG['required_fields']:
            value = request.POST.get(field, '').strip()
            if not value:
                messages.error(request, f'{field}는 필수 입력 항목입니다.')
                return redirect('dashboard:product_add')
            required_data[field] = value
        
        print(f"✅ 필수 필드 검증 완료: {required_data}")  # 디버깅용
        
        # 🔍 SKU 중복 검증
        if Product.objects.filter(sku=required_data['sku']).exists():
            messages.error(request, f'SKU "{required_data["sku"]}"는 이미 존재합니다.')
            return redirect('dashboard:product_add')
        
        # 🔍 상품 데이터 수집
        product_data = {}
        
        # 텍스트 필드 처리
        for field in PRODUCT_FIELD_CONFIG['text_fields']:
            product_data[field] = request.POST.get(field, '').strip()
        
        # 토글 선택 필드 처리 (일반등록에서는 텍스트로 저장)
        for field_key, field_config in PRODUCT_FIELD_CONFIG['toggle_fields'].items():
            # 토글에서 선택한 값을 텍스트로 저장
            selected_text = request.POST.get(f'{field_key}_text', '').strip()
            product_data[field_key] = selected_text
        
        # 가격 필드 처리 (숫자 변환)
        for field in PRODUCT_FIELD_CONFIG['price_fields']:
            try:
                value = request.POST.get(field, '0')
                product_data[field] = float(value) if value else 0.0
            except (ValueError, TypeError):
                product_data[field] = 0.0
        
        # 🖼️ 이미지 처리 (파일 업로드)
        for i in range(1, 5):  # 1~4번 이미지
            image_file = request.FILES.get(f'image_file_{i}')
            if image_file:
                image_url, error = process_image_upload(image_file)
                if error:
                    messages.error(request, f'이미지 {i}: {error}')
                    return redirect('dashboard:product_add')
                product_data[f'image_url_{i}'] = image_url
            else:
                product_data[f'image_url_{i}'] = ''
        
        print(f"📝 수집된 상품 데이터: {product_data}")  # 디버깅용
        
        # 💾 상품 생성
        product = Product.objects.create(**product_data)
        print(f"✅ 상품 생성 완료: ID {product.id}")  # 디버깅용
        
        # 🎯 옵션 처리
        success = handle_product_options(request, product)
        if not success:
            # 옵션 처리 실패시 상품도 삭제
            product.delete()
            messages.error(request, '옵션 처리 중 오류가 발생했습니다.')
            return redirect('dashboard:product_add')
        
        messages.success(request, f'상품 "{product.product_name}"이 성공적으로 등록되었습니다.')
        return redirect('dashboard:product_list')
        
    except Exception as e:
        print(f"💥 등록 처리 오류: {str(e)}")  # 디버깅용
        messages.error(request, f'상품 등록 중 오류가 발생했습니다: {str(e)}')
        return redirect('dashboard:product_add')

def handle_product_options(request, product):
    """상품 옵션 처리 - 동적 행 추가 방식"""
    try:
        # 옵션 데이터 수집 (배열 형태)
        option_names = request.POST.getlist('option_name[]')
        option_stocks = request.POST.getlist('option_stock[]')
        
        print(f"🔍 옵션 데이터 디버깅:")
        print(f"   옵션명: {option_names}")
        print(f"   재고: {option_stocks}")
        
        # 옵션 데이터 검증 및 생성
        created_options = []
        
        for i, name in enumerate(option_names):
            name = name.strip()
            if not name:  # 빈 옵션명은 건너뛰기
                continue
                
            try:
                # 재고 처리 (인덱스 범위 확인)
                stock = int(option_stocks[i]) if i < len(option_stocks) and option_stocks[i].strip() else 0
                stock = max(0, stock)  # 음수 방지
            except (ValueError, IndexError):
                stock = 0
            
            # 중복 옵션명 확인
            if name in [opt['name'] for opt in created_options]:
                print(f"⚠️  중복 옵션명 건너뛰기: {name}")
                continue
            
            # 옵션 데이터 저장 (실제 옵션 모델 확인 후 구현)
            option_data = {
                'product': product,
                'option_name': name,
                'stock': stock
            }
            
            # TODO: 실제 ProductOption 모델로 생성
            # ProductOption.objects.create(**option_data)
            
            # 임시로 리스트에 저장
            created_options.append({
                'name': name,
                'stock': stock
            })
            
            print(f"✅ 옵션 생성: {name} (재고: {stock})")
        
        print(f"📊 총 {len(created_options)}개 옵션 생성됨")
        return True
        
    except Exception as e:
        print(f"💥 옵션 처리 오류: {str(e)}")
        return False

def validate_product_options(request):
    """상품 옵션 사전 검증"""
    option_names = request.POST.getlist('option_name[]')
    option_stocks = request.POST.getlist('option_stock[]')
    
    errors = []
    
    # 최소 1개 옵션 확인
    valid_options = [name.strip() for name in option_names if name.strip()]
    if not valid_options:
        errors.append('최소 1개 이상의 옵션을 입력해주세요.')
    
    # 중복 옵션명 확인
    if len(valid_options) != len(set(valid_options)):
        errors.append('중복된 옵션명이 있습니다.')
    
    # 재고 음수 확인
    for i, stock_str in enumerate(option_stocks):
        if i < len(option_names) and option_names[i].strip():
            try:
                stock = int(stock_str) if stock_str.strip() else 0
                if stock < 0:
                    errors.append(f'재고는 음수일 수 없습니다: {option_names[i]}')
            except ValueError:
                errors.append(f'올바르지 않은 재고 값: {option_names[i]}')
    
    return errors

def handle_excel_register(request):
    """엑셀등록 처리 - 옵션 포함"""
    try:
        excel_file = request.FILES.get('excel_file')
        if not excel_file:
            messages.error(request, '엑셀 파일을 선택해주세요.')
            return redirect('dashboard:product_add')
        
        # 🔍 엑셀 파일 검증
        is_valid, error_msg = validate_excel_file(excel_file)
        if not is_valid:
            messages.error(request, error_msg)
            return redirect('dashboard:product_add')
        
        # 📊 엑셀 파일 읽기
        try:
            df = pd.read_excel(excel_file)
        except Exception as e:
            messages.error(request, f'엑셀 파일을 읽을 수 없습니다: {str(e)}')
            return redirect('dashboard:product_add')
        
        # 🔍 데이터 검증 및 처리
        success_count, error_count, errors = process_excel_data_with_options(df)
        
        # 📊 결과 메시지
        if success_count > 0:
            messages.success(request, f'{success_count}개 상품이 성공적으로 등록되었습니다.')
        
        if error_count > 0:
            error_summary = '\n'.join(errors[:5])  # 최대 5개 오류만 표시
            if len(errors) > 5:
                error_summary += f'\n... 외 {len(errors) - 5}개 오류'
            messages.error(request, f'{error_count}개 상품 등록 실패:\n{error_summary}')
        
        return redirect('dashboard:product_list')
        
    except Exception as e:
        messages.error(request, f'엑셀 등록 중 오류가 발생했습니다: {str(e)}')
        return redirect('dashboard:product_add')

def validate_excel_file(file):
    """엑셀 파일 검증"""
    if file.size > EXCEL_SETTINGS['max_size']:
        return False, _('엑셀 파일 크기는 10MB 이하여야 합니다.')
    
    file_extension = os.path.splitext(file.name)[1].lower()
    if file_extension not in EXCEL_SETTINGS['allowed_extensions']:
        return False, _('xlsx 또는 xls 파일만 업로드 가능합니다.')
    
    return True, None

def process_excel_data_with_options(df):
    """엑셀 데이터 처리 - 옵션 포함"""
    success_count = 0
    error_count = 0
    errors = []
    
    # 📋 필수 컬럼 확인
    required_columns = ['고유상품ID', '상품명', 'SKU']
    missing_columns = [col for col in required_columns if col not in df.columns]
    
    if missing_columns:
        errors.append(f'필수 컬럼이 없습니다: {", ".join(missing_columns)}')
        return 0, len(df), errors
    
    # 🔍 각 행 처리
    for index, row in df.iterrows():
        try:
            row_num = index + 2  # 엑셀 행 번호 (헤더 제외)
            
            # 필수 필드 검증
            external_product_id = str(row.get('고유상품ID', '')).strip()
            product_name = str(row.get('상품명', '')).strip()
            sku = str(row.get('SKU', '')).strip()
            
            if not external_product_id or not product_name or not sku:
                errors.append(f'행 {row_num}: 고유상품ID, 상품명, SKU는 필수입니다.')
                error_count += 1
                continue
            
            # SKU 중복 검사
            if Product.objects.filter(sku=sku).exists():
                errors.append(f'행 {row_num}: SKU "{sku}"는 이미 존재합니다.')
                error_count += 1
                continue
            
            # 🔍 상품 데이터 구성
            product_data = {}
            
            # 엑셀 컬럼명 → 모델 필드명 매핑
            field_mapping = {
                'external_product_id': '고유상품ID',
                'product_name': '상품명',
                'sku': 'SKU',
                'retailer': '부띠끄명',
                'brand_name': '브랜드명',
                'gender': '성별',
                'category1': '카테고리1',
                'category2': '카테고리2',
                'season': '시즌',
                'color': '색상명',
                'origin': '원산지',
                'material': '소재',
                'description': '설명',
                'status': '상태',
            }
            
            for field_name, excel_column in field_mapping.items():
                product_data[field_name] = str(row.get(excel_column, '')).strip()
            
            # 가격 필드 처리
            price_mapping = {
                'price_org': 'COST',
                'discount_rate': '할인율',
                'price_retail': '소비자가',
                'manual_price_krw': '수동원화가',
                'manual_retail_price_krw': '수동소비자가',
            }
            
            for field_name, excel_column in price_mapping.items():
                try:
                    price_value = row.get(excel_column, 0)
                    product_data[field_name] = float(price_value) if price_value else 0.0
                except (ValueError, TypeError):
                    product_data[field_name] = 0.0
            
            # 🖼️ 이미지 URL 처리
            for i in range(1, 5):
                image_url = str(row.get(f'이미지{i}', '')).strip()
                if image_url and validate_image_url(image_url):
                    product_data[f'image_url_{i}'] = image_url
                else:
                    product_data[f'image_url_{i}'] = ''
            
            # 💾 상품 생성
            product = Product.objects.create(**product_data)
            
            # 🎯 옵션 처리 (엑셀에서 옵션정보 컬럼 파싱)
            options_success = process_excel_options(row, product, row_num, errors)
            if not options_success:
                # 옵션 처리 실패해도 상품은 유지 (선택사항)
                pass
            
            success_count += 1
            
        except Exception as e:
            errors.append(f'행 {row_num}: {str(e)}')
            error_count += 1
    
    return success_count, error_count, errors

def process_excel_options(row, product, row_num, errors):
    """엑셀 옵션 데이터 처리"""
    try:
        # 옵션정보 컬럼에서 데이터 추출
        options_string = str(row.get('옵션정보', '')).strip()
        
        if not options_string:
            return True  # 옵션이 없어도 OK
        
        # 형식: "BLACK-S:10,WHITE-M:15,RED-L:20"
        option_items = options_string.split(',')
        created_options = []
        
        for item in option_items:
            item = item.strip()
            if ':' in item:
                try:
                    name, stock_str = item.split(':', 1)
                    name = name.strip()
                    stock = int(stock_str.strip()) if stock_str.strip().isdigit() else 0
                    
                    if name and name not in [opt['name'] for opt in created_options]:
                        # TODO: 실제 ProductOption 모델로 생성
                        # ProductOption.objects.create(
                        #     product=product,
                        #     option_name=name,
                        #     stock=stock
                        # )
                        
                        created_options.append({
                            'name': name,
                            'stock': stock
                        })
                        
                except ValueError:
                    errors.append(f'행 {row_num}: 잘못된 옵션 형식 - {item}')
        
        return True
        
    except Exception as e:
        errors.append(f'행 {row_num}: 옵션 처리 오류 - {str(e)}')
        return False

def validate_image_url(url):
    """이미지 URL 유효성 검증"""
    try:
        response = requests.head(url, timeout=5)
        if response.status_code == 200:
            content_type = response.headers.get('content-type', '')
            if content_type.startswith('image/'):
                return True
        return False
    except:
        return False

# ========================================
# 🔧 AJAX 지원 함수들
# ========================================

@staff_member_required 
def get_product_preview(request):
    """상품 미리보기 AJAX (등록 전 확인용)"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': '잘못된 요청입니다.'})
    
    try:
        # 기본 정보 수집
        preview_data = {
            'external_product_id': request.POST.get('external_product_id', ''),
            'product_name': request.POST.get('product_name', ''),
            'sku': request.POST.get('sku', ''),
            'brand_name': request.POST.get('brand_name_text', ''),
            'retailer': request.POST.get('retailer_text', ''),
            'price_retail': request.POST.get('price_retail', '0'),
            'price_org': request.POST.get('price_org', '0'),
        }
        
        # 옵션 정보 수집
        option_names = request.POST.getlist('option_name[]')
        option_stocks = request.POST.getlist('option_stock[]')
        
        options = []
        total_stock = 0
        
        for i, name in enumerate(option_names):
            if name.strip():
                stock = int(option_stocks[i]) if i < len(option_stocks) and option_stocks[i].strip().isdigit() else 0
                options.append({
                    'name': name.strip(),
                    'stock': stock
                })
                total_stock += stock
        
        preview_data['options'] = options
        preview_data['total_stock'] = total_stock
        
        return JsonResponse({
            'success': True,
            'preview': preview_data
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False, 
            'message': f'미리보기 생성 중 오류: {str(e)}'
        })

@staff_member_required
def validate_sku(request):
    """SKU 중복 검사 AJAX"""
    sku = request.GET.get('sku', '').strip()
    
    if not sku:
        return JsonResponse({'valid': False, 'message': 'SKU를 입력해주세요.'})
    
    exists = Product.objects.filter(sku=sku).exists()