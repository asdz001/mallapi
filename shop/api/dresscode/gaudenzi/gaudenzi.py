"""
Gaudenzi 상품 수집/등록 시스템 (수정된 버전)
============================
🎯 Dresscode API → Gaudenzi 상품 자동 수집/등록
📝 실행: python manage.py collect_gaudenzi_products
"""

import json
import logging
import requests
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List
import pytz
from utils.product_logger import get_product_logger

from django.core.management.base import BaseCommand
from django.db import transaction

# Django 모델 임포트 (단독 실행시에는 하단에서 처리)
try:
    from shop.models import RawProduct, RawProductOption
except ImportError:
    # 단독 실행시에는 나중에 임포트
    RawProduct = None
    RawProductOption = None


# 설정
class Config:
    API_URL = "https://api.dresscode.cloud/channels/v2/api/feeds/en/clients/gaudenzi/products"
    CLIENT = "gaudenzi"
    CHANNEL_KEY = "33a2aaeb-7ef2-44c5-bb66-0d3a84e9869f"
    SUBSCRIPTION_KEY = "d9b2538817b248d6a39e7289d5b87e87"
    RETAILER_CODE = "IT-G-03"
    
    EXPORT_DIR = Path("export/GAUDENZI")
    HISTORY_FILE = EXPORT_DIR / "last_collection_time.txt"
    FULL_HISTORY_FILE = EXPORT_DIR / "full_collections.txt"
    BACKUP_DIR = EXPORT_DIR / "json_backup"
    
    @classmethod
    def setup(cls):
        cls.EXPORT_DIR.mkdir(parents=True, exist_ok=True)
        cls.BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def get_headers(cls):
        return {
            'client': cls.CLIENT,
            'Ocp-Apim-Subscription-Key': cls.SUBSCRIPTION_KEY,
            'Accept': 'application/json'
        }


# 시간 처리
class TimeHelper:
    KST = pytz.timezone('Asia/Seoul')
    UTC = pytz.UTC
    
    @classmethod
    def now_kst(cls):
        return datetime.now(cls.KST)
    
    @classmethod
    def now_utc(cls):
        return datetime.now(cls.UTC)
    
    @classmethod
    def get_midnight_utc(cls):
        now_kst = cls.now_kst()
        midnight_kst = cls.KST.localize(
            datetime(now_kst.year, now_kst.month, now_kst.day, 0, 0, 0)
        )
        return midnight_kst.astimezone(cls.UTC)
    
    @classmethod
    def did_full_collection_today(cls):
        try:
            if not Config.FULL_HISTORY_FILE.exists():
                return False
            
            today = cls.now_kst().date()
            with open(Config.FULL_HISTORY_FILE, 'r') as f:
                for line in f:
                    if line.strip().startswith(today.strftime('%Y-%m-%d')):
                        return True
            return False
        except:
            return False
    
    @classmethod
    def get_collection_range(cls):
        if cls.did_full_collection_today():
            # 부분 수집
            last_time = cls.read_last_time()
            return last_time or cls.get_midnight_utc(), cls.now_utc(), False
        else:
            # 전체 수집
            return cls.get_midnight_utc(), None, True
    
    @classmethod
    def read_last_time(cls):
        try:
            if Config.HISTORY_FILE.exists():
                time_str = Config.HISTORY_FILE.read_text().strip()
                return datetime.fromisoformat(time_str.replace('Z', '+00:00'))
        except:
            pass
        return None
    
    @classmethod
    def save_time(cls, is_full=False):
        now = cls.now_utc()
        time_str = now.isoformat().replace('+00:00', 'Z')
        
        Config.HISTORY_FILE.write_text(time_str)
        
        if is_full:
            today = cls.now_kst().date()
            with open(Config.FULL_HISTORY_FILE, 'a') as f:
                f.write(f"{today}\t{time_str}\n")


# API 클라이언트
class APIClient:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(Config.get_headers())
    
    def fetch_products(self, from_time=None, to_time=None, is_full_collection=False):
        if is_full_collection:
            params = {'channelKey': Config.CHANNEL_KEY}
            logging.info("📡 전체 수집 API 요청")
        else:
            params = {
                'channelKey': Config.CHANNEL_KEY,
                'from': from_time.isoformat().replace('+00:00', 'Z')
            }
            if to_time:
                params['to'] = to_time.isoformat().replace('+00:00', 'Z')
            logging.info(f"📡 부분 수집 API 요청: {params}")
        
        try:
            response = self.session.get(Config.API_URL, params=params, timeout=120)
            print(f"✅ 응답 코드: {response.status_code}")
            print(f"📦 응답 내용 (앞 300자): {response.text[:300]}")            
            response.raise_for_status()
            
            data = response.json()
            products = data.get('data', data) if isinstance(data, dict) else data
            
            logging.info(f"✅ 수집 완료: {len(products)}개")
            return products
            
        except Exception as e:
            logging.error(f"❌ API 요청 실패: {e}")
            return None


# 데이터 처리 (수정된 버전)
class DataProcessor:
    def __init__(self):
        self.stats = {'products_created': 0, 'products_updated': 0, 'products_soldout': 0,
                     'options_created': 0, 'options_updated': 0, 'options_deleted': 0, 'errors': 0}
    
    @transaction.atomic
    def process_products(self, products_data, is_full_collection=False):
        logging.info(f"🔄 {'전체' if is_full_collection else '부분'} 상품 처리 시작: {len(products_data)}개")
        
        valid_products = [p for p in products_data if p.get('productID')]
        incoming_product_ids = [str(p['productID']) for p in valid_products]
        
        if is_full_collection:
            existing_products_dict = self._get_all_existing_products_dict()
            existing_options_dict = self._get_all_existing_options_dict()
        else:
            existing_products_dict = self._get_existing_products_dict(incoming_product_ids)
            existing_options_dict = self._get_existing_options_dict(incoming_product_ids)
        
        # 상품 처리
        products_to_create, products_to_update = self._classify_products(valid_products, existing_products_dict)
        self._bulk_process_products(products_to_create, products_to_update)
        
        # 옵션 처리
        if is_full_collection:
            self._process_options_full_sync(valid_products, existing_options_dict, incoming_product_ids)
        else:
            self._process_options_partial_sync(valid_products, existing_options_dict, incoming_product_ids)
        
        # 전체 수집시 soldout 처리
        if is_full_collection:
            self._bulk_mark_soldout(incoming_product_ids)
        
        self._print_stats()
    
    def _get_all_existing_products_dict(self):
        existing_products = RawProduct.objects.filter(retailer=Config.RETAILER_CODE)
        return {p.external_product_id: p for p in existing_products}
    
    # ✅ 수정: product 필드명으로 변경
    def _get_all_existing_options_dict(self):
        existing_options = RawProductOption.objects.filter(
            product__retailer=Config.RETAILER_CODE  # ✅ raw_product → product
        ).select_related('product')  # ✅ raw_product → product
        return {o.external_option_id: o for o in existing_options}
    
    def _get_existing_products_dict(self, product_ids):
        existing_products = RawProduct.objects.filter(
            retailer=Config.RETAILER_CODE, external_product_id__in=product_ids
        )
        return {p.external_product_id: p for p in existing_products}
    
    # ✅ 수정: product 필드명으로 변경
    def _get_existing_options_dict(self, product_ids):
        existing_options = RawProductOption.objects.filter(
            product__retailer=Config.RETAILER_CODE,  # ✅ raw_product → product
            product__external_product_id__in=product_ids  # ✅ raw_product → product
        ).select_related('product')  # ✅ raw_product → product
        return {o.external_option_id: o for o in existing_options}
    
    def _classify_products(self, valid_products, existing_products_dict):
        products_to_create = []
        products_to_update = []
        
        for product_data in valid_products:
            try:
                product_id = str(product_data['productID'])
                product_fields = self._map_product_fields(product_data)
                
                if product_id in existing_products_dict:
                    existing_product = existing_products_dict[product_id]
                    if self._has_product_changes(existing_product, product_fields):
                        for field, value in product_fields.items():
                            setattr(existing_product, field, value)
                        products_to_update.append(existing_product)
                else:
                    new_product = RawProduct(
                        retailer=Config.RETAILER_CODE,
                        external_product_id=product_id,
                        **product_fields
                    )
                    products_to_create.append(new_product)
                    
            except Exception as e:
                logging.error(f"❌ 상품 분류 실패 {product_data.get('productID')}: {e}")
                self.stats['errors'] += 1
        
        return products_to_create, products_to_update
    
    def _has_product_changes(self, existing_product, new_fields):
        key_fields = ['product_name', 'price_org', 'price_supply', 'price_retail', 'color', 'description']
        for field in key_fields:
            if field in new_fields and getattr(existing_product, field) != new_fields[field]:
                return True
        return False
    
    def _bulk_process_products(self, products_to_create, products_to_update):
        if products_to_create:
            RawProduct.objects.bulk_create(products_to_create, batch_size=1000)
            self.stats['products_created'] = len(products_to_create)
            logging.info(f"🆕 상품 생성: {len(products_to_create)}개")
        
        if products_to_update:
            update_fields = ['product_name', 'raw_brand_name', 'season', 'gender', 'category1', 'category2', 
                           'origin', 'material', 'price_org', 'price_supply', 'price_retail', 'sku', 
                           'color', 'description', 'image_url_1', 'image_url_2', 'image_url_3', 'image_url_4', 'status']
            RawProduct.objects.bulk_update(products_to_update, update_fields, batch_size=1000)
            self.stats['products_updated'] = len(products_to_update)
            logging.info(f"🔄 상품 업데이트: {len(products_to_update)}개")
    
    def _process_options_full_sync(self, valid_products, existing_options_dict, incoming_product_ids):
        current_products_dict = {
            p.external_product_id: p for p in RawProduct.objects.filter(
                retailer=Config.RETAILER_CODE, external_product_id__in=incoming_product_ids
            )
        }
        
        incoming_options = {}
        for product_data in valid_products:
            product_id = str(product_data['productID'])
            options_data = product_data.get('sizes', [])
            if not options_data:
                options_data = [{'size': 'ONE', 'stock': 0}]
            
            for option_data in options_data:
                external_option_id = self._get_option_external_id(product_id, option_data)
                incoming_options[external_option_id] = (product_id, option_data, product_data)
        
        incoming_option_ids = set(incoming_options.keys())
        # ✅ 수정: product 필드명으로 변경
        product_related_existing_options = {
            oid: opt for oid, opt in existing_options_dict.items()
            if opt.product.external_product_id in incoming_product_ids  # ✅ raw_product → product
        }
        options_to_delete_ids = [
            oid for oid in product_related_existing_options.keys()
            if oid not in incoming_option_ids
        ]
        
        self._process_incoming_options(incoming_options, existing_options_dict, 
                                     current_products_dict, options_to_delete_ids)
    
    def _process_options_partial_sync(self, valid_products, existing_options_dict, incoming_product_ids):
        current_products_dict = {
            p.external_product_id: p for p in RawProduct.objects.filter(
                retailer=Config.RETAILER_CODE, external_product_id__in=incoming_product_ids
            )
        }
        
        incoming_options = {}
        for product_data in valid_products:
            product_id = str(product_data['productID'])
            options_data = product_data.get('sizes', [])
            if not options_data:
                options_data = [{'size': 'ONE', 'stock': 0}]
            
            for option_data in options_data:
                external_option_id = self._get_option_external_id(product_id, option_data)
                incoming_options[external_option_id] = (product_id, option_data, product_data)
        
        incoming_option_ids = set(incoming_options.keys())
        # ✅ 수정: product 필드명으로 변경
        options_to_delete_ids = [
            oid for oid, opt in existing_options_dict.items()
            if (opt.product.external_product_id in incoming_product_ids and  # ✅ raw_product → product
                oid not in incoming_option_ids)
        ]
        
        self._process_incoming_options(incoming_options, existing_options_dict, 
                                     current_products_dict, options_to_delete_ids)
    
    def _process_incoming_options(self, incoming_options, existing_options_dict, 
                                current_products_dict, options_to_delete_ids):
        options_to_create = []
        options_to_update = []
        
        for external_option_id, (product_id, option_data, product_data) in incoming_options.items():
            try:
                if product_id not in current_products_dict:
                    continue
                
                product_obj = current_products_dict[product_id]
                option_fields = self._map_option_fields(option_data, product_data)
                
                if external_option_id in existing_options_dict:
                    existing_option = existing_options_dict[external_option_id]
                    if self._has_option_changes(existing_option, option_fields):
                        for field, value in option_fields.items():
                            setattr(existing_option, field, value)
                        options_to_update.append(existing_option)
                else:
                    # ✅ 수정: product 필드명으로 변경
                    new_option = RawProductOption(
                        product=product_obj,  # ✅ raw_product → product
                        external_option_id=external_option_id,
                        **option_fields
                    )
                    options_to_create.append(new_option)
                    
            except Exception as e:
                logging.error(f"❌ 옵션 처리 실패 {external_option_id}: {e}")
                self.stats['errors'] += 1
        
        self._bulk_process_options(options_to_create, options_to_update, options_to_delete_ids)
    
    # ✅ 수정: 실제 모델 필드명으로 변경
    def _has_option_changes(self, existing_option, new_fields):
        for field in ['option_name', 'stock', 'price']:  # ✅ size → option_name, status 제거
            if field in new_fields and getattr(existing_option, field) != new_fields[field]:
                return True
        return False
    
    # ✅ 수정: 실제 모델 필드명으로 업데이트
    def _bulk_process_options(self, options_to_create, options_to_update, options_to_delete_ids):
        if options_to_delete_ids:
            deleted_count = RawProductOption.objects.filter(
                external_option_id__in=options_to_delete_ids
            ).delete()[0]
            self.stats['options_deleted'] = deleted_count
            logging.info(f"🗑️ 옵션 삭제: {deleted_count}개")
        
        if options_to_create:
            RawProductOption.objects.bulk_create(options_to_create, batch_size=1000)
            self.stats['options_created'] = len(options_to_create)
            logging.info(f"🆕 옵션 생성: {len(options_to_create)}개")
        
        if options_to_update:
            # ✅ 수정: 실제 모델 필드명으로 변경
            update_fields = ['option_name', 'stock', 'price']  # ✅ size → option_name, status 제거
            RawProductOption.objects.bulk_update(options_to_update, update_fields, batch_size=1000)
            self.stats['options_updated'] = len(options_to_update)
            logging.info(f"🔄 옵션 업데이트: {len(options_to_update)}개")
    
    def _bulk_mark_soldout(self, incoming_product_ids):
        soldout_count = RawProduct.objects.filter(
            retailer=Config.RETAILER_CODE
        ).exclude(
            external_product_id__in=incoming_product_ids
        ).exclude(
            status='soldout'
        ).update(status='soldout')
        
        if soldout_count > 0:
            self.stats['products_soldout'] = soldout_count
            logging.info(f"🧹 soldout 처리: {soldout_count}개")
    
    def _get_option_external_id(self, product_id, option_data):
        gtin = option_data.get('gtin') or option_data.get('GTIN')
        if gtin:
            return str(gtin)
        size = option_data.get('size', 'ONE')
        return f"{product_id}_{size}"
    
    # ✅ 수정: status 기본값을 pending으로 변경
    def _map_product_fields(self, data):
        photos = data.get('photos', [])
        images = ['', '', '', '']
        for i, photo in enumerate(photos[:4]):
            if isinstance(photo, str):
                images[i] = photo
            elif isinstance(photo, dict):
                images[i] = photo.get('url', '')

        # ✅ 옵션에서 가장 높은 wholesalePrice 가져오기 (우리가 추가할 부분)
        max_opt_wholesale = max(
            (float(opt.get("wholesalePrice", 0)) for opt in data.get("sizes", [])),
            default=0
        )
        # ✅ 상품의 최종 가격 설정
        price_org = (
            float(data["wholesalePrice"])
            if data.get("wholesalePrice")
            else max_opt_wholesale
            if max_opt_wholesale > 0
            else float(data.get("price", 0))
        )


        
        return {
            'product_name': f"{data.get('brand', '')} {data.get('name', '')} {data.get('sku', '')}".strip(),
            'raw_brand_name': data.get('brand', ''),
            'season': data.get('season', ''),
            'gender': data.get('genre', ''),
            'category1': data.get('type', ''),
            'category2': data.get('category', ''),
            'origin': data.get('madeIn', ''),
            'material': data.get('composition', ''),
            'price_org': price_org,
            'price_supply': float(data.get('price', 0)),
            'price_retail': float(data.get('retailPrice', 0)),
            'sku': data.get('sku', ''),
            'color': data.get('color', ''),
            'description': f"{data.get('description', '')}\n{data.get('sizeType', '')}".strip(),
            'image_url_1': images[0],
            'image_url_2': images[1],
            'image_url_3': images[2],
            'image_url_4': images[3],
            'status': 'pending'  # ✅ RawProduct의 올바른 기본값 (active → pending)
        }
    
    # ✅ 수정: 올바른 필드 매핑
    def _map_option_fields(self, option_data, product_data):
        stock = int(option_data.get('stock', 0))
        price = (float(option_data["wholesalePrice"])
                 if option_data.get("wholesalePrice")else float(product_data["wholesalePrice"])
                 if product_data.get("wholesalePrice")else float(product_data.get("price", 0)))
        
        return {
            'option_name': option_data.get('size', 'ONE'),  # ✅ size → option_name
            'stock': stock,
            'price': price,
            # ✅ status 필드 제거 (models.py에 없음)
        }
    
    def _print_stats(self):
        logging.info("📊 처리 결과:")
        for key, value in self.stats.items():
            if value > 0:
                logging.info(f"   {key.replace('_', ' ').title()}: {value:,}개")


# Django Command
class Command(BaseCommand):
    help = 'Gaudenzi 상품 수집 및 등록'
    
    def add_arguments(self, parser):
        parser.add_argument('--force-full', action='store_true', help='강제 전체 수집')
        parser.add_argument('--no-backup', action='store_true', help='JSON 백업 안함')
        parser.add_argument('--test-api', action='store_true', help='API 테스트만')
    
    def handle(self, *args, **options):
        # 로깅 설정
        custom_logger = get_product_logger(Config.RETAILER_CODE)
        
        for h in custom_logger.handlers:
            logging.getLogger().addHandler(h)
        
        try:
            Config.setup()
            
            # 강제 전체 수집 처리
            if options['force_full']:
                if Config.FULL_HISTORY_FILE.exists():
                    today = TimeHelper.now_kst().date()
                    lines = Config.FULL_HISTORY_FILE.read_text().splitlines()
                    filtered = [l for l in lines if not l.startswith(today.strftime('%Y-%m-%d'))]
                    Config.FULL_HISTORY_FILE.write_text('\n'.join(filtered))
                logging.info("🔄 강제 전체 수집 모드")
            
            client = APIClient()
            
            # 테스트 모드
            if options['test_api']:
                test_time = TimeHelper.now_utc() - timedelta(hours=1)
                result = client.fetch_products(test_time, TimeHelper.now_utc(), is_full_collection=False)
                if result is not None:
                    self.stdout.write(self.style.SUCCESS(f'✅ API 테스트 성공: {len(result)}개'))
                else:
                    self.stdout.write(self.style.ERROR('❌ API 테스트 실패'))
                return
            
            # 수집 시간 범위 계산
            from_time, to_time, is_full = TimeHelper.get_collection_range()
            
            logging.info(f"🎯 {'📦 전체' if is_full else '🔄 부분'} 수집 실행")
            logging.info(f"📅 범위: {from_time} ~ {to_time or '현재'}")
            
            # 상품 데이터 수집
            products = client.fetch_products(from_time, to_time, is_full)
            if products is None:
                raise Exception("API 데이터 수집 실패")
            
            if not products:
                logging.info("📭 수집할 데이터 없음")
                TimeHelper.save_time(is_full)
                return
            
            # JSON 백업 (실험용 - 전체 수집시에만)
            if is_full and not options['no_backup']:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                backup_file = Config.BACKUP_DIR / f"gaudenzi_full_{timestamp}_{len(products)}items.json"
                backup_file.write_text(json.dumps(products, ensure_ascii=False, indent=2))
                logging.info(f"💾 백업 (전체 수집): {backup_file}")
            elif not is_full:
                logging.info("📝 부분 수집 - JSON 백업 생략")
            
            # 데이터 처리
            processor = DataProcessor()
            processor.process_products(products, is_full)
            
            # 완료 시간 저장
            TimeHelper.save_time(is_full)
            
            logging.info("✅ 수집 완료")
            self.stdout.write(self.style.SUCCESS('✅ Gaudenzi 상품 수집 완료'))
            
        except Exception as e:
            logging.error(f"❌ 수집 실패: {e}")
            self.stdout.write(self.style.ERROR(f'❌ 수집 실패: {e}'))
            raise


# pipeline_runner용 메인 함수 ==
def run_gaudenzi_collection(force_full=False):
    try:
        print("📦 Gaudenzi 상품 수집 시작")
        Config.setup()
        
        # 강제 전체 수집 처리
        if force_full:
            if Config.FULL_HISTORY_FILE.exists():
                today = TimeHelper.now_kst().date()
                lines = Config.FULL_HISTORY_FILE.read_text().splitlines()
                filtered = [l for l in lines if not l.startswith(today.strftime('%Y-%m-%d'))]
                Config.FULL_HISTORY_FILE.write_text('\n'.join(filtered))
                print("🔄 강제 전체 수집 모드 활성화")
        
        client = APIClient()
        from_time, to_time, is_full = TimeHelper.get_collection_range()
        
        print(f"🎯 {'전체' if is_full else '부분'} 수집 실행")
        print(f"📅 범위: {from_time} ~ {to_time or '현재'}")
        
        products = client.fetch_products(from_time, to_time, is_full)
        
        if products is None:
            print("❌ API 응답이 None입니다")
            return 0
            
        if not products:
            print("📭 수집할 데이터 없음 (빈 배열)")
            TimeHelper.save_time(is_full)
            return 0
        
        print(f"📥 API에서 {len(products)}개 상품 수집됨")
        
        # 💾 JSON 백업 저장 (전체 수집시에만!)
        if is_full:
            try:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                backup_file = Config.BACKUP_DIR / f"gaudenzi_full_{timestamp}_{len(products)}items.json"
                backup_file.write_text(json.dumps(products, ensure_ascii=False, indent=2), encoding='utf-8')
                print(f"💾 JSON 백업 저장 (전체 수집): {backup_file}")
            except Exception as e:
                print(f"⚠️ JSON 백업 실패: {e}")
        else:
            print("📝 부분 수집 - JSON 백업 생략")
        
        processor = DataProcessor()
        processor.process_products(products, is_full)
        TimeHelper.save_time(is_full)
        
        print(f"✅ Gaudenzi 수집 완료: {len(products)}개")
        return len(products)
        
    except Exception as e:
        print(f"❌ Gaudenzi 수집 실패: {e}")
        import traceback
        traceback.print_exc()
        return 0


# 단독 실행용
if __name__ == "__main__":
    import os
    import sys
    import django
    
    # Django 환경 설정 (경로 수정)
    print("🔧 Django 환경 설정 시작...")
    
    # 현재 파일 위치에서 4단계 위로 올라가야 mallapi 프로젝트 루트
    # 현재: shop/api/dresscode/gaudenzi/gaudenzi.py
    # 목표: mallapi/ (manage.py가 있는 곳)
    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../"))
    print(f"📁 BASE_DIR: {BASE_DIR}")
    print(f"📄 manage.py 존재 확인: {os.path.exists(os.path.join(BASE_DIR, 'manage.py'))}")

    # ✅ Python 경로에 mallapi (manage.py가 있는 폴더)를 추가
    sys.path.insert(0, BASE_DIR)

    # ✅ Django 설정 지정
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mallapi.settings")
    
    try:
        django.setup()
        print("✅ Django 환경 설정 완료")
        
        # Django 모델 임포트
        from shop.models import RawProduct, RawProductOption
        print("✅ Django 모델 임포트 성공")
        
        # 전역 변수로 설정 (함수들에서 사용할 수 있도록)
        globals()['RawProduct'] = RawProduct
        globals()['RawProductOption'] = RawProductOption
        
        # 실제 수집 실행
        print("🚀 Gaudenzi 수집 실행 시작")
        result = run_gaudenzi_collection()
        print(f"{'✅ 성공' if result > 0 else '❌ 실패'}: {result}개")
        
    except Exception as e:
        print(f"❌ Django 환경 설정 실패: {e}")
        print(f"📁 계산된 BASE_DIR: {BASE_DIR}")
        print(f"📄 manage.py 존재 확인: {os.path.exists(os.path.join(BASE_DIR, 'manage.py'))}")
        print("📝 Django management command로 실행해보세요:")
        print("   python manage.py collect_gaudenzi_products")
        import traceback
        traceback.print_exc()
        sys.exit(1)