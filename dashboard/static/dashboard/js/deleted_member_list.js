/**
 * ========================================
 * 📁 파일 위치: dashboard/static/dashboard/js/deleted_member_list.js
 * 🎯 목적: 삭제 회원 관리 페이지 전용 기능
 * 📅 버전: 1.0
 * 🔄 의존성: search_engine.js, jQuery, AdminLTE(로컬), Bootstrap(로컬)
 * ========================================
 */

/**
 * 🎯 삭제 회원 관리 객체
 */
const DeletedMemberList = {
    
    /**
     * 🔧 초기화
     */
    init: function() {
        console.log('🗑️ 삭제 회원 관리 모듈 초기화 중...');
        
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
        $('#bulk-restore').on('click', function() {
            self.bulkRestore();
        });
        
        $('#bulk-permanent-delete').on('click', function() {
            self.bulkPermanentDelete();
        });
        
        // 개별 액션 버튼들 (이벤트 위임 사용)
        $(document).on('click', '.btn-restore-member', function() {
            const memberId = $(this).data('member-id');
            self.showRestoreModal(memberId);
        });
        
        $(document).on('click', '.btn-permanent-delete-member', function() {
            const memberId = $(this).data('member-id');
            self.showPermanentDeleteModal(memberId);
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
     * 🎯 전체 선택/해제 (복구 가능한 회원만)
     * @param {boolean} checked - 선택 상태
     */
    toggleAllCheckboxes: function(checked) {
        $('input[name="member_ids"]:not(:disabled)').prop('checked', checked);
        this.updateBulkButtons();
    },
    
    /**
     * 🎯 벌크 액션 버튼 상태 업데이트
     */
    updateBulkButtons: function() {
        const checkedCount = $('input[name="member_ids"]:checked').length;
        const bulkButtons = $('#bulk-restore, #bulk-permanent-delete');
        
        if (checkedCount > 0) {
            bulkButtons.prop('disabled', false);
            $('#bulk-restore').removeClass('btn-outline-secondary').addClass('btn-success');
            $('#bulk-permanent-delete').removeClass('btn-outline-secondary').addClass('btn-danger');
        } else {
            bulkButtons.prop('disabled', true);
            $('#bulk-restore').removeClass('btn-success').addClass('btn-outline-secondary');
            $('#bulk-permanent-delete').removeClass('btn-danger').addClass('btn-outline-secondary');
        }
    },
    
    /**
     * 🎯 전체 선택 체크박스 상태 업데이트
     */
    updateSelectAllState: function() {
        const totalCheckboxes = $('input[name="member_ids"]:not(:disabled)').length;
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
     * 🔄 벌크 복구
     */
    bulkRestore: function() {
        const selectedIds = this.getSelectedMemberIds();
        
        if (selectedIds.length === 0) {
            alert('복구할 회원을 선택해주세요.');
            return;
        }
        
        this.showRestoreModal('bulk', selectedIds);
    },
    
    /**
     * 🗑️ 벌크 완전삭제
     */
    bulkPermanentDelete: function() {
        const selectedIds = this.getSelectedMemberIds();
        
        if (selectedIds.length === 0) {
            alert('완전삭제할 회원을 선택해주세요.');
            return;
        }
        
        this.showPermanentDeleteModal('bulk', selectedIds);
    },
    
    /**
     * 🔄 복구 모달 표시
     * @param {string|number|string} target - 회원 ID 또는 'bulk'
     * @param {Array} memberIds - 벌크 작업 시 회원 ID 배열
     */
    showRestoreModal: function(target, memberIds = null) {
        const modal = $('#restoreModal');
        const targetInfo = $('#restoreTargetInfo');
        
        if (target === 'bulk') {
            targetInfo.html(`<strong>${memberIds.length}명의 선택된 회원</strong>을 복구하시겠습니까?`);
            modal.data('restore-type', 'bulk');
            modal.data('member-ids', memberIds);
        } else {
            const row = $(`tr[data-member-id="${target}"]`);
            const username = row.find('td').eq(1).text().trim();
            const name = row.find('td').eq(2).text().trim();
            targetInfo.html(`회원 <strong>${username} (${name})</strong>을 복구하시겠습니까?`);
            modal.data('restore-type', 'single');
            modal.data('member-id', target);
        }
        
        modal.modal('show');
    },
    
    /**
     * 🗑️ 완전삭제 모달 표시
     * @param {string|number|string} target - 회원 ID 또는 'bulk'
     * @param {Array} memberIds - 벌크 작업 시 회원 ID 배열
     */
    showPermanentDeleteModal: function(target, memberIds = null) {
        const modal = $('#permanentDeleteModal');
        const targetInfo = $('#permanentDeleteTargetInfo');
        
        if (target === 'bulk') {
            targetInfo.html(`<strong>${memberIds.length}명의 선택된 회원</strong>을 영구적으로 삭제합니다.`);
            modal.data('delete-type', 'bulk');
            modal.data('member-ids', memberIds);
        } else {
            const row = $(`tr[data-member-id="${target}"]`);
            const username = row.find('td').eq(1).text().trim();
            const name = row.find('td').eq(2).text().trim();
            targetInfo.html(`회원 <strong>${username} (${name})</strong>을 영구적으로 삭제합니다.`);
            modal.data('delete-type', 'single');
            modal.data('member-id', target);
        }
        
        // 확인 텍스트 초기화
        $('#confirmText').val('');
        $('#confirmPermanentDeleteBtn').prop('disabled', true);
        
        modal.modal('show');
    },
    
    /**
     * 🔄 회원 복구 실행
     * @param {string|number} memberId - 회원 ID
     */
    restoreMember: function(memberId) {
        this.showLoadingState(`.btn-restore-member[data-member-id="${memberId}"]`, '복구 중...');
        
        $.ajax({
            url: `/dashboard/members/deleted/restore/${memberId}`,  // 슬래시 제거
            method: 'POST',
            data: {
                'csrfmiddlewaretoken': $('[name=csrfmiddlewaretoken]').val()
            },
            success: function(response) {
                if (response.success) {
                    // 성공 시 해당 행 제거
                    $(`tr[data-member-id="${memberId}"]`).fadeOut(300, function() {
                        $(this).remove();
                    });
                    alert(response.message);
                    DeletedMemberList.updateBulkButtons();
                    DeletedMemberList.updateSelectAllState();
                } else {
                    alert('복구 실패: ' + response.message);
                }
            },
            error: function() {
                alert('복구 중 오류가 발생했습니다.');
            },
            complete: function() {
                DeletedMemberList.hideLoadingState(`.btn-restore-member[data-member-id="${memberId}"]`, '<i class="fas fa-undo"></i>');
            }
        });
    },
    
    /**
     * 🗑️ 회원 완전삭제 실행
     * @param {string|number} memberId - 회원 ID
     */
    permanentDeleteMember: function(memberId) {
        this.showLoadingState(`.btn-permanent-delete-member[data-member-id="${memberId}"]`, '삭제 중...');
        
        $.ajax({
            url: `/dashboard/members/deleted/permanent-delete/${memberId}`,  // 슬래시 제거
            method: 'POST',
            data: {
                'csrfmiddlewaretoken': $('[name=csrfmiddlewaretoken]').val()
            },
            success: function(response) {
                if (response.success) {
                    // 성공 시 해당 행 제거
                    $(`tr[data-member-id="${memberId}"]`).fadeOut(300, function() {
                        $(this).remove();
                    });
                    alert(response.message);
                    DeletedMemberList.updateBulkButtons();
                    DeletedMemberList.updateSelectAllState();
                } else {
                    alert('완전삭제 실패: ' + response.message);
                }
            },
            error: function() {
                alert('완전삭제 중 오류가 발생했습니다.');
            },
            complete: function() {
                DeletedMemberList.hideLoadingState(`.btn-permanent-delete-member[data-member-id="${memberId}"]`, '<i class="fas fa-times"></i>');
            }
        });
    },
    
    /**
     * 🔄 벌크 복구 실행
     * @param {Array} memberIds - 회원 ID 배열
     */
    executeBulkRestore: function(memberIds) {
        this.showLoadingState('#bulk-restore', '복구 중...');
        
        $.ajax({
            url: '/dashboard/members/deleted/bulk-restore',
            method: 'POST',
            data: {
                'csrfmiddlewaretoken': $('[name=csrfmiddlewaretoken]').val(),
                'member_ids[]': memberIds
            },
            success: function(response) {
                if (response.success) {
                    // 성공 시 해당 행들 제거
                    memberIds.forEach(function(id) {
                        $(`tr[data-member-id="${id}"]`).fadeOut(300, function() {
                            $(this).remove();
                        });
                    });
                    
                    alert(response.message);
                    $('#select-all').prop('checked', false);
                    DeletedMemberList.updateBulkButtons();
                } else {
                    alert('벌크 복구 실패: ' + response.message);
                }
            },
            error: function() {
                alert('벌크 복구 중 오류가 발생했습니다.');
            },
            complete: function() {
                DeletedMemberList.hideLoadingState('#bulk-restore', '<i class="fas fa-undo"></i> 선택 복구');
            }
        });
    },
    
    /**
     * 🗑️ 벌크 완전삭제 실행
     * @param {Array} memberIds - 회원 ID 배열
     */
    executeBulkPermanentDelete: function(memberIds) {
        this.showLoadingState('#bulk-permanent-delete', '삭제 중...');
        
        $.ajax({
            url: '/dashboard/members/deleted/bulk-permanent-delete',
            method: 'POST',
            data: {
                'csrfmiddlewaretoken': $('[name=csrfmiddlewaretoken]').val(),
                'member_ids[]': memberIds,
                'confirm_text': '영구삭제'
            },
            success: function(response) {
                if (response.success) {
                    // 성공 시 해당 행들 제거
                    memberIds.forEach(function(id) {
                        $(`tr[data-member-id="${id}"]`).fadeOut(300, function() {
                            $(this).remove();
                        });
                    });
                    
                    alert(response.message);
                    $('#select-all').prop('checked', false);
                    DeletedMemberList.updateBulkButtons();
                } else {
                    alert('벌크 완전삭제 실패: ' + response.message);
                }
            },
            error: function() {
                alert('벌크 완전삭제 중 오류가 발생했습니다.');
            },
            complete: function() {
                DeletedMemberList.hideLoadingState('#bulk-permanent-delete', '<i class="fas fa-times"></i> 선택 완전삭제');
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
    }
};

/**
 * ========================================
 * 🚀 자동 초기화 (DOM 로드 완료 시)
 * ========================================
 */
$(document).ready(function() {
    // 삭제 회원 관리 페이지에서만 초기화
    if ($('#deleted-member-list-table').length > 0) {
        DeletedMemberList.init();
        console.log('✅ 삭제 회원 관리 모듈이 초기화되었습니다.');
    }
    
    // 툴팁 초기화
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
    
    // 🆕 복구 확인 버튼 클릭
    $('#confirmRestoreBtn').on('click', function() {
        const modal = $('#restoreModal');
        const restoreType = modal.data('restore-type');
        
        modal.modal('hide');
        
        if (restoreType === 'single') {
            const memberId = modal.data('member-id');
            DeletedMemberList.restoreMember(memberId);
        } else {
            const memberIds = modal.data('member-ids');
            DeletedMemberList.executeBulkRestore(memberIds);
        }
    });
    
    // 🆕 완전삭제 확인 텍스트 검증
    $('#confirmText').on('input', function() {
        const confirmText = $(this).val();
        const confirmBtn = $('#confirmPermanentDeleteBtn');
        
        if (confirmText === '영구삭제') {
            confirmBtn.prop('disabled', false);
        } else {
            confirmBtn.prop('disabled', true);
        }
    });
    
    // 🆕 완전삭제 확인 버튼 클릭
    $('#confirmPermanentDeleteBtn').on('click', function() {
        const modal = $('#permanentDeleteModal');
        const deleteType = modal.data('delete-type');
        
        modal.modal('hide');
        
        if (deleteType === 'single') {
            const memberId = modal.data('member-id');
            DeletedMemberList.permanentDeleteMember(memberId);
        } else {
            const memberIds = modal.data('member-ids');
            DeletedMemberList.executeBulkPermanentDelete(memberIds);
        }
    });
    
    // 🆕 완전삭제 모달 닫힐 때 초기화
    $('#permanentDeleteModal').on('hidden.bs.modal', function() {
        $('#confirmText').val('');
        $('#confirmPermanentDeleteBtn').prop('disabled', true);
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
window.DeletedMemberList = DeletedMemberList;