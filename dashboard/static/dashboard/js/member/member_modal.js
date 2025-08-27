/**
 * ========================================
 * 📁 파일 위치: dashboard/static/dashboard/js/member/member_modal.js
 * 🎯 목적: 회원 모달 관련 기능
 * 버전: 1.0
 * ========================================
 */

const MemberModal = {

    // 현재 조회중인 회원 정보
    currentMember: null,

    // 수정 모드 상태
    isEditMode: false,

    /**
     * 초기화
     */
    init: function () {
        console.log('회원 모달 관리 모듈 초기화 중...');

        this.bindEvents();
        this.initializeModals();
    },

    /**
     * 이벤트 바인딩 - 기존 방식 유지
     */
    bindEvents: function () {
        const self = this;

        // 수정 1: 모달 닫기 버튼 - 기존 방식에 추가만
        $(document).on('click', '#memberModal .close, #memberModal [data-dismiss="modal"]', function (e) {
            e.preventDefault();
            $('#memberModal').modal('hide');
        });

        // 모달 닫힐 때 초기화 - 기존과 동일
        $('#memberModal').on('hidden.bs.modal', function () {
            self.resetModal();
        });

        // Bootstrap 4/5 호환성을 위한 이벤트 처리 - 기존과 동일
        $('#memberModal').on('hide.bs.modal', function () {
            self.resetModal();
        });

        // 수정 모드 토글 버튼 - 기존과 동일
        $(document).on('click', '#editModeBtn', function () {
            self.enableEditMode();
        });

        // 수정 저장 버튼 - 기존과 동일
        $(document).on('click', '#saveMemberBtn', function () {
            self.saveMember();
        });

        // 수정 취소 버튼 - 기존과 동일
        $(document).on('click', '#cancelEditBtn', function () {
            self.cancelEdit();
        });

        // 수정 2: 탭 전환 - Bootstrap 기본 이벤트만 사용
        $('#memberModal .nav-tabs a').on('click', function (e) {
            e.preventDefault();
            $(this).tab('show'); // Bootstrap 기본 탭 전환
        });

        // 수정 3: Bootstrap 탭 이벤트로 활동내역 로드
        $('#memberModal .nav-tabs a[href="#tab-activity"]').on('shown.bs.tab', function () {
            self.loadActivityData();
        });
    },

    /**
     * 모달 초기화 - 기존과 동일
     */
    initializeModals: function () {
        // 기본 탭 활성화
        this.showTab('#tab-member-info');
    },

    /**
     * 회원 상세보기 모달 열기 - 기존과 동일
     */
    showMemberDetail: function (memberId) {
        console.log(`회원 상세보기 모달 열기: ${memberId}`);

        // 모달 열기
        $('#memberModal').modal('show');

        // 로딩 상태 표시
        this.showLoadingState();

        // API 호출하여 회원 정보 조회
        $.ajax({
            url: `/dashboard/members/detail/${memberId}`,
            method: 'GET',
            success: function (response) {
                console.log('API 응답 받음:', response);
                if (response.success) {
                    MemberModal.displayMemberData(response.member);
                    MemberModal.currentMember = response.member;
                    MemberModal.hideLoadingState();
                } else {
                    alert('회원 정보를 불러올 수 없습니다: ' + response.message);
                    $('#memberModal').modal('hide');
                }
            },
            error: function (xhr) {
                console.error('API 호출 오류:', xhr);
                let errorMessage = '회원 정보를 불러오는 중 오류가 발생했습니다.';
                if (xhr.status === 404) {
                    errorMessage = '존재하지 않는 회원입니다.';
                }
                alert(errorMessage);
                $('#memberModal').modal('hide');
            }
        });
    },

    /**
     * 회원 정보를 모달에 표시 - 기존과 동일
     */
    displayMemberData: function (member) {
        console.log('회원 데이터 표시:', member);

        // 모달 제목 설정
        $('#memberModalLabel').html(`
            <i class="fas fa-user"></i> 
            ${member.name || '이름없음'} (${member.username}) - ${member.member_type_display || member.member_type}
        `);

        // 상태 배지 설정
        const statusBadge = member.is_active
            ? '<span class="badge badge-success">활성</span>'
            : '<span class="badge badge-secondary">비활성</span>';
        $('#modal-status-badge').html(statusBadge);
        $('#modal-member-type-badge').text(member.member_type_display || member.member_type);
        $('#modal-created-at').text(member.created_at_display || member.created_at || '');

        // 통합된 회원정보 탭 채우기
        this.fillMemberInfo(member);

        // 마케팅설정 탭 채우기
        this.fillMarketingInfo(member);

        // 시스템정보 탭 채우기
        this.fillSystemInfo(member);

        // 기본 탭으로 전환
        this.showTab('#tab-member-info');
    },

    /**
     * 통합된 회원정보 채우기 - 기존과 동일
     */
    fillMemberInfo: function (member) {
        // 기본 정보
        $('#modal-username').val(member.username || '');
        $('#modal-name').val(member.name || '');
        $('#modal-member-type').val(member.member_type_display || member.member_type || '');
        $('#modal-is-active').prop('checked', member.is_active);

        // 연락처 정보
        $('#modal-email').val(member.email || '');
        $('#modal-phone').val(member.phone || '');
        $('#modal-home-phone').val(member.home_phone || '');
        $('#modal-address').val(member.address || '');
        $('#modal-zip-code').val(member.zip_code || '');

        // B2C 전용 필드들
        if (member.member_type === 'B2C') {
            $('.b2c-fields').show();
            $('.b2b-fields').hide();

            $('#modal-gender').val(member.gender || '');
            $('#modal-birth-date').val(member.birth_date || '');
            $('#modal-nickname').val(member.nickname || '');
            $('#modal-recommender-id').val(member.recommender_id || '');
            $('#modal-join-channel').val(member.join_channel || 'direct');
            $('#modal-is-forever-member').prop('checked', member.is_forever_member || false);
        }

        // B2B 전용 필드들
        if (member.member_type === 'B2B') {
            $('.b2b-fields').show();
            $('.b2c-fields').hide();

            $('#modal-company-name').val(member.company_name || '');
            $('#modal-business-number').val(member.business_number || '');
            $('#modal-representative-name').val(member.representative_name || '');
            $('#modal-business-type').val(member.business_type || '');
            $('#modal-business-item').val(member.business_item || '');
            $('#modal-company-phone').val(member.company_phone || '');
            $('#modal-fax').val(member.fax || '');
            $('#modal-company-address').val(member.company_address || '');
        }
    },

    /**
     * 마케팅 정보 채우기 - 기존과 동일
     */
    fillMarketingInfo: function (member) {
        $('#modal-marketing-agree').prop('checked', member.marketing_agree || false);
        $('#modal-is-sms-agree').prop('checked', member.is_sms_agree || false);
        $('#modal-join-channel-display').val(member.join_channel_display || member.join_channel || 'direct');
    },

    /**
     * 시스템 정보 채우기 - 기존과 동일
     */
    fillSystemInfo: function (member) {
        const pointDisplay = member.point ? parseInt(member.point).toLocaleString() : '0';
        $('#modal-point').val(pointDisplay);
        $('#modal-is-blacklisted').prop('checked', member.is_blacklisted || false);
        $('#modal-memo').val(member.memo || '');
    },

    /**
     * 수정 모드 활성화 - 기존과 동일
     */
    enableEditMode: function () {
        console.log('수정 모드 활성화');
        this.isEditMode = true;

        $('#memberModal input:not([data-readonly]), #memberModal select, #memberModal textarea').prop('disabled', false);
        $('#modal-username, #modal-member-type, #modal-created-at, #modal-point').prop('disabled', true);

        $('#view-mode-buttons').hide();
        $('#edit-mode-buttons').show();
        $('#edit-mode-indicator').show();

        $('#memberModal .modal-header').addClass('bg-warning text-dark');
        $('#memberModalLabel').prepend('<i class="fas fa-edit"></i> [수정 중] ');

        $('#modal-name').focus();
    },

    /**
     * 수정 모드 비활성화 - 기존과 동일
     */
    disableEditMode: function () {
        console.log('수정 모드 비활성화');
        this.isEditMode = false;

        $('#memberModal input, #memberModal select, #memberModal textarea').prop('disabled', true);

        $('#view-mode-buttons').show();
        $('#edit-mode-buttons').hide();
        $('#edit-mode-indicator').hide();

        $('#memberModal .modal-header').removeClass('bg-warning text-dark');

        if (this.currentMember) {
            this.displayMemberData(this.currentMember);
        }
    },

    // member_modal.js의 saveMember 함수 수정 (332라인 근처)

    /**
    * 회원 정보 저장 - Django Form 방식으로 개선
    */
    saveMember: function () {
        if (!this.currentMember) {
            alert('저장할 회원 정보가 없습니다.');
            return;
        }

        console.log('회원 정보 저장 시작 - Django Form 방식');

        // 폼 데이터 수집
        const formData = this.collectFormData();

        // ✅ CSRF 토큰을 데이터에 포함 (Django 표준 방식)
        formData['csrfmiddlewaretoken'] = $('[name=csrfmiddlewaretoken]').val();

        // 로딩 상태 표시
        this.showLoadingState('#saveMemberBtn', '저장 중...');

        // ✅ member_add와 동일한 AJAX 방식
        $.ajax({
            url: `/dashboard/members/update/${this.currentMember.id}`,
            method: 'POST',
            data: formData,  // ✅ 일반 form data로 전송 (JSON 아님)
            // headers 제거 - Django가 자동으로 CSRF 처리
            success: function (response) {
                if (response.success) {
                    alert(response.message);

                    // 현재 회원 데이터 업데이트
                    MemberModal.updateCurrentMemberData(formData);
                    MemberModal.disableEditMode();

                    console.log('회원 정보 수정 완료:', response);
                } else {
                    // ✅ 구체적인 오류 메시지 표시
                    let errorMsg = response.message || '저장에 실패했습니다.';
                    if (response.errors && response.errors.length > 0) {
                        errorMsg += '\n\n세부 오류:\n' + response.errors.join('\n');
                    }
                    alert(errorMsg);
                }
            },
            error: function (xhr, status, error) {
                console.error('저장 오류:', { xhr, status, error });

                let errorMessage = '저장 중 오류가 발생했습니다.';

                // ✅ 서버 응답에서 구체적 오류 메시지 추출
                if (xhr.responseJSON && xhr.responseJSON.message) {
                    errorMessage = xhr.responseJSON.message;

                    // 폼 검증 오류도 함께 표시
                    if (xhr.responseJSON.errors) {
                        errorMessage += '\n\n' + xhr.responseJSON.errors.join('\n');
                    }
                } else if (xhr.status === 404) {
                    errorMessage = '존재하지 않는 회원입니다.';
                } else if (xhr.status === 400) {
                    errorMessage = '잘못된 요청입니다. 입력값을 확인해주세요.';
                } else if (xhr.status === 500) {
                    errorMessage = '서버 오류가 발생했습니다. 관리자에게 문의하세요.';
                }

                alert(errorMessage);
            },
            complete: function () {
                MemberModal.hideLoadingState('#saveMemberBtn', '<i class="fas fa-save"></i> 저장');
            }
        });
    },

    /**
     * 폼 데이터 수집 - 기존과 동일
     */
    collectFormData: function () {
        const formData = {
            name: $('#modal-name').val(),
            is_active: $('#modal-is-active').is(':checked'),
            email: $('#modal-email').val(),
            phone: $('#modal-phone').val(),
            home_phone: $('#modal-home-phone').val(),
            address: $('#modal-address').val(),
            zip_code: $('#modal-zip-code').val(),
            marketing_agree: $('#modal-marketing-agree').is(':checked'),
            is_sms_agree: $('#modal-is-sms-agree').is(':checked'),
            is_blacklisted: $('#modal-is-blacklisted').is(':checked'),
            memo: $('#modal-memo').val(),
        };

        if (this.currentMember.member_type === 'B2C') {
            Object.assign(formData, {
                gender: $('#modal-gender').val(),
                birth_date: $('#modal-birth-date').val(),
                nickname: $('#modal-nickname').val(),
                recommender_id: $('#modal-recommender-id').val(),
                join_channel: $('#modal-join-channel').val(),
                is_forever_member: $('#modal-is-forever-member').is(':checked'),
            });
        }

        if (this.currentMember.member_type === 'B2B') {
            Object.assign(formData, {
                company_name: $('#modal-company-name').val(),
                business_number: $('#modal-business-number').val(),
                representative_name: $('#modal-representative-name').val(),
                business_type: $('#modal-business-type').val(),
                business_item: $('#modal-business-item').val(),
                company_phone: $('#modal-company-phone').val(),
                fax: $('#modal-fax').val(),
                company_address: $('#modal-company-address').val(),
            });
        }

        return formData;
    },

    /**
     * 현재 회원 데이터 업데이트 - 기존과 동일
     */
    updateCurrentMemberData: function (newData) {
        if (this.currentMember) {
            Object.assign(this.currentMember, newData);
        }
    },

    /**
     * 수정 취소 - 기존과 동일
     */
    cancelEdit: function () {
        if (confirm('수정 중인 내용이 있습니다. 취소하시겠습니까?')) {
            this.disableEditMode();
        }
    },

    /**
     * 활동 내역 데이터 로드 - 기존과 동일
     */
    loadActivityData: function () {
        if (!this.currentMember) return;

        console.log('활동 내역 데이터 로드');

        $('#activity-content').html(`
            <div class="text-center text-muted py-4">
                <i class="fas fa-spinner fa-spin fa-2x mb-3"></i>
                <p>활동 내역을 불러오는 중...</p>
            </div>
        `);

        $.ajax({
            url: `/dashboard/members/activity/${this.currentMember.id}`,
            method: 'GET',
            success: function (response) {
                if (response.success) {
                    MemberModal.displayActivityData(response.activity);
                } else {
                    $('#activity-content').html(`
                        <div class="text-center text-muted py-4">
                            <i class="fas fa-exclamation-triangle fa-2x mb-3 text-warning"></i>
                            <p>활동 내역을 불러올 수 없습니다.</p>
                        </div>
                    `);
                }
            },
            error: function () {
                $('#activity-content').html(`
                    <div class="text-center text-muted py-4">
                        <i class="fas fa-exclamation-triangle fa-2x mb-3 text-danger"></i>
                        <p>활동 내역 로딩 중 오류가 발생했습니다.</p>
                    </div>
                `);
            }
        });
    },

    /**
     * 활동 내역 표시 - 기존과 동일
     */
    displayActivityData: function (activity) {
        // 기존과 동일한 구현
        $('#activity-content').html('<p>활동 내역이 표시됩니다.</p>');
    },

    /**
     * 탭 전환 - Bootstrap 기본 방식 사용
     */
    showTab: function (tabId) {
        // Bootstrap 기본 탭 전환 사용
        $(`#memberModal .nav-tabs a[href="${tabId}"]`).tab('show');
    },

    /**
     * 모달 초기화 - 기존과 동일
     */
    resetModal: function () {
        console.log('모달 초기화');

        this.currentMember = null;
        this.isEditMode = false;

        $('#memberModal input, #memberModal select, #memberModal textarea').val('');
        $('#memberModal input[type="checkbox"]').prop('checked', false);

        $('#view-mode-buttons').show();
        $('#edit-mode-buttons').hide();
        $('#edit-mode-indicator').hide();

        $('#memberModal .modal-header').removeClass('bg-warning text-dark');

        $('.b2c-fields, .b2b-fields').hide();

        this.showTab('#tab-member-info');

        $('#modal-content').hide();
        $('#modal-loading').show();
    },

    /**
     * 로딩 상태 표시 - 기존과 동일
     */
    showLoadingState: function (selector = null, text = '로딩 중...') {
        if (selector) {
            const button = $(selector);
            button.data('original-text', button.html());
            button.prop('disabled', true);
            button.html(`<i class="fas fa-spinner fa-spin"></i> ${text}`);
        } else {
            $('#modal-loading').show();
            $('#modal-content').hide();
        }
    },

    /**
     * 로딩 상태 해제 - 기존과 동일
     */
    hideLoadingState: function (selector = null, originalText = null) {
        if (selector) {
            const button = $(selector);
            const text = originalText || button.data('original-text') || '완료';

            button.prop('disabled', false);
            button.html(text);
        } else {
            $('#modal-loading').hide();
            $('#modal-content').show();
        }
    }
};

/**
 * 자동 초기화
 */
$(document).ready(function () {
    if ($('#member-list-table').length > 0 || $('.btn-view-member').length > 0) {
        MemberModal.init();
        console.log('회원 모달 관리 모듈이 초기화되었습니다.');
    }

    if (typeof $().tooltip === 'function') {
        $('[data-toggle="tooltip"]').tooltip({
            container: 'body',
            trigger: 'hover'
        });
    }
});

/**
 * 전역 접근용
 */
window.MemberModal = MemberModal;