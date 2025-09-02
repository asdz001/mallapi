# members/views/member_detail.py
# 모든 오류 해결 완전 버전 - 한번에 모든 문제 해결

from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.core.serializers.json import DjangoJSONEncoder
from django.db import transaction
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.db import models
import json
import logging

# ✅ 필수 모델 import
from ..models import Member, MemberGrade, MemberGradeHistory

logger = logging.getLogger(__name__)

# ========================================
# 유틸리티 함수들
# ========================================

def safe_json_loads(data):
    """
    JSON 안전 파싱 - bytes 객체 처리 추가
    """
    try:
        # bytes 객체를 str로 변환
        if isinstance(data, bytes):
            data = data.decode('utf-8')
        
        # str 객체인 경우 JSON 파싱
        if isinstance(data, str):
            return json.loads(data)
        
        # 이미 dict인 경우 그대로 반환
        if isinstance(data, dict):
            return data
            
        # 그 외의 경우 빈 dict 반환
        return {}
        
    except (json.JSONDecodeError, TypeError, UnicodeDecodeError) as e:
        logger.error(f'JSON 파싱 오류: {str(e)}')
        return {}

def serialize_member_data(member):
    """회원 데이터 직렬화 - 등급 정보 포함"""
    try:
        data = {
            # 기본 정보
            'id': member.id,
            'username': member.username or '',
            'name': member.name or '',
            'member_type': member.member_type or '',
            'member_type_display': getattr(member, 'get_member_type_display', lambda: member.member_type)(),
            'email': member.email or '',
            'phone': member.phone or '',
            'home_phone': getattr(member, 'home_phone', '') or '',
            'address': getattr(member, 'address', '') or '',
            'zip_code': getattr(member, 'zip_code', '') or '',
            'is_active': getattr(member, 'is_active', True),
            
            # 마케팅 설정
            'marketing_agree': getattr(member, 'marketing_agree', False),
            'is_sms_agree': getattr(member, 'is_sms_agree', False),
            
            # 시스템 정보
            'is_blacklisted': getattr(member, 'is_blacklisted', False),
            'memo': getattr(member, 'memo', '') or '',
            'created_at': member.created_at,
            'created_at_display': member.created_at.strftime('%Y-%m-%d %H:%M') if member.created_at else '',
        }
        
        # 등급 정보 추가
        if hasattr(member, 'grade') and member.grade:
            data.update({
                'grade_id': member.grade.id,
                'grade_name': getattr(member.grade, 'display_name', None) or member.grade.name,
                'grade_color': getattr(member.grade, 'color_code', '#6c757d') or '#6c757d',
                'grade_icon': getattr(member.grade, 'icon_class', 'fas fa-user') or 'fas fa-user',
            })
        else:
            data.update({
                'grade_id': None,
                'grade_name': '등급없음',
                'grade_color': '#6c757d',
                'grade_icon': 'fas fa-user',
            })
            
        # 등급 고정 정보
        data.update({
            'grade_fixed': getattr(member, 'grade_fixed', False),
            'grade_fixed_reason': getattr(member, 'grade_fixed_reason', '') or '',
        })
        
        # B2C/B2B 필드 처리
        if member.member_type == 'B2C':
            data.update({
                'gender': getattr(member, 'gender', '') or '',
                'birth_date': str(getattr(member, 'birth_date', '')) if getattr(member, 'birth_date', None) else '',
                'nickname': getattr(member, 'nickname', '') or '',
                'recommender_id': getattr(member, 'recommender_id', '') or '',
                'join_channel': getattr(member, 'join_channel', '') or '',
                'is_forever_member': getattr(member, 'is_forever_member', False),
            })
            
        elif member.member_type == 'B2B':
            data.update({
                'company_name': getattr(member, 'company_name', '') or '',
                'business_number': getattr(member, 'business_number', '') or '',
                'representative_name': getattr(member, 'representative_name', '') or '',
                'business_type': getattr(member, 'business_type', '') or '',
                'business_item': getattr(member, 'business_item', '') or '',
                'company_phone': getattr(member, 'company_phone', '') or '',
                'fax': getattr(member, 'fax', '') or '',
                'company_address': getattr(member, 'company_address', '') or '',
            })
            
        return data
        
    except Exception as e:
        logger.error(f'회원 데이터 직렬화 오류: {str(e)}')
        return {'error': f'데이터 처리 중 오류: {str(e)}'}

def get_available_grades(member_type):
    """회원 타입에 맞는 등급 목록 반환"""
    try:
        grades = MemberGrade.objects.filter(
            models.Q(member_type=member_type) | models.Q(member_type='ALL'),
            is_active=True
        ).order_by('order', 'name')
        
        return [
            {
                'id': grade.id,
                'name': getattr(grade, 'display_name', None) or grade.name,
                'color': getattr(grade, 'color_code', '#6c757d') or '#6c757d',
                'icon': getattr(grade, 'icon_class', 'fas fa-user') or 'fas fa-user',
                'member_type': grade.member_type,
                'is_default': getattr(grade, 'is_default', False),
            }
            for grade in grades
        ]
    except Exception as e:
        logger.error(f'등급 목록 조회 오류: {str(e)}')
        return []

# ========================================
# API 함수들
# ========================================

@staff_member_required
@require_http_methods(["GET"])
def member_detail_api(request, member_id):
    """회원 상세보기 API"""
    try:
        member = get_object_or_404(
            Member.objects.select_related('grade'),
            id=member_id, 
            is_deleted=False
        )
        
        # 등급 변경 이력 조회 (최근 5개)
        grade_histories = []
        try:
            histories = MemberGradeHistory.objects.filter(
                member=member
            ).select_related('old_grade', 'new_grade', 'changed_by').order_by('-created_at')[:5]
            
            for history in histories:
                grade_histories.append({
                    'id': history.id,
                    'old_grade': getattr(history.old_grade, 'display_name', None) or getattr(history.old_grade, 'name', None) if history.old_grade else None,
                    'new_grade': getattr(history.new_grade, 'display_name', None) or getattr(history.new_grade, 'name', None) if history.new_grade else None,
                    'change_reason': getattr(history, 'get_change_reason_display', lambda: getattr(history, 'change_reason', ''))(),
                    'reason_detail': getattr(history, 'reason_detail', '') or '',
                    'changed_by': getattr(history.changed_by, 'username', 'system') if history.changed_by else 'system',
                    'created_at': history.created_at.strftime('%Y-%m-%d %H:%M') if hasattr(history, 'created_at') and history.created_at else '',
                })
        except Exception as e:
            logger.error(f'등급 이력 조회 오류: {str(e)}')
        
        # 사용 가능한 등급 목록
        available_grades = get_available_grades(member.member_type)
        
        return JsonResponse({
            'success': True,
            'member': serialize_member_data(member),
            'grade_histories': grade_histories,
            'available_grades': available_grades,
        })
        
    except Member.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': '존재하지 않는 회원입니다.'
        }, status=404)
        
    except Exception as e:
        logger.error(f'회원 상세조회 오류: {str(e)}', exc_info=True)
        return JsonResponse({
            'success': False,
            'message': f'회원 정보를 불러오는 중 오류가 발생했습니다: {str(e)}'
        }, status=500)



@staff_member_required 
@require_http_methods(["POST"])
@csrf_exempt
def member_update_api(request, member_id):
    """
    회원 정보 수정 API - safe_json_loads 수정으로 해결
    """
    try:
        # 회원 조회
        member = get_object_or_404(
            Member.objects.select_related('grade'),
            id=member_id,
            is_deleted=False
        )
        
        # JSON 데이터 파싱 (이제 bytes 처리 가능)
        data = safe_json_loads(request.body)
        if not data:
            return JsonResponse({
                'success': False,
                'message': '잘못된 요청 데이터입니다.'
            }, status=400)
        
        # 안전한 로깅 (data가 dict임을 보장)
        try:
            data_info = f"키: {list(data.keys())}" if isinstance(data, dict) else f"타입: {type(data)}"
            logger.info(f'회원 수정 요청: {member.username}, {data_info}')
        except Exception:
            logger.info(f'회원 수정 요청: {member.username}')
        
        # 트랜잭션으로 안전하게 처리
        with transaction.atomic():
            # 등급 변경 처리
            new_grade_id = data.get('grade_id')
            grade_change_reason = data.get('grade_change_reason', '관리자 수정')
            current_grade_id = member.grade.id if member.grade else None
            
            if new_grade_id and str(new_grade_id) != str(current_grade_id):
                try:
                    new_grade = MemberGrade.objects.get(id=new_grade_id, is_active=True)
                    
                    # 회원 타입 검증
                    if new_grade.member_type not in [member.member_type, 'ALL']:
                        return JsonResponse({
                            'success': False,
                            'message': f'해당 등급은 {member.member_type} 회원에게 적용할 수 없습니다.'
                        }, status=400)
                    
                    # 등급 변경 실행
                    member.change_grade(
                        new_grade=new_grade,
                        reason="manual",
                        changed_by=request.user,
                        reason_detail=grade_change_reason
                    )
                    
                    logger.info(f'등급 변경 완료: {member.username} -> {new_grade.name}')
                    
                except MemberGrade.DoesNotExist:
                    return JsonResponse({
                        'success': False,
                        'message': '존재하지 않는 등급입니다.'
                    }, status=400)
            
            # 등급 고정 처리
            grade_fixed = data.get('grade_fixed', False)
            grade_fixed_reason = data.get('grade_fixed_reason', '')
            
            current_fixed = getattr(member, 'grade_fixed', False)
            
            if grade_fixed != current_fixed:
                if grade_fixed:
                    # 등급 고정 설정
                    member.fix_grade(
                        reason=grade_fixed_reason or '관리자 수정',
                        fixed_by=request.user
                    )
                    logger.info(f'등급 고정 설정: {member.username}')
                else:
                    # 등급 고정 해제 (직접 처리)
                    member.grade_fixed = False
                    member.grade_fixed_reason = ''
                    member.grade_fixed_at = None
                    member.grade_fixed_by = None
                    logger.info(f'등급 고정 해제: {member.username}')
            
            # 기본 정보 업데이트
            basic_fields = ['name', 'email', 'phone', 'home_phone', 'address', 'zip_code', 
                           'is_active', 'marketing_agree', 'is_sms_agree', 'is_blacklisted', 'memo']
            
            for field in basic_fields:
                if field in data:
                    setattr(member, field, data[field])
            
            # 회원 타입별 필드 업데이트
            if member.member_type == 'B2C':
                b2c_fields = ['gender', 'birth_date', 'nickname', 'recommender_id', 
                             'join_channel', 'is_forever_member']
                for field in b2c_fields:
                    if field in data:
                        value = data[field]

                        # ✅ join_channel이 비어있으면 기본값 'direct'로 세팅
                        if field == 'join_channel' and not value:
                            value = 'direct'

                        # ✅ 날짜 필드 처리
                        if field == 'birth_date' and value:
                            try:
                                from datetime import datetime
                                if isinstance(value, str) and value:
                                    value = datetime.strptime(value, '%Y-%m-%d').date()
                            except ValueError:
                                continue

                        setattr(member, field, value)
            
            elif member.member_type == 'B2B':
                b2b_fields = ['company_name', 'business_number', 'representative_name', 
                             'business_type', 'business_item', 'company_phone', 'fax', 'company_address']
                for field in b2b_fields:
                    if field in data:
                        setattr(member, field, data[field])
            
            # 최종 저장
            member.save()
            
            logger.info(f'회원 정보 수정 완료: {member.username}')
        
        # 성공 응답
        return JsonResponse({
            'success': True,
            'message': '회원 정보가 성공적으로 수정되었습니다.',
            'member': serialize_member_data(member)
        })
        
    except Member.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': '존재하지 않는 회원입니다.'
        }, status=404)
        
    except Exception as e:
        logger.error(f'회원 정보 수정 오류: {str(e)}', exc_info=True)
        return JsonResponse({
            'success': False,
            'message': f'회원 정보 수정 중 오류가 발생했습니다: {str(e)}'
        }, status=500)
    



@staff_member_required
@require_http_methods(["GET"])
def member_activity_api(request, member_id):
    """회원 활동내역 API"""
    try:
        member = get_object_or_404(Member, id=member_id, is_deleted=False)
        
        activities = []
        
        # 등급 이력을 활동으로 변환
        try:
            grade_histories = MemberGradeHistory.objects.filter(
                member=member
            ).select_related('old_grade', 'new_grade', 'changed_by').order_by('-created_at')
            
            for history in grade_histories:
                old_name = getattr(history.old_grade, 'display_name', None) or getattr(history.old_grade, 'name', None) if history.old_grade else "없음"
                new_name = getattr(history.new_grade, 'display_name', None) or getattr(history.new_grade, 'name', None) if history.new_grade else "없음"
                
                activities.append({
                    'type': 'grade_change',
                    'title': '등급 변경',
                    'description': f'{old_name} → {new_name}',
                    'reason': getattr(history, 'get_change_reason_display', lambda: getattr(history, 'change_reason', ''))(),
                    'detail': getattr(history, 'reason_detail', '') or '',
                    'user': getattr(history.changed_by, 'username', 'system') if history.changed_by else 'system',
                    'created_at': history.created_at.strftime('%Y-%m-%d %H:%M:%S') if hasattr(history, 'created_at') and history.created_at else '',
                    'icon': 'fas fa-crown',
                    'color': 'primary'
                })
        except Exception as e:
            logger.error(f'등급 이력 조회 오류: {str(e)}')
        
        return JsonResponse({
            'success': True,
            'activities': activities
        })
        
    except Member.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': '존재하지 않는 회원입니다.'
        }, status=404)
        
    except Exception as e:
        logger.error(f'활동 로그 조회 오류: {str(e)}', exc_info=True)
        return JsonResponse({
            'success': False,
            'message': f'활동 로그를 불러오는 중 오류가 발생했습니다: {str(e)}'
        }, status=500)

@staff_member_required
@require_http_methods(["GET"])  
def get_member_grades_api(request, member_type):
    """회원 타입별 등급 선택 옵션 조회 API"""
    try:
        grades = MemberGrade.objects.filter(
            models.Q(member_type=member_type) | models.Q(member_type='ALL'),
            is_active=True
        ).order_by('order', 'name')
        
        grades_data = []
        for grade in grades:
            grades_data.append({
                'id': grade.id,
                'name': getattr(grade, 'display_name', None) or grade.name,
                'color': getattr(grade, 'color_code', '#6c757d') or '#6c757d',
                'icon': getattr(grade, 'icon_class', 'fas fa-user') or 'fas fa-user',
                'member_type': grade.member_type,
                'is_default': getattr(grade, 'is_default', False),
                'discount_rate': float(getattr(grade, 'discount_rate', 0)),
                'point_rate': float(getattr(grade, 'point_rate', 0)),
            })
        
        return JsonResponse({
            'success': True,
            'grades': grades_data
        })
        
    except Exception as e:
        logger.error(f'등급 목록 조회 오류: {str(e)}', exc_info=True)
        return JsonResponse({
            'success': False,
            'message': f'등급 목록을 불러오는 중 오류가 발생했습니다: {str(e)}'
        }, status=500)