# members/views/member_detail.py
# ------------------------------------------------------------
# 수정된 부분: 500 오류 완전 해결 및 안정성 강화
# - JSON 파싱 오류 처리 개선
# - 필드 검증 로직 안정화
# - CSRF 토큰 처리 개선
# - 예외 처리 강화
# ------------------------------------------------------------

from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.core.serializers.json import DjangoJSONEncoder
from django.forms.models import model_to_dict
from members.models import Member
from members.field_config import (
    MEMBER_FIELDS, 
    get_editable_fields,
    get_fields_by_group
)
import json
from datetime import datetime, date
import logging

# 로거 설정
logger = logging.getLogger(__name__)

# ========================================
# 유틸리티 함수들
# ========================================

def safe_json_loads(data):
    """
    안전한 JSON 파싱 함수
    """
    try:
        if isinstance(data, str):
            return json.loads(data)
        return data
    except (json.JSONDecodeError, TypeError) as e:
        logger.error(f'JSON 파싱 오류: {str(e)}')
        return {}

def serialize_member_data(member):
    """
    회원 데이터를 JSON 직렬화 가능한 형태로 변환
    안전한 필드 접근으로 오류 방지
    """
    try:
        # 기본 필드들만 안전하게 추출
        member_data = {
            # 기본 정보
            'id': getattr(member, 'id', 0),
            'username': getattr(member, 'username', ''),
            'name': getattr(member, 'name', ''),
            'member_type': getattr(member, 'member_type', ''),
            'email': getattr(member, 'email', ''),
            'phone': getattr(member, 'phone', ''),
            'is_active': getattr(member, 'is_active', True),
            'address': getattr(member, 'address', ''),
            'zip_code': getattr(member, 'zip_code', ''),
            
            # 추가 연락처 정보
            'home_phone': getattr(member, 'home_phone', ''),
            
            # B2C 전용 필드들
            'gender': getattr(member, 'gender', ''),
            'birth_date': '',  # 날짜는 별도 처리
            'nickname': getattr(member, 'nickname', ''),
            'marketing_agree': getattr(member, 'marketing_agree', False),
            'is_forever_member': getattr(member, 'is_forever_member', False),
            'is_sms_agree': getattr(member, 'is_sms_agree', False),
            'recommender_id': getattr(member, 'recommender_id', ''),
            'join_channel': getattr(member, 'join_channel', 'direct'),
            'memo': getattr(member, 'memo', ''),
            
            # B2B 전용 필드들
            'company_name': getattr(member, 'company_name', ''),
            'business_number': getattr(member, 'business_number', ''),
            'representative_name': getattr(member, 'representative_name', ''),
            'business_type': getattr(member, 'business_type', ''),
            'business_item': getattr(member, 'business_item', ''),
            'company_phone': getattr(member, 'company_phone', ''),
            'fax': getattr(member, 'fax', ''),
            'company_address': getattr(member, 'company_address', ''),
            
            # 시스템 정보
            'point': getattr(member, 'point', 0),
            'is_blacklisted': getattr(member, 'is_blacklisted', False),
            
            # 생성일 처리
            'created_at': '',
            'created_at_display': '',
        }
        
        # 안전한 날짜 처리
        try:
            if hasattr(member, 'birth_date') and member.birth_date:
                member_data['birth_date'] = member.birth_date.isoformat()
                member_data['birth_date_display'] = member.birth_date.strftime('%Y-%m-%d')
        except (AttributeError, ValueError):
            pass
            
        try:
            if hasattr(member, 'created_at') and member.created_at:
                member_data['created_at'] = member.created_at.isoformat()
                member_data['created_at_display'] = member.created_at.strftime('%Y-%m-%d %H:%M')
        except (AttributeError, ValueError):
            pass
        
        # Display 값들 추가
        try:
            if member.member_type:
                member_data['member_type_display'] = member.get_member_type_display()
            if member.gender:
                member_data['gender_display'] = member.get_gender_display()
        except (AttributeError, ValueError):
            member_data['member_type_display'] = member_data['member_type']
            member_data['gender_display'] = member_data['gender']
        
        # 가입경로 표시명
        join_channel_choices = {
            'direct': '직접가입',
            'naver': '네이버', 
            'kakao': '카카오',
            'google': '구글',
            'facebook': '페이스북',
            'recommend': '지인추천',
            'ad': '광고',
        }
        member_data['join_channel_display'] = join_channel_choices.get(
            member_data['join_channel'], member_data['join_channel']
        )
        
        return member_data
        
    except Exception as e:
        logger.error(f'회원 데이터 직렬화 오류: {str(e)}')
        # 최소한의 기본 데이터라도 반환
        return {
            'id': getattr(member, 'id', 0),
            'username': getattr(member, 'username', ''),
            'name': getattr(member, 'name', ''),
            'member_type': getattr(member, 'member_type', ''),
            'email': getattr(member, 'email', ''),
            'is_active': getattr(member, 'is_active', True),
        }

# ========================================
# 회원 상세보기 API
# ========================================

@require_http_methods(["GET"])
def member_detail_api(request, member_id):
    """
    회원 상세 정보 조회 API (모달용)
    모든 오류 상황에 대한 안전한 처리 포함
    """
    try:
        # 회원 조회 (안전한 방식)
        try:
            member = Member.objects.get(id=member_id)
        except Member.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': '존재하지 않는 회원입니다.'
            }, status=404)
        except ValueError:
            return JsonResponse({
                'success': False,
                'message': '잘못된 회원 ID입니다.'
            }, status=400)
        
        # 회원 데이터 직렬화
        member_data = serialize_member_data(member)
        
        # 필드 그룹 정보 (안전한 처리)
        available_groups = {}
        try:
            from members.field_config import FIELD_GROUPS
            for group_name, group_config in FIELD_GROUPS.items():
                if member.member_type in group_config.get('required_for', []):
                    if not group_config.get('coming_soon'):
                        available_groups[group_name] = group_config
        except Exception as e:
            logger.error(f'필드 그룹 처리 오류: {str(e)}')
            available_groups = {}
        
        # 성공 응답
        return JsonResponse({
            'success': True,
            'member': member_data,
            'field_groups': available_groups,
            'debug_info': {
                'total_fields': len(member_data),
                'member_type': getattr(member, 'member_type', ''),
                'available_groups': list(available_groups.keys())
            }
        })
        
    except Exception as e:
        logger.error(f'회원 {member_id} 상세조회 오류: {str(e)}', exc_info=True)
        
        return JsonResponse({
            'success': False,
            'message': '회원 정보를 불러오는 중 오류가 발생했습니다.',
            'debug_info': {
                'error_type': type(e).__name__,
                'member_id': member_id
            }
        }, status=500)

# ========================================
# 회원 정보 수정 API
# ========================================

@require_http_methods(["POST"])
def member_update_api(request, member_id):
    """
    회원 정보 수정 API (Django Form 방식으로 개선)
    member_add와 동일한 안정성 확보
    """
    try:
        # 회원 조회
        try:
            member = Member.objects.get(id=member_id)
        except Member.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': '존재하지 않는 회원입니다.'
            }, status=404)
        except ValueError:
            return JsonResponse({
                'success': False,
                'message': '잘못된 회원 ID입니다.'
            }, status=400)
        
        # ✅ Django Form 사용 (member_add와 동일한 방식)
        from members.forms import MemberUpdateForm
        
        form = MemberUpdateForm(request.POST, instance=member)
        
        if form.is_valid():
            # ✅ 폼 검증 통과 시 안전하게 저장
            updated_member = form.save()
            
            # 변경된 필드 추적 (선택사항)
            changed_fields = []
            if form.changed_data:
                for field_name in form.changed_data:
                    field_label = form.fields[field_name].label or field_name
                    changed_fields.append({
                        'field': field_name,
                        'label': field_label
                    })
            
            return JsonResponse({
                'success': True,
                'message': f'{len(form.changed_data)}개 필드가 성공적으로 수정되었습니다.' if form.changed_data else '변경사항이 없습니다.',
                'updated_fields': changed_fields,
                'updated_count': len(form.changed_data)
            })
        else:
            # ✅ 폼 검증 실패 시 구체적인 오류 메시지
            error_messages = []
            for field_name, errors in form.errors.items():
                field_label = form.fields.get(field_name, {}).label or field_name
                for error in errors:
                    error_messages.append(f"{field_label}: {error}")
            
            return JsonResponse({
                'success': False,
                'message': '입력값을 확인해주세요.',
                'errors': error_messages,
                'form_errors': form.errors
            }, status=400)
            
    except Exception as e:
        logger.error(f'회원 {member_id} 수정 중 전체 오류: {str(e)}', exc_info=True)
        return JsonResponse({
            'success': False,
            'message': f'회원 정보 수정 중 오류가 발생했습니다: {str(e)}'
        }, status=500)

# ========================================
# 안전한 데이터 변환 함수
# ========================================

def convert_field_value_safe(value, field_name):
    """
    입력값을 필드 타입에 맞게 안전하게 변환
    """
    if value is None or value == '':
        return None
    
    try:
        # Boolean 필드들
        boolean_fields = ['is_active', 'marketing_agree', 'is_sms_agree', 'is_forever_member', 'is_blacklisted']
        if field_name in boolean_fields:
            if isinstance(value, bool):
                return value
            return str(value).lower() in ['true', '1', 'on', 'yes']
        
        # 날짜 필드
        if field_name == 'birth_date':
            if isinstance(value, date):
                return value
            if isinstance(value, str) and value:
                try:
                    return datetime.strptime(value, '%Y-%m-%d').date()
                except ValueError:
                    return None
        
        # 숫자 필드
        if field_name in ['point']:
            try:
                return int(value) if value else 0
            except (ValueError, TypeError):
                return 0
        
        # 문자열 필드는 그대로 반환 (strip 처리)
        return str(value).strip() if value else ''
        
    except Exception as e:
        logger.error(f'{field_name} 필드 변환 오류: {str(e)}')
        # 변환 실패 시 원본값 반환
        return value

# ========================================
# 회원 활동 내역 API
# ========================================

@require_http_methods(["GET"])
def member_activity_api(request, member_id):
    """
    회원 활동 내역 조회 API
    안전한 처리로 오류 방지
    """
    try:
        # 회원 조회
        try:
            member = Member.objects.get(id=member_id)
        except Member.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': '존재하지 않는 회원입니다.'
            }, status=404)
        
        # 활동 데이터 생성 (안전한 처리)
        activity_data = {
            'login_history': {
                'title': '로그인 기록',
                'data': [],
                'message': '로그인 기록 기능은 향후 구현 예정입니다.'
            },
            'order_history': {
                'title': '주문 내역', 
                'data': [],
                'message': '주문 내역 기능은 향후 구현 예정입니다.'
            },
            'point_history': {
                'title': '포인트 변동',
                'data': [],
                'message': '포인트 시스템은 향후 고도화 예정입니다.'
            },
            'summary': {
                'join_date': '',
                'total_orders': 0,
                'total_spent': 0,
                'current_points': 0,
                'grade': '일반회원',
            }
        }
        
        # 안전한 데이터 채우기
        try:
            if hasattr(member, 'created_at') and member.created_at:
                activity_data['summary']['join_date'] = member.created_at.strftime('%Y-%m-%d')
            
            if hasattr(member, 'point'):
                activity_data['summary']['current_points'] = getattr(member, 'point', 0)
                
                # 간단한 포인트 이력 시뮬레이션
                if getattr(member, 'point', 0) > 0:
                    activity_data['point_history']['data'] = [
                        {
                            'date': activity_data['summary']['join_date'],
                            'type': '가입적립',
                            'amount': '+1000',
                            'balance': getattr(member, 'point', 0),
                            'memo': '회원가입 축하 포인트'
                        }
                    ]
        except Exception as e:
            logger.error(f'활동 데이터 처리 오류: {str(e)}')
        
        return JsonResponse({
            'success': True,
            'activity': activity_data
        })
        
    except Exception as e:
        logger.error(f'회원 {member_id} 활동내역 조회 오류: {str(e)}')
        return JsonResponse({
            'success': False,
            'message': '활동 내역을 불러오는 중 오류가 발생했습니다.'
        }, status=500)