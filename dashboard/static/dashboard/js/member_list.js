/**
 * ========================================
 * 📁 파일 위치: dashboard/static/dashboard/js/member_list.js
 * 🎯 목적: 회원 목록 페이지 전용 기능
 * 📅 버전: 1.0
 * 🔄 의존성: search_engine.js, jQuery, AdminLTE(로컬), Bootstrap(로컬)
 * ========================================
 */

/**
 * 🎯 회원 목록 관리 객체
 */
const MemberList = {
    
    /**
     * 🔧 초기화
     */
    init: function() {
        console.log('👥 회원 목록 관리 모듈 초기화 중...');
        
        this.bindEvents();
        this.initializeCheckboxes();
    },
    
    /**
     * 🔧 이벤트 바인딩
     */
    bindEvents: function() {
        const self = this;
        
        // 전체 선택/해제 체크박스
        $('#select-all').on('change', function() {
            self.toggleAllCheckboxes(this.checked);
        });
        
        // 개별 체크박스 변경
        $(document).on('change', 'input[name="member_ids"]', function() {
            self.updateBulkButtons();
            self.updateSelectAllState();
        });
        
        // 벌크 액션 버튼들
        $('#bulk-delete').on('click', function() {
            self.bulkDelete();
        });
        
        $('#bulk-deactivate').on('click', function() {
            self.bulkDeactivate();
        });
        
        // 개별 액션 버튼들 (이벤트 위임 사용)
        $(document).on('click', '.btn-view-member', function() {
            const memberId = $(this).data('member-id');
            self.viewMember(memberId);
        });
        
        $(document).on('click', '.btn-edit-member', function() {
            const memberId = $(this).data('member-id');
            self.editMember(memberId);
        });
        
        $(document).on('click', '.btn-delete-member', function() {
            const memberId = $(this).data('member-id');
            self.showDeleteModal(memberId);
        });
    },
    
    /**
     * 🔧 체크박스 초기화
     */
    initializeCheckboxes: function() {
        this.updateBulkButtons();
        this.updateSelectAllState();
    },
    
    /**
     * 🎯 전체 선택/해제
     * @param {boolean} checked - 선택 상태
     */
    toggleAllCheckboxes: function(checked) {
        $('input[name="member_ids"]').prop('checked', checked);
        this.updateBulkButtons();
    },
    
    /**
     * 🎯 벌크 액션 버튼 상태 업데이트
     */
    updateBulkButtons: function() {
        const checkedCount = $('input[name="member_ids"]:checked').length;
        const bulkButtons = $('#bulk-delete, #bulk-deactivate');
        
        if (checkedCount > 0) {
            bulkButtons.prop('disabled', false);
            bulkButtons.removeClass('btn-outline-secondary').addClass('btn-outline-danger');
        } else {
            bulkButtons.prop('disabled', true);
            bulkButtons.removeClass('btn-outline-danger').addClass('btn-outline-secondary');
        }
    },
    
    /**
     * 🎯 전체 선택 체크박스 상태 업데이트
     */
    updateSelectAllState: function() {
        const totalCheckboxes = $('input[name="member_ids"]').length;
        const checkedCheckboxes = $('input[name="member_ids"]:checked').length;
        
        const selectAllCheckbox = $('#select-all');
        
        if (checkedCheckboxes === 0) {
            selectAllCheckbox.prop('checked', false);
            selectAllCheckbox.prop('indeterminate', false);
        } else if (checkedCheckboxes === totalCheckboxes) {
            selectAllCheckbox.prop('checked', true);
            selectAllCheckbox.prop('indeterminate', false);
        } else {
            selectAllCheckbox.prop('checked', false);
            selectAllCheckbox.prop('indeterminate', true);
        }
    },
    
    /**
     * 🎯 선택된 회원 ID 목록 가져오기
     * @returns {Array} 선택된 회원 ID 배열
     */
    getSelectedMemberIds: function() {
        const selectedIds = [];
        $('input[name="member_ids"]:checked').each(function() {
            selectedIds.push($(this).val());
        });
        return selectedIds;
    },
    
    /**
     * 🗑️ 벌크 삭제 - 🆕 삭제 사유 모달 연동으로 수정
     */
    bulkDelete: function() {
        const selectedIds = this.getSelectedMemberIds();
        
        if (selectedIds.length === 0) {
            alert('삭제할 회원을 선택해주세요.');
            return;
        }
        
        // 🆕 삭제 사유 모달 표시 (기존 confirm 대신)
        this.showDeleteReasonModal('bulk', selectedIds);
    },
    
    /**
     * 🚫 벌크 비활성화
     */
    bulkDeactivate: function() {
        const selectedIds = this.getSelectedMemberIds();
        
        if (selectedIds.length === 0) {
            alert('비활성화할 회원을 선택해주세요.');
            return;
        }
        
        const confirmMessage = `선택된 ${selectedIds.length}명의 회원을 비활성화하시겠습니까?`;
        
        if (confirm(confirmMessage)) {
            this.showLoadingState('#bulk-deactivate', '처리 중...');
            
            // TODO: 실제 AJAX 요청으로 구현
            setTimeout(() => {
                alert(`${selectedIds.length}명의 회원이 비활성화되었습니다. (구현 예정)`);
                this.hideLoadingState('#bulk-deactivate', '선택 비활성화');
                // 페이지 새로고침 또는 상태 업데이트
                // window.location.reload();
            }, 1000);
        }
    },
    
    /**
     * 👁️ 회원 상세보기
     * @param {string|number} memberId - 회원 ID
     */
    viewMember: function(memberId) {
        console.log(`회원 상세보기: ${memberId}`);
        
        // TODO: 모달 또는 새 페이지로 이동
        alert(`회원 상세보기 기능 구현 예정\n회원 ID: ${memberId}`);
        
        // 향후 구현:
        // window.location.href = `/dashboard/members/${memberId}/`;
        // 또는 모달로 상세정보 표시
    },
    
    /**
     * ✏️ 회원 정보 수정
     * @param {string|number} memberId - 회원 ID
     */
    editMember: function(memberId) {
        console.log(`회원 정보 수정: ${memberId}`);
        
        // TODO: 수정 페이지로 이동
        alert(`회원 정보 수정 기능 구현 예정\n회원 ID: ${memberId}`);
        
        // 향후 구현:
        // window.location.href = `/dashboard/members/${memberId}/edit/`;
    },
    
    /**
     * 🗑️ 삭제 확인 모달 표시 - 🆕 삭제 사유 모달 연동으로 수정
     * @param {string|number} memberId - 회원 ID
     */
    showDeleteModal: function(memberId) {
        // 🆕 삭제 사유 모달 표시 (기존 confirm 대신)
        this.showDeleteReasonModal('single', [memberId]);
    },
    
    /**
     * 🆕 삭제 사유 입력 모달 표시 (새로 추가된 함수)
     * @param {string} type - 'single' 또는 'bulk'
     * @param {Array} memberIds - 회원 ID 배열
     */
    showDeleteReasonModal: function(type, memberIds) {
        const modal = $('#deleteReasonModal');
        const targetInfo = $('#deleteTargetInfo');
        
        // 모달 설정
        $('#deleteType').val(type);
        if (type === 'single') {
            $('#targetMemberId').val(memberIds[0]);
            $('#targetMemberIds').val('');
            
            // 단일 회원 정보 표시
            const row = $(`tr[data-member-id="${memberIds[0]}"]`);
            const username = row.find('td').eq(1).text().trim();
            const name = row.find('td').eq(2).text().trim();
            targetInfo.html(`<i class="fas fa-user"></i> ${username} (${name})`);
        } else {
            $('#targetMemberId').val('');
            $('#targetMemberIds').val(memberIds.join(','));
            targetInfo.html(`<i class="fas fa-users"></i> 선택된 ${memberIds.length}명의 회원`);
        }
        
        // 폼 초기화
        $('#deleteReason').val('');
        $('#confirmDeleteBtn').prop('disabled', false);
        
        // 모달 표시
        modal.modal('show');
    },
    
    /**
     * 🗑️ 회원 삭제 - 🆕 실제 AJAX 구현으로 수정
     * @param {string|number} memberId - 회원 ID
     * @param {string} deleteReason - 삭제 사유 (새로 추가된 파라미터)
     */
    deleteMember: function(memberId, deleteReason) {
        console.log(`회원 삭제 처리: ${memberId}`);
        
        this.showLoadingState(`.btn-delete-member[data-member-id="${memberId}"]`, '삭제 중...');
        
        // 🆕 실제 AJAX 삭제 요청 (기존 TODO 구현)
        $.ajax({
            url: `/dashboard/members/delete/${memberId}`,
            method: 'POST',
            data: {
                'csrfmiddlewaretoken': $('[name=csrfmiddlewaretoken]').val(),
                'delete_reason': deleteReason
            },
            success: function(response) {
                if (response.success) {
                    // 성공 시 해당 행 제거
                    $(`tr[data-member-id="${memberId}"]`).fadeOut(300, function() {
                        $(this).remove();
                    });
                    
                    // 성공 메시지 표시
                    alert(response.message);
                    
                    // 체크박스 상태 업데이트
                    MemberList.updateBulkButtons();
                    MemberList.updateSelectAllState();
                } else {
                    alert('삭제 실패: ' + response.message);
                }
            },
            error: function() {
                alert('삭제 중 오류가 발생했습니다.');
            },
            complete: function() {
                MemberList.hideLoadingState(`.btn-delete-member[data-member-id="${memberId}"]`, '<i class="fas fa-trash"></i>');
            }
        });
    },
    
    /**
     * 🆕 벌크 삭제 실행 (새로 추가된 함수)
     * @param {Array} memberIds - 회원 ID 배열
     * @param {string} deleteReason - 삭제 사유
     */
    executeBulkDelete: function(memberIds, deleteReason) {
        this.showLoadingState('#bulk-delete', '삭제 중...');
        
        // 실제 AJAX 벌크 삭제 요청
        $.ajax({
            url: '/dashboard/members/bulk-action',
            method: 'POST',
            data: {
                'csrfmiddlewaretoken': $('[name=csrfmiddlewaretoken]').val(),
                'action': 'delete',
                'member_ids[]': memberIds,
                'delete_reason': deleteReason
            },
            success: function(response) {
                if (response.success) {
                    // 성공 시 해당 행들 제거
                    memberIds.forEach(function(id) {
                        $(`tr[data-member-id="${id}"]`).fadeOut(300, function() {
                            $(this).remove();
                        });
                    });
                    
                    // 성공 메시지 표시
                    alert(response.message);
                    
                    // 체크박스 상태 초기화
                    $('#select-all').prop('checked', false);
                    MemberList.updateBulkButtons();
                } else {
                    alert('삭제 실패: ' + response.message);
                }
            },
            error: function() {
                alert('벌크 삭제 중 오류가 발생했습니다.');
            },
            complete: function() {
                MemberList.hideLoadingState('#bulk-delete', '<i class="fas fa-trash"></i> 선택 삭제');
            }
        });
    },
    
    /**
     * 🔄 로딩 상태 표시
     * @param {string} selector - 버튼 선택자
     * @param {string} text - 로딩 텍스트
     */
    showLoadingState: function(selector, text) {
        const button = $(selector);
        button.data('original-text', button.html());
        button.prop('disabled', true);
        button.html(`<i class="fas fa-spinner fa-spin"></i> ${text}`);
    },
    
    /**
     * 🔄 로딩 상태 해제
     * @param {string} selector - 버튼 선택자
     * @param {string} originalText - 원본 텍스트 (선택사항)
     */
    hideLoadingState: function(selector, originalText = null) {
        const button = $(selector);
        const text = originalText || button.data('original-text') || '처리완료';
        
        button.prop('disabled', false);
        button.html(text);
    },
    
    /**
     * 🛠️ 유틸리티: 현재 선택된 회원 수 표시
     */
    updateSelectionInfo: function() {
        const selectedCount = this.getSelectedMemberIds().length;
        const totalCount = $('input[name="member_ids"]').length;
        
        // 선택 정보 표시 영역이 있다면 업데이트
        $('.selection-info').text(`${selectedCount}/${totalCount} 선택됨`);
    }
};

/**
 * ========================================
 * 🚀 자동 초기화 (DOM 로드 완료 시)
 * ========================================
 */
$(document).ready(function() {
    // 회원 목록 페이지에서만 초기화
    if ($('#member-list-table').length > 0 || $('input[name="member_ids"]').length > 0) {
        MemberList.init();
        console.log('✅ 회원 목록 관리 모듈이 초기화되었습니다.');
    }
    
    // 툴팁 초기화 (AdminLTE/Bootstrap 로컬 버전 대응)
    if (typeof $().tooltip === 'function') {
        $('[data-toggle="tooltip"]').tooltip({
            container: 'body',
            trigger: 'hover'
        });
    }
    
    // 페이지당 표시 개수 변경 이벤트
    $('#per_page').on('change', function() {
        changePerPage(this.value);
    });
    
    // 🆕 삭제 사유 모달 이벤트 처리 (새로 추가된 부분)
    $('#deleteReasonModal').on('shown.bs.modal', function() {
        $('#deleteReason').focus();
    });
    
    // 🆕 삭제 사유 입력 검증 (새로 추가된 부분)
    $('#deleteReason').on('input', function() {
        const reason = $(this).val().trim();
        const confirmBtn = $('#confirmDeleteBtn');
        
        if (reason.length >= 5) {
            confirmBtn.prop('disabled', false);
        } else {
            confirmBtn.prop('disabled', true);
        }
    });
    
    // 🆕 삭제 확인 버튼 클릭 (새로 추가된 부분)
    $('#confirmDeleteBtn').on('click', function() {
        const deleteType = $('#deleteType').val();
        const deleteReason = $('#deleteReason').val().trim();
        
        if (deleteReason.length < 5) {
            alert('삭제 사유를 최소 5자 이상 입력해주세요.');
            return;
        }
        
        // 모달 숨기기
        $('#deleteReasonModal').modal('hide');
        
        // 삭제 실행
        if (deleteType === 'single') {
            const memberId = $('#targetMemberId').val();
            MemberList.deleteMember(memberId, deleteReason);
        } else {
            const memberIds = $('#targetMemberIds').val().split(',');
            MemberList.executeBulkDelete(memberIds, deleteReason);
        }
    });
});

/**
 * 🔧 페이지당 표시 개수 변경 함수
 * @param {number} value - 표시할 개수
 */
function changePerPage(value) {
    const currentUrl = new URL(window.location);
    currentUrl.searchParams.set('per_page', value);
    currentUrl.searchParams.delete('page'); // 페이지는 1로 리셋
    window.location.href = currentUrl.toString();
}

/**
 * ========================================
 * 🔧 전역 접근용 (다른 스크립트에서 사용 가능)
 * ========================================
 */
window.MemberList = MemberList;