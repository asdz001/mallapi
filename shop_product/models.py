# shop_product/models.py
# 사용자별 테이블 컬럼 설정을 저장하는 모델 (기존 모델에 추가)

from django.db import models
from django.contrib.auth.models import User
import json

class UserTableColumnSetting(models.Model):
    """
    🎯 사용자별 테이블 컬럼 설정 모델
    - 각 사용자마다 다른 테이블 컬럼 표시 설정을 저장
    - 페이지별로 다른 설정 가능 (product_list, member_list 등)
    """
    
    # 사용자 정보 (Django User와 연결)
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE,
        verbose_name="사용자"
    )
    
    # 페이지 구분 (어떤 페이지의 설정인지)
    page_name = models.CharField(
        max_length=50,
        verbose_name="페이지명",
        help_text="예: product_list, member_list, supplier_list"
    )
    
    # 컬럼 설정 (JSON 형태로 저장)
    column_settings = models.JSONField(
        default=dict,
        verbose_name="컬럼 설정",
        help_text="{'external_product_id': {'visible': True, 'order': 1}, ...}"
    )
    
    # 생성일/수정일
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="생성일")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="수정일")
    
    class Meta:
        verbose_name = "사용자 테이블 컬럼 설정"
        verbose_name_plural = "사용자 테이블 컬럼 설정"
        # 사용자별 + 페이지별로 하나의 설정만 가능
        unique_together = ['user', 'page_name']
    
    def __str__(self):
        return f"{self.user.username} - {self.page_name}"
    
    def get_visible_columns(self):
        """표시할 컬럼 목록을 순서대로 반환"""
        if not self.column_settings:
            return []
        
        # visible=True인 컬럼들을 order 순서대로 정렬
        visible_columns = []
        for field_name, settings in self.column_settings.items():
            if settings.get('visible', True):  # 기본값은 True
                visible_columns.append({
                    'field': field_name,
                    'order': settings.get('order', 999)
                })
        
        # order 순서대로 정렬
        visible_columns.sort(key=lambda x: x['order'])
        return [col['field'] for col in visible_columns]
    
    def set_column_visibility(self, field_name, visible=True, order=None):
        """특정 컬럼의 표시/숨김 설정"""
        if not self.column_settings:
            self.column_settings = {}
        
        if field_name not in self.column_settings:
            self.column_settings[field_name] = {}
        
        self.column_settings[field_name]['visible'] = visible
        if order is not None:
            self.column_settings[field_name]['order'] = order
        
        self.save()
    
    @classmethod
    def get_user_columns(cls, user, page_name, default_columns):
        """
        사용자의 컬럼 설정을 가져오거나 기본 설정을 반환
        
        Args:
            user: Django User 객체
            page_name: 페이지명 (예: 'product_list')
            default_columns: 기본 컬럼 설정 리스트
        
        Returns:
            표시할 컬럼 설정 리스트
        """
        try:
            # 사용자 설정 조회
            user_setting = cls.objects.get(user=user, page_name=page_name)
            visible_fields = user_setting.get_visible_columns()
            
            if not visible_fields:
                # 설정이 비어있으면 기본 설정 사용
                return default_columns
            
            # 사용자 설정에 따라 컬럼 필터링 및 정렬
            filtered_columns = []
            for field_name in visible_fields:
                # 기본 컬럼 설정에서 해당 필드 찾기
                for col in default_columns:
                    if col['field'] == field_name:
                        filtered_columns.append(col)
                        break
            
            return filtered_columns if filtered_columns else default_columns
            
        except cls.DoesNotExist:
            # 사용자 설정이 없으면 기본 설정 사용
            return default_columns
    
    @classmethod
    def save_user_columns(cls, user, page_name, column_settings):
        """
        사용자의 컬럼 설정을 저장
        
        Args:
            user: Django User 객체
            page_name: 페이지명
            column_settings: {'field_name': {'visible': True, 'order': 1}, ...}
        """
        setting, created = cls.objects.get_or_create(
            user=user,
            page_name=page_name,
            defaults={'column_settings': column_settings}
        )
        
        if not created:
            setting.column_settings = column_settings
            setting.save()
        
        return setting