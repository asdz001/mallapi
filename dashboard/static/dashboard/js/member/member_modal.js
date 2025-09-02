/**
 * ========================================
 * 📁 파일 위치: dashboard/static/dashboard/js/member/member_modal.js
 * 🎯 목적: 회원 모달 관련 기능 - 등급 관리 기능 추가
 * 버전: 3.0 (모든 오류 해결 최종)
 * ========================================
 */

const MemberModal = {
    // 현재 조회중인 회원 정보
    currentMember: null,
    
    // 수정 모드 상태
    isEditMode: false,
    
    // ✅ 사용 가능한 등급 목록
    availableGrades: [],
    
    // ✅ 등급 변경 사유 임시 저장
    pendingGradeChangeReason: null,

    /**
     * 초기화
     */
    init: function () {
        console.log('회원 모달 관리 모듈 초기화 중...');
        this.bindEvents();
        this.initializeModals();
    },

    /**
     * 이벤트 바인딩
     */
    bindEvents: function () {
        const self = this;

        // 모달 닫기 버튼
        $(document).on('click', '#memberModal .close, #memberModal [data-dismiss="modal"]', function (e) {
            e.preventDefault();
            $('#memberModal').modal('hide');
        });

        // 모달 닫힐 때 초기화
        $('#memberModal').on('hidden.bs.modal', function () {
            self.resetModal();
        });

        // 수정 모드 토글 버튼
        $(document).on('click', '#editModeBtn', function () {
            self.enableEditMode();
        });

        // 수정 저장 버튼
        $(document).on('click', '#saveMemberBtn', function () {
            self.saveMember();
        });

        // 수정 취소 버튼
        $(document).on('click', '#cancelEditBtn', function () {
            self.cancelEdit();
        });

        // 탭 전환 (기존 방식 유지)
        $('#memberModal .nav-tabs a').on('click', function (e) {
            e.preventDefault();
            $(this).tab('show');
        });

        // 활동내역 탭 활성화 시 데이터 로드
        $('#memberModal .nav-tabs a[href="#tab-activity"]').on('shown.bs.tab', function () {
            self.loadActivityData();
        });

        // ✅ 등급 변경 시 확인
        $(document).on('change', '#modal-grade', function() {
            if (self.isEditMode) {
                const selectedGradeId = $(this).val();
                const selectedGrade = self.availableGrades.find(g => g.id == selectedGradeId);
                
                if (selectedGrade && selectedGrade.id != (self.currentMember.grade_id || null)) {
                    self.showGradeChangeConfirm(selectedGrade);
                }
            }
        });

        // ✅ 등급 고정 체크박스 변경 시
        $(document).on('change', '#modal-grade-fixed', function() {
            const isFixed = $(this).is(':checked');
            const reasonGroup = $('#modal-grade-fixed-reason-edit-group');
            if (reasonGroup.length) {
                if (isFixed) {
                    reasonGroup.show();
                } else {
                    reasonGroup.hide();
                    $('#modal-grade-fixed-reason').val('');
                }
            }
        });
    },

    /**
     * 모달 초기화
     */
    initializeModals: function () {
        // 기본 탭 활성화
        this.showTab('#tab-member-info');
    },

    /**
     * 모달 리셋
     */
    resetModal: function () {
        this.currentMember = null;
        this.isEditMode = false;
        this.availableGrades = [];
        this.pendingGradeChangeReason = null;
        
        // 로딩 표시, 컨텐츠 숨김
        $('#modal-loading').show();
        $('#modal-content').hide();
        
        // 수정 모드 해제
        this.disableEditMode();
        
        console.log('회원 모달 리셋 완료');
    },

    /**
     * 회원 상세보기 모달 표시
     */
    showMemberDetail: function (memberId) {
        if (!memberId) {
            alert('회원 ID가 필요합니다.');
            return;
        }

        console.log(`회원 상세보기: ${memberId}`);
        
        // 모달 표시 및 로딩 상태
        $('#memberModal').modal('show');
        this.showLoadingState();

        // API 호출
        $.ajax({
            url: `/dashboard/members/detail/${memberId}`,
            method: 'GET',
            success: function (response) {
                console.log('회원 상세 데이터:', response);
                
                if (response.success) {
                    MemberModal.currentMember = response.member;
                    MemberModal.availableGrades = response.available_grades || [];
                    
                    // 화면에 데이터 표시
                    MemberModal.displayMemberData(response.member);
                    
                    // 등급 이력 표시
                    if (response.grade_histories) {
                        MemberModal.displayGradeHistory(response.grade_histories);
                    }
                    
                } else {
                    alert('회원 정보를 불러오지 못했습니다: ' + (response.message || '알 수 없는 오류'));
                    $('#memberModal').modal('hide');
                }
            },
            error: function (xhr) {
                console.error('회원 상세 조회 오류:', xhr);
                
                let errorMessage = '회원 정보를 불러오는 중 오류가 발생했습니다.';
                if (xhr.status === 404) {
                    errorMessage = '존재하지 않는 회원입니다.';
                } else if (xhr.status === 500) {
                    errorMessage = '서버 오류가 발생했습니다.';
                }
                
                alert(errorMessage);
                $('#memberModal').modal('hide');
            },
            complete: function () {
                MemberModal.hideLoadingState();
            }
        });
    },

    /**
     * 회원 데이터 표시
     */
    displayMemberData: function (member) {
        if (!member) {
            console.error('회원 데이터가 없습니다.');
            return;
        }

        console.log('회원 데이터 표시:', member);

        // 등급 표시 (안전하게)
        const gradeDisplay = member.grade_name && member.grade_name !== '등급없음' ?
            `<span class="badge ml-2" style="background-color: ${member.grade_color}; color: white;">
                <i class="${member.grade_icon}"></i> ${member.grade_name}
            </span>` : '';

        // 모달 제목 설정 (안전하게)
        const modalLabel = $('#memberModalLabel');
        if (modalLabel.length) {
            modalLabel.html(`
                <i class="fas fa-user"></i> 
                ${member.name || '이름없음'} (${member.username}) - ${member.member_type_display || member.member_type}
                ${gradeDisplay}
            `);
        }

        // 상태 배지 설정 (안전하게)
        const statusBadge = member.is_active
            ? '<span class="badge badge-success">활성</span>'
            : '<span class="badge badge-secondary">비활성</span>';
        
        this.safeSetHtml('#modal-status-badge', statusBadge);
        this.safeSetText('#modal-member-type-badge', member.member_type_display || member.member_type);
        this.safeSetText('#modal-created-at', member.created_at_display || member.created_at || '');

        // 탭별 정보 채우기
        this.fillMemberInfo(member);
        this.fillGradeInfo(member);
        this.fillMarketingInfo(member);
        this.fillSystemInfo(member);

        // 회원 타입별 필드 표시/숨김
        this.toggleMemberTypeFields(member.member_type);

        // 기본 탭으로 전환
        this.showTab('#tab-member-info');
    },

    /**
     * 안전한 DOM 조작 헬퍼 함수들
     */
    safeSetValue: function(selector, value) {
        const element = $(selector);
        if (element.length) {
            element.val(value || '');
        }
    },

    safeSetText: function(selector, text) {
        const element = $(selector);
        if (element.length) {
            element.text(text || '');
        }
    },

    safeSetHtml: function(selector, html) {
        const element = $(selector);
        if (element.length) {
            element.html(html || '');
        }
    },

    safeSetChecked: function(selector, checked) {
        const element = $(selector);
        if (element.length) {
            element.prop('checked', !!checked);
        }
    },

    /**
     * 회원 타입별 필드 표시/숨김
     */
    toggleMemberTypeFields: function(memberType) {
        const b2cFields = $('#b2c-fields');
        const b2bFields = $('#b2b-fields');
        
        if (memberType === 'B2C') {
            b2cFields.show();
            b2bFields.hide();
        } else if (memberType === 'B2B') {
            b2cFields.hide();
            b2bFields.show();
        } else {
            b2cFields.hide();
            b2bFields.hide();
        }
    },

    /**
     * 통합된 회원정보 채우기
     */
    fillMemberInfo: function (member) {
        // 기본 정보
        this.safeSetValue('#modal-username', member.username);
        this.safeSetValue('#modal-name', member.name);
        this.safeSetValue('#modal-member-type', member.member_type_display || member.member_type);
        this.safeSetChecked('#modal-is-active', member.is_active);

        // 연락처 정보
        this.safeSetValue('#modal-email', member.email);
        this.safeSetValue('#modal-phone', member.phone);
        this.safeSetValue('#modal-home-phone', member.home_phone);
        this.safeSetValue('#modal-address', member.address);
        this.safeSetValue('#modal-zip-code', member.zip_code);

        // B2C 전용 필드
        if (member.member_type === 'B2C') {
            this.safeSetValue('#modal-gender', member.gender);
            this.safeSetValue('#modal-birth-date', member.birth_date);
            this.safeSetValue('#modal-nickname', member.nickname);
            this.safeSetValue('#modal-recommender-id', member.recommender_id);
            this.safeSetValue('#modal-join-channel', member.join_channel);
            this.safeSetChecked('#modal-is-forever-member', member.is_forever_member);
        }

        // B2B 전용 필드
        if (member.member_type === 'B2B') {
            this.safeSetValue('#modal-company-name', member.company_name);
            this.safeSetValue('#modal-business-number', member.business_number);
            this.safeSetValue('#modal-representative-name', member.representative_name);
            this.safeSetValue('#modal-business-type', member.business_type);
            this.safeSetValue('#modal-business-item', member.business_item);
            this.safeSetValue('#modal-company-phone', member.company_phone);
            this.safeSetValue('#modal-fax', member.fax);
            this.safeSetValue('#modal-company-address', member.company_address);
        }
    },

    /**
     * ✅ 등급정보 탭 채우기
     */
    fillGradeInfo: function (member) {
        // 현재 등급 표시
        const currentGradeEl = $('#modal-current-grade');
        if (currentGradeEl.length) {
            const gradeDisplay = member.grade_name && member.grade_name !== '등급없음' ?
                `<span class="badge badge-lg" style="background-color: ${member.grade_color}; color: white;">
                    <i class="${member.grade_icon}"></i> ${member.grade_name}
                </span>` : '<span class="text-muted">등급 없음</span>';
            
            currentGradeEl.html(gradeDisplay);
        }
        
        // 등급 고정 정보
        const gradeFixedStatusEl = $('#modal-grade-fixed-status');
        if (gradeFixedStatusEl.length) {
            const gradeFixedIcon = member.grade_fixed ? 
                '<i class="fas fa-lock text-warning"></i>' : '<i class="fas fa-unlock text-muted"></i>';
            const gradeFixedText = member.grade_fixed ? '고정됨' : '고정 안됨';
            
            gradeFixedStatusEl.html(`${gradeFixedIcon} ${gradeFixedText}`);
        }
        
        // 고정 사유 표시
        const gradeFixedReasonDisplayEl = $('#modal-grade-fixed-reason-display');
        if (gradeFixedReasonDisplayEl.length) {
            gradeFixedReasonDisplayEl.text(member.grade_fixed_reason || '-');
            
            // 고정 사유 그룹 표시/숨김
            const reasonGroup = $('#modal-grade-fixed-reason-group');
            if (reasonGroup.length) {
                if (member.grade_fixed && member.grade_fixed_reason) {
                    reasonGroup.show();
                } else {
                    reasonGroup.hide();
                }
            }
        }

        // 등급 선택 드롭다운 구성 (수정 모드용)
        this.setupGradeSelectOptions();
        
        // 등급 관련 입력 필드 설정
        this.safeSetChecked('#modal-grade-fixed', member.grade_fixed);
        this.safeSetValue('#modal-grade-fixed-reason', member.grade_fixed_reason);
    },

    /**
     * ✅ 등급 선택 드롭다운 구성
     */
    setupGradeSelectOptions: function() {
        const gradeSelect = $('#modal-grade');
        
        if (!gradeSelect.length) {
            console.warn('등급 선택 요소(#modal-grade)를 찾을 수 없습니다.');
            return;
        }
        
        gradeSelect.empty();
        gradeSelect.append('<option value="">등급 선택</option>');
        
        if (this.availableGrades && this.availableGrades.length > 0) {
            this.availableGrades.forEach(grade => {
                const isSelected = this.currentMember && (this.currentMember.grade_id == grade.id);
                const defaultText = grade.is_default ? ' (기본)' : '';
                
                gradeSelect.append(
                    `<option value="${grade.id}" ${isSelected ? 'selected' : ''}>
                        [${grade.member_type}] ${grade.name}${defaultText}
                    </option>`
                );
            });
        }
    },

    /**
     * 등급 변경 이력 표시
     */
    displayGradeHistory: function(histories) {
        const historyContainer = $('#grade-history-list');
        if (!historyContainer.length) return;
        
        if (!histories || histories.length === 0) {
            historyContainer.html(`
                <div class="text-center text-muted py-3">
                    <i class="fas fa-info-circle"></i> 등급 변경 이력이 없습니다.
                </div>
            `);
            return;
        }
        
        let historyHtml = '';
        histories.forEach(history => {
            historyHtml += `
                <div class="border-bottom pb-2 mb-2">
                    <div class="d-flex justify-content-between align-items-start">
                        <div>
                            <strong>${history.old_grade || '없음'} → ${history.new_grade || '없음'}</strong>
                            <div class="text-muted small">
                                사유: ${history.change_reason || '-'}
                                ${history.reason_detail ? ` (${history.reason_detail})` : ''}
                            </div>
                        </div>
                        <div class="text-right">
                            <div class="text-muted small">${history.changed_by || 'system'}</div>
                            <div class="text-muted small">${history.created_at || ''}</div>
                        </div>
                    </div>
                </div>
            `;
        });
        
        historyContainer.html(historyHtml);
    },

    /**
     * ✅ 등급 변경 확인 다이얼로그
     */
    showGradeChangeConfirm: function(newGrade) {
        const currentGradeName = this.currentMember.grade_name || '없음';
        
        if (confirm(`등급을 "${currentGradeName}"에서 "${newGrade.name}"(으)로 변경하시겠습니까?`)) {
            const reason = prompt('등급 변경 사유를 입력하세요:', '관리자 수정');
            
            if (reason !== null) {
                this.pendingGradeChangeReason = reason || '관리자 수정';
            } else {
                // 취소 시 원래 값으로 되돌림
                $('#modal-grade').val(this.currentMember.grade_id || '');
                this.pendingGradeChangeReason = null;
            }
        } else {
            // 취소 시 원래 값으로 되돌림
            $('#modal-grade').val(this.currentMember.grade_id || '');
            this.pendingGradeChangeReason = null;
        }
    },

    /**
     * 마케팅설정 탭 채우기
     */
    fillMarketingInfo: function (member) {
        this.safeSetChecked('#modal-marketing-agree', member.marketing_agree);
        this.safeSetChecked('#modal-is-sms-agree', member.is_sms_agree);
    },

    /**
     * 시스템정보 탭 채우기
     */
    fillSystemInfo: function (member) {
        this.safeSetChecked('#modal-is-blacklisted', member.is_blacklisted);
        this.safeSetValue('#modal-memo', member.memo);
    },

    /**
     * 탭 전환
     */
    showTab: function (tabId) {
        $('#memberModal .nav-tabs .nav-link').removeClass('active');
        $('#memberModal .tab-pane').removeClass('active show');
        
        $(`#memberModal .nav-tabs .nav-link[href="${tabId}"]`).addClass('active');
        $(tabId).addClass('active show');
    },

    /**
     * 수정 모드 활성화
     */
    enableEditMode: function () {
        if (!this.currentMember) {
            alert('회원 정보를 먼저 불러와주세요.');
            return;
        }

        this.isEditMode = true;

        // 기본 필드들 활성화
        const basicFields = [
            '#modal-name', '#modal-email', '#modal-phone', '#modal-home-phone', 
            '#modal-address', '#modal-zip-code', '#modal-memo', '#modal-is-active',
            '#modal-marketing-agree', '#modal-is-sms-agree', '#modal-is-blacklisted'
        ];
        
        basicFields.forEach(selector => {
            const element = $(selector);
            if (element.length) {
                element.prop('disabled', false);
            }
        });

        // 등급 관련 필드 활성화
        const gradeFields = ['#modal-grade', '#modal-grade-fixed', '#modal-grade-fixed-reason'];
        gradeFields.forEach(selector => {
            const element = $(selector);
            if (element.length) {
                element.prop('disabled', false);
            }
        });

        // 회원 타입별 필드 활성화
        if (this.currentMember.member_type === 'B2C') {
            const b2cFields = [
                '#modal-gender', '#modal-birth-date', '#modal-nickname',
                '#modal-recommender-id', '#modal-join-channel', '#modal-is-forever-member'
            ];
            b2cFields.forEach(selector => {
                const element = $(selector);
                if (element.length) {
                    element.prop('disabled', false);
                }
            });
        } else if (this.currentMember.member_type === 'B2B') {
            const b2bFields = [
                '#modal-company-name', '#modal-business-number', '#modal-representative-name',
                '#modal-business-type', '#modal-business-item', '#modal-company-phone',
                '#modal-fax', '#modal-company-address'
            ];
            b2bFields.forEach(selector => {
                const element = $(selector);
                if (element.length) {
                    element.prop('disabled', false);
                }
            });
        }

        // 등급 수정 섹션 표시
        const gradeEditSection = $('#grade-edit-section');
        if (gradeEditSection.length) {
            gradeEditSection.show();
        }

        // 등급 고정 사유 입력 영역 처리
        const isFixed = $('#modal-grade-fixed').is(':checked');
        const reasonEditGroup = $('#modal-grade-fixed-reason-edit-group');
        if (reasonEditGroup.length) {
            if (isFixed) {
                reasonEditGroup.show();
            } else {
                reasonEditGroup.hide();
            }
        }

        // ✅ 버튼 상태 변경 (단순화)
        $('#editModeBtn').hide();
        $('#saveMemberBtn, #cancelEditBtn').show();

        console.log('수정 모드 활성화됨');
    },

    /**
     * 수정 모드 비활성화
     */
    disableEditMode: function () {
        this.isEditMode = false;
        this.pendingGradeChangeReason = null;

        // 모든 입력 필드 비활성화
        $('#memberModal input, #memberModal textarea, #memberModal select').prop('disabled', true);

        // 등급 수정 섹션 숨기기
        const gradeEditSection = $('#grade-edit-section');
        if (gradeEditSection.length) {
            gradeEditSection.hide();
        }

        // ✅ 버튼 상태 변경 (단순화)
        $('#editModeBtn').show();
        $('#saveMemberBtn, #cancelEditBtn').hide();

        console.log('수정 모드 비활성화됨');
    },

    /**
     * 로딩 상태 표시
     */
    showLoadingState: function (buttonSelector = null, loadingText = null) {
        if (buttonSelector) {
            $(buttonSelector).prop('disabled', true);
            if (loadingText) {
                $(buttonSelector).html(loadingText);
            }
        } else {
            $('#modal-loading').show();
            $('#modal-content').hide();
        }
    },

    /**
     * 로딩 상태 해제
     */
    hideLoadingState: function (buttonSelector = null, originalText = null) {
        if (buttonSelector && originalText) {
            $(buttonSelector).prop('disabled', false).html(originalText);
        } else {
            $('#modal-loading').hide();
            $('#modal-content').show();
        }
    },

    /**
     * 회원 정보 저장
     */
    saveMember: function () {
        if (!this.currentMember || !this.isEditMode) {
            alert('수정 모드가 아닙니다.');
            return;
        }

        // 필수 필드 검증
        const name = $('#modal-name').val().trim();
        const email = $('#modal-email').val().trim();
        
        if (!name) {
            alert('이름을 입력해주세요.');
            $('#modal-name').focus();
            return;
        }
        
        if (!email) {
            alert('이메일을 입력해주세요.');
            $('#modal-email').focus();
            return;
        }

        // 폼 데이터 수집
        const formData = this.collectFormData();
        
        // 등급 변경 사유 추가
        if (this.pendingGradeChangeReason) {
            formData.grade_change_reason = this.pendingGradeChangeReason;
        }

        console.log('💾 저장할 데이터:', formData);

        // 로딩 상태 표시
        this.showLoadingState('#saveMemberBtn', '<i class="fas fa-spinner fa-spin"></i> 저장중...');

        // API 호출
        $.ajax({
            url: `/dashboard/members/update/${this.currentMember.id}`,
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify(formData),
            timeout: 30000,
            success: function (response) {
                console.log('✅ 저장 성공:', response);
                
                if (response.success) {
                    alert('회원 정보가 성공적으로 수정되었습니다.');
                    
                    // 현재 회원 데이터 업데이트
                    MemberModal.updateCurrentMemberData(response.member);
                    
                    // 화면 다시 표시 (읽기 모드로)
                    MemberModal.displayMemberData(response.member);
                    MemberModal.disableEditMode();
                    
                    // 회원 목록 새로고침 (있다면)
                    if (typeof MemberList !== 'undefined' && MemberList.refreshList) {
                        MemberList.refreshList();
                    }
                    
                    // 등급 변경 사유 초기화
                    MemberModal.pendingGradeChangeReason = null;
                    
                } else {
                    alert('저장 실패: ' + (response.message || '알 수 없는 오류가 발생했습니다.'));
                }
            },
            error: function (xhr, textStatus, errorThrown) {
                console.error('❌ 저장 오류:', {
                    status: xhr.status,
                    statusText: xhr.statusText,
                    responseText: xhr.responseText,
                    textStatus: textStatus,
                    errorThrown: errorThrown
                });
                
                let errorMessage = '저장 중 오류가 발생했습니다.';
                
                if (xhr.status === 0) {
                    errorMessage = '네트워크 연결을 확인해주세요.';
                } else if (xhr.status === 400) {
                    try {
                        const response = JSON.parse(xhr.responseText);
                        errorMessage = response.message || '입력값을 확인해주세요.';
                    } catch (e) {
                        errorMessage = '입력값을 확인해주세요.';
                    }
                } else if (xhr.status === 404) {
                    errorMessage = '존재하지 않는 회원입니다.';
                } else if (xhr.status === 500) {
                    errorMessage = '서버 오류가 발생했습니다. 관리자에게 문의하세요.';
                } else if (textStatus === 'timeout') {
                    errorMessage = '요청 시간이 초과되었습니다. 다시 시도해주세요.';
                }

                alert(errorMessage);
            },
            complete: function () {
                MemberModal.hideLoadingState('#saveMemberBtn', '<i class="fas fa-save"></i> 저장');
            }
        });
    },

    /**
     * 폼 데이터 수집
     */
    collectFormData: function () {
        const formData = {
            // 기본 정보
            name: $('#modal-name').val().trim(),
            is_active: $('#modal-is-active').is(':checked'),
            email: $('#modal-email').val().trim(),
            phone: $('#modal-phone').val().trim(),
            home_phone: $('#modal-home-phone').val().trim(),
            address: $('#modal-address').val().trim(),
            zip_code: $('#modal-zip-code').val().trim(),
            
            // 마케팅 설정
            marketing_agree: $('#modal-marketing-agree').is(':checked'),
            is_sms_agree: $('#modal-is-sms-agree').is(':checked'),
            
            // 시스템 정보
            is_blacklisted: $('#modal-is-blacklisted').is(':checked'),
            memo: $('#modal-memo').val().trim(),
            
            // ✅ 등급 관련 데이터
            grade_id: $('#modal-grade').val() || null,
            grade_fixed: $('#modal-grade-fixed').is(':checked'),
            grade_fixed_reason: $('#modal-grade-fixed-reason').val().trim(),
        };

        // 회원 타입별 데이터 추가
        if (this.currentMember.member_type === 'B2C') {
            Object.assign(formData, {
                gender: $('#modal-gender').val() || null,
                birth_date: $('#modal-birth-date').val() || null,
                nickname: $('#modal-nickname').val().trim(),
                recommender_id: $('#modal-recommender-id').val().trim(),
                join_channel: $('#modal-join-channel').val() || null,
                is_forever_member: $('#modal-is-forever-member').is(':checked'),
            });
        }

        if (this.currentMember.member_type === 'B2B') {
            Object.assign(formData, {
                company_name: $('#modal-company-name').val().trim(),
                business_number: $('#modal-business-number').val().trim(),
                representative_name: $('#modal-representative-name').val().trim(),
                business_type: $('#modal-business-type').val().trim(),
                business_item: $('#modal-business-item').val().trim(),
                company_phone: $('#modal-company-phone').val().trim(),
                fax: $('#modal-fax').val().trim(),
                company_address: $('#modal-company-address').val().trim(),
            });
        }

        return formData;
    },

    /**
     * 현재 회원 데이터 업데이트
     */
    updateCurrentMemberData: function (newData) {
        if (this.currentMember) {
            Object.assign(this.currentMember, newData);
        }
    },

    /**
     * 수정 취소
     */
    cancelEdit: function () {
        if (confirm('수정 중인 내용이 있습니다. 취소하시겠습니까?')) {
            // 원래 데이터로 복원
            this.displayMemberData(this.currentMember);
            this.disableEditMode();
        }
    },

    /**
     * 활동내역 로드
     */
    loadActivityData: function () {
        if (!this.currentMember) return;

        const activityContainer = $('#activity-list');
        const activityLoading = $('#activity-loading');
        const activityContent = $('#activity-content');
        const activityEmpty = $('#activity-empty');

        // 로딩 표시
        if (activityLoading.length) activityLoading.show();
        if (activityContent.length) activityContent.hide();
        if (activityEmpty.length) activityEmpty.hide();

        $.ajax({
            url: `/dashboard/members/activity/${this.currentMember.id}`,
            method: 'GET',
            success: function (response) {
                if (response.success && response.activities && response.activities.length > 0) {
                    let activitiesHtml = '';
                    
                    response.activities.forEach(activity => {
                        activitiesHtml += `
                            <div class="border-bottom pb-3 mb-3">
                                <div class="d-flex align-items-start">
                                    <div class="mr-3">
                                        <i class="${activity.icon || 'fas fa-info-circle'} text-${activity.color || 'primary'}"></i>
                                    </div>
                                    <div class="flex-grow-1">
                                        <div class="d-flex justify-content-between align-items-start">
                                            <div>
                                                <h6 class="mb-1">${activity.title || '활동'}</h6>
                                                <p class="mb-1">${activity.description || ''}</p>
                                                ${activity.reason ? `<small class="text-muted">사유: ${activity.reason}</small>` : ''}
                                                ${activity.detail ? `<br><small class="text-muted">${activity.detail}</small>` : ''}
                                            </div>
                                            <div class="text-right">
                                                <small class="text-muted">${activity.user || 'system'}</small><br>
                                                <small class="text-muted">${activity.created_at || ''}</small>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        `;
                    });
                    
                    if (activityContainer.length) {
                        activityContainer.html(activitiesHtml);
                    }
                    if (activityContent.length) activityContent.show();
                } else {
                    if (activityEmpty.length) activityEmpty.show();
                }
            },
            error: function (xhr) {
                console.error('활동내역 로드 오류:', xhr);
                if (activityContainer.length) {
                    activityContainer.html(`
                        <div class="text-center text-danger py-3">
                            <i class="fas fa-exclamation-triangle"></i> 활동내역을 불러오는 중 오류가 발생했습니다.
                        </div>
                    `);
                }
                if (activityContent.length) activityContent.show();
            },
            complete: function () {
                if (activityLoading.length) activityLoading.hide();
            }
        });
    }
};

// DOM 로드 완료 시 초기화
$(document).ready(function () {
    MemberModal.init();
});

// 전역 접근을 위한 window 객체에 추가
window.MemberModal = MemberModal;