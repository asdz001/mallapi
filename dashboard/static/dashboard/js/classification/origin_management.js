/**
 * ========================================
 * 📁 파일 위치: dashboard/static/dashboard/js/classification/origin_management.js
 * 🎯 목적: 원산지 관리 JavaScript (통합된 별칭 관리)
 * 📅 버전: 2.0
 * ========================================
 */

$(document).ready(function() {
    
    // 🌍 전역 변수
    let isEditMode = false;
    let currentCountryId = null;
    let currentAliases = [];  // 현재 별칭 목록
    
    console.log('원산지 관리 JavaScript 로드 완료');
    
    // ========================================
    // 🔹 CSRF 토큰 설정
    // ========================================
    
    // Django CSRF 토큰 가져오기
    function getCSRFToken() {
        return $('[name=csrfmiddlewaretoken]').val();
    }
    
    // AJAX 요청에 CSRF 토큰 자동 추가
    $.ajaxSetup({
        beforeSend: function(xhr, settings) {
            if (!(/^http:.*/.test(settings.url) || /^https:.*/.test(settings.url))) {
                xhr.setRequestHeader("X-CSRFToken", getCSRFToken());
            }
        }
    });
    
    // ========================================
    // 🔹 별칭 관리 기능
    // ========================================
    
    /**
     * 별칭 추가 함수
     */
    function addAlias() {
        const aliasValue = $('#alias_input').val().trim();
        if (aliasValue && !currentAliases.includes(aliasValue)) {
            currentAliases.push(aliasValue);
            updateAliasDisplay();
            $('#alias_input').val('');
        }
    }

    /**
     * 별칭 목록 화면 업데이트
     */
    function updateAliasDisplay() {
        const aliasContainer = $('#alias_list');
        if (currentAliases.length === 0) {
            aliasContainer.html('<small class="text-muted">추가된 별칭이 여기에 표시됩니다.</small>');
        } else {
            let html = '';
            currentAliases.forEach(function(alias, index) {
                html += `<span class="badge badge-info badge-large mr-1 mb-1">
                    ${alias}
                    <span class="ml-1 alias-remove" onclick="removeAlias(${index})">×</span>
                </span>`;
            });
            aliasContainer.html(html);
        }
    }

    // 전역 함수로 정의 (HTML에서 onclick 사용)
    window.removeAlias = function(index) {
        currentAliases.splice(index, 1);
        updateAliasDisplay();
    };

    // 별칭 추가 버튼 이벤트
    $('#add_alias_btn').click(function() {
        addAlias();
    });

    // Enter 키로 별칭 추가
    $('#alias_input').keypress(function(e) {
        if (e.which === 13) {
            e.preventDefault();
            addAlias();
        }
    });
    
    // ========================================
    // 🔹 모달창 관리 함수들
    // ========================================
    
    function resetCountryModal() {
        $('#countryForm')[0].reset();
        $('#country_id').val('');
        isEditMode = false;
        currentCountryId = null;
        currentAliases = [];
        updateAliasDisplay();
    }
    
    function closeCountryModal() {
        $('#countryModal').modal('hide');
        resetCountryModal();
    }
    
    function closeDetailModal() {
        $('#countryDetailModal').modal('hide');
    }
    
    // ========================================
    // 🔹 표준국가 관리 기능
    // ========================================
    
    /**
     * 표준국가 등록 모달창 열기
     */
    $('[data-target="#countryModal"]').click(function() {
        console.log('표준국가 추가 버튼 클릭됨');
        resetCountryModal();
        $('#countryModalLabel').text('표준국가 등록');
        $('#countryModal').modal('show');
    });
    
    /**
     * 표준국가 상세보기 버튼 클릭
     */
    $(document).on('click', '.btn-view-country', function() {
        const countryId = $(this).data('country-id');
        
        // 국가 정보 조회 (URL을 문자열로 직접 구성)
        const detailUrl = '/dashboard/products/classification/origin/country/' + countryId + '/detail/';
        
        $.get(detailUrl)
            .done(function(response) {
                if (response.success) {
                    const data = response.data;
                    
                    $('#detail_country_name').text(data.name || '-');
                    $('#detail_country_id').text(data.id || '-');
                    
                    if (data.fta_applicable) {
                        $('#detail_fta_status').html('<span class="badge badge-success">적용</span>');
                    } else {
                        $('#detail_fta_status').html('<span class="badge badge-secondary">미적용</span>');
                    }
                    
                    $('#detail_alias_count').text(data.alias_count + '개');
                    
                    if (data.alias_list && data.alias_list.length > 0) {
                        let aliasHtml = '';
                        data.alias_list.forEach(function(alias) {
                            aliasHtml += `<span class="badge badge-info badge-large mr-1 mb-1">${alias}</span>`;
                        });
                        $('#detail_alias_list').html(aliasHtml);
                    } else {
                        $('#detail_alias_list').html('<small class="text-muted">연결된 별칭이 없습니다.</small>');
                    }
                    
                    currentCountryId = countryId;
                    $('#countryDetailModal').modal('show');
                } else {
                    alert('국가 정보를 불러오는데 실패했습니다: ' + response.message);
                }
            })
            .fail(function(xhr, status, error) {
                console.error('AJAX 오류:', xhr.responseText);
                alert('서버 오류가 발생했습니다: ' + error);
            });
    });
    
    /**
     * 상세보기에서 수정 버튼 클릭
     */
    $('#editFromDetailBtn').click(function() {
        if (currentCountryId) {
            closeDetailModal();
            
            isEditMode = true;
            $('#countryModalLabel').text('표준국가 수정');
            
            const detailUrl = '/dashboard/products/classification/origin/country/' + currentCountryId + '/detail/';
            
            $.get(detailUrl)
                .done(function(response) {
                    if (response.success) {
                        const data = response.data;
                        $('#country_id').val(data.id);
                        $('#country_name').val(data.name);
                        $('#fta_applicable').prop('checked', data.fta_applicable);
                        
                        // 기존 별칭 로드
                        currentAliases = data.alias_list || [];
                        updateAliasDisplay();
                        
                        $('#countryModal').modal('show');
                    } else {
                        alert('국가 정보를 불러오는데 실패했습니다: ' + response.message);
                    }
                })
                .fail(function(xhr, status, error) {
                    console.error('AJAX 오류:', xhr.responseText);
                    alert('서버 오류가 발생했습니다: ' + error);
                });
        }
    });
    
    /**
     * 표준국가 수정 버튼 클릭
     */
    $(document).on('click', '.btn-edit-country', function() {
        isEditMode = true;
        currentCountryId = $(this).data('country-id');
        $('#countryModalLabel').text('표준국가 수정');
        
        const detailUrl = '/dashboard/products/classification/origin/country/' + currentCountryId + '/detail/';
        
        $.get(detailUrl)
            .done(function(response) {
                if (response.success) {
                    const data = response.data;
                    $('#country_id').val(data.id);
                    $('#country_name').val(data.name);
                    $('#fta_applicable').prop('checked', data.fta_applicable);
                    
                    // 기존 별칭 로드
                    currentAliases = data.alias_list || [];
                    updateAliasDisplay();
                    
                    $('#countryModal').modal('show');
                } else {
                    alert('국가 정보를 불러오는데 실패했습니다: ' + response.message);
                }
            })
            .fail(function(xhr, status, error) {
                console.error('AJAX 오류:', xhr.responseText);
                alert('서버 오류가 발생했습니다: ' + error);
            });
    });
    
    /**
     * 표준국가 저장 버튼 클릭
     */
    $('#saveCountryBtn').click(function() {
        const countryName = $('#country_name').val().trim();
        if (!countryName) {
            alert('국가명을 입력해주세요.');
            $('#country_name').focus();
            return;
        }
        
        let formData = $('#countryForm').serialize();
        
        // 별칭 데이터 추가
        currentAliases.forEach(function(alias) {
            formData += '&aliases[]=' + encodeURIComponent(alias);
        });
        
        const url = isEditMode ? 
            '/dashboard/products/classification/origin/country/' + currentCountryId + '/update/' :
            '/dashboard/products/classification/origin/country/create/';
        
        $('#saveCountryBtn').prop('disabled', true).text('저장 중...');
        
        $.post(url, formData)
            .done(function(response) {
                if (response.success) {
                    alert(response.message);
                    closeCountryModal();
                    location.reload();
                } else {
                    alert('오류: ' + response.message);
                }
            })
            .fail(function(xhr, status, error) {
                console.error('AJAX 오류:', xhr.responseText);
                alert('서버 오류가 발생했습니다: ' + error);
            })
            .always(function() {
                $('#saveCountryBtn').prop('disabled', false).text('저장');
            });
    });
    
    /**
     * 표준국가 삭제 버튼 클릭
     */
    $(document).on('click', '.btn-delete-country', function() {
        const countryId = $(this).data('country-id');
        const countryName = $(this).data('country-name');
        
        if (confirm(`"${countryName}" 국가를 삭제하시겠습니까?\n\n⚠️ 연결된 별칭이 있으면 삭제할 수 없습니다.`)) {
            const deleteUrl = '/dashboard/products/classification/origin/country/' + countryId + '/delete/';
            
            $.post(deleteUrl)
                .done(function(response) {
                    if (response.success) {
                        alert(response.message);
                        location.reload();
                    } else {
                        alert('오류: ' + response.message);
                    }
                })
                .fail(function(xhr, status, error) {
                    console.error('AJAX 오류:', xhr.responseText);
                    alert('서버 오류가 발생했습니다: ' + error);
                });
        }
    });
    
    /**
     * 별칭 삭제 버튼 클릭 (별칭 테이블에서) - 제거됨
     */
    // 별칭 테이블이 제거되었으므로 해당 기능도 제거
    
    // ========================================
    // 🔹 모달창 이벤트 처리
    // ========================================
    
    $('#cancelModalBtn, #closeModalBtn').click(function() {
        closeCountryModal();
    });
    
    $('#closeDetailModalBtn, #closeDetailModalXBtn').click(function() {
        closeDetailModal();
    });
    
    $('#countryModal').on('hidden.bs.modal', function () {
        resetCountryModal();
    });
    
    $('#countryDetailModal').on('hidden.bs.modal', function () {
        currentCountryId = null;
    });
    
    // ========================================
    // 🔹 키보드 이벤트 처리
    // ========================================
    
    $('#country_name').keypress(function(e) {
        if (e.which === 13) {
            e.preventDefault();
            $('#saveCountryBtn').click();
        }
    });
    
    // 툴팁 초기화
    $('[data-toggle="tooltip"]').tooltip();
    
    console.log('원산지 관리 기능 초기화 완료');
    
});