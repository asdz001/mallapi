// dashboard/static/dashboard/js/brand_management.js
// 🏷️ 브랜드 관리 전용 JavaScript

$(document).ready(function() {
    
    // ========================================
    // 🔹 전역 변수
    // ========================================
    
    let isEditMode = false;           // 수정 모드 여부
    let currentBrandId = null;        // 현재 편집중인 브랜드 ID
    let currentAliases = [];          // 현재 등록된 별칭 목록
    
    // 🔐 CSRF 토큰 가져오기
    const csrfToken = $('[name=csrfmiddlewaretoken]').val();
    
    console.log('브랜드 관리 기능 초기화 시작');
    
    // ========================================
    // 🔹 별칭 관리 기능
    // ========================================
    
    /**
     * 🎛️ 브랜드 활성화/비활성화 토글 버튼 클릭 (🆕 추가)
     */
    $(document).on('click', '.btn-toggle-brand', function() {
        const brandId = $(this).data('brand-id');
        const currentStatus = $(this).data('current-status');
        const actionText = currentStatus === 'active' ? '비활성화' : '활성화';
        
        if (confirm(`이 브랜드를 ${actionText}하시겠습니까?\n\n${actionText === '비활성화' ? '⚠️ 서비스 화면에서 노출되지 않습니다.' : '✅ 서비스 화면에서 노출됩니다.'}`)) {
            const toggleUrl = '/dashboard/products/classification/brand/' + brandId + '/toggle/';
            
            // 🔐 CSRF 토큰과 함께 POST 요청
            $.post(toggleUrl, {
                'csrfmiddlewaretoken': csrfToken
            })
                .done(function(response) {
                    if (response.success) {
                        alert(response.message);
                        location.reload(); // 상태 변경 후 새로고침
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
     * 별칭 추가 버튼 클릭
     */
    $('#addAliasBtn').click(function() {
        const newAlias = $('#new_alias').val().trim();
        
        if (!newAlias) {
            alert('별칭을 입력해주세요.');
            $('#new_alias').focus();
            return;
        }
        
        // 중복 검사
        if (currentAliases.includes(newAlias)) {
            alert('이미 추가된 별칭입니다.');
            $('#new_alias').focus();
            return;
        }
        
        // 별칭 추가
        currentAliases.push(newAlias);
        $('#new_alias').val('');  // 입력창 클리어
        updateAliasDisplay();     // 화면 업데이트
        
        console.log('별칭 추가됨:', newAlias);
    });
    
    /**
     * 별칭 입력창에서 엔터키 처리
     */
    $('#new_alias').keypress(function(e) {
        if (e.which === 13) {  // 엔터키
            e.preventDefault();
            $('#addAliasBtn').click();
        }
    });
    
    /**
     * 별칭 화면 업데이트
     */
    function updateAliasDisplay() {
        const container = $('#aliasDisplay');
        
        if (currentAliases.length === 0) {
            container.html('<small class="text-muted">별칭이 등록되면 여기에 표시됩니다.</small>');
            return;
        }
        
        let html = '';
        currentAliases.forEach(function(alias, index) {
            html += `
                <span class="badge badge-secondary mr-2 mb-2" style="font-size: 14px;">
                    ${alias}
                    <button type="button" class="btn btn-sm p-0 ml-1 text-white remove-alias-btn" 
                            data-index="${index}" style="background: none; border: none;">
                        <i class="fas fa-times"></i>
                    </button>
                </span>
            `;
        });
        
        container.html(html);
    }
    
    /**
     * 별칭 제거 버튼 클릭 (동적 이벤트)
     */
    $(document).on('click', '.remove-alias-btn', function() {
        const index = $(this).data('index');
        const removedAlias = currentAliases[index];
        
        currentAliases.splice(index, 1);  // 배열에서 제거
        updateAliasDisplay();              // 화면 업데이트
        
        console.log('별칭 제거됨:', removedAlias);
    });
    
    // ========================================
    // 🔹 모달창 관리 기능
    // ========================================
    
    function resetBrandModal() {
        $('#brandForm')[0].reset();
        $('#brand_id').val('');
        isEditMode = false;
        currentBrandId = null;
        currentAliases = [];
        updateAliasDisplay();
    }
    
    function closeBrandModal() {
        $('#brandModal').modal('hide');
        resetBrandModal();
    }
    
    function closeDetailModal() {
        $('#brandDetailModal').modal('hide');
    }
    
    // ========================================
    // 🔹 표준 브랜드 관리 기능
    // ========================================
    
    /**
     * 표준 브랜드 등록 모달창 열기
     */
    $('[data-target="#brandModal"]').click(function() {
        console.log('표준 브랜드 추가 버튼 클릭됨');
        resetBrandModal();
        $('#brandModalLabel').text('표준 브랜드 등록');
        $('#brandModal').modal('show');
    });
    
    /**
     * 표준 브랜드 상세보기 버튼 클릭
     */
    $(document).on('click', '.btn-view-brand', function() {
        const brandId = $(this).data('brand-id');
        
        // 브랜드 정보 조회
        const detailUrl = '/dashboard/products/classification/brand/' + brandId + '/detail/';
        
        $.get(detailUrl)
            .done(function(response) {
                if (response.success) {
                    const data = response.data;
                    
                    $('#detail_brand_name').text(data.name || '-');
                    $('#detail_brand_id').text(data.id || '-');
                    $('#detail_alias_count').text(data.alias_count + '개');
                    $('#detail_product_count').text(data.product_count + '개');
                    
                    // 🆕 활성화 상태 표시
                    if (data.is_active) {
                        $('#detail_brand_status').html('<span class="badge badge-success">활성화</span>');
                    } else {
                        $('#detail_brand_status').html('<span class="badge badge-secondary">비활성화</span>');
                    }
                    
                    // 별칭 목록 표시
                    if (data.alias_list && data.alias_list.length > 0) {
                        let aliasHtml = '';
                        data.alias_list.forEach(function(alias) {
                            aliasHtml += `<span class="badge badge-info mr-2 mb-1">${alias}</span>`;
                        });
                        $('#detail_alias_list').html(aliasHtml);
                    } else {
                        $('#detail_alias_list').html('<small class="text-muted">등록된 별칭이 없습니다.</small>');
                    }
                    
                    $('#brandDetailModal').modal('show');
                    
                    // 상세보기에서 수정 버튼 클릭 시 수정 모달로 전환
                    $('#editFromDetailBtn').off('click').on('click', function() {
                        $('#brandDetailModal').modal('hide');
                        
                        // 수정 모달 데이터 설정
                        isEditMode = true;
                        currentBrandId = brandId;
                        $('#brandModalLabel').text('표준 브랜드 수정');
                        $('#brand_id').val(data.id);
                        $('#brand_name').val(data.name);
                        
                        // 기존 별칭 로드
                        currentAliases = data.alias_list || [];
                        updateAliasDisplay();
                        
                        $('#brandModal').modal('show');
                    });
                    
                } else {
                    alert('브랜드 정보를 불러오는데 실패했습니다: ' + response.message);
                }
            })
            .fail(function() {
                alert('서버 오류가 발생했습니다.');
            });
    });
    
    /**
     * 표준 브랜드 수정 버튼 클릭
     */
    $(document).on('click', '.btn-edit-brand', function() {
        isEditMode = true;
        currentBrandId = $(this).data('brand-id');
        $('#brandModalLabel').text('표준 브랜드 수정');
        
        const detailUrl = '/dashboard/products/classification/brand/' + currentBrandId + '/detail/';
        
        $.get(detailUrl)
            .done(function(response) {
                if (response.success) {
                    const data = response.data;
                    $('#brand_id').val(data.id);
                    $('#brand_name').val(data.name);
                    
                    // 기존 별칭 로드
                    currentAliases = data.alias_list || [];
                    updateAliasDisplay();
                    
                    $('#brandModal').modal('show');
                } else {
                    alert('브랜드 정보를 불러오는데 실패했습니다: ' + response.message);
                }
            })
            .fail(function(xhr, status, error) {
                console.error('AJAX 오류:', xhr.responseText);
                alert('서버 오류가 발생했습니다: ' + error);
            });
    });
    
    /**
     * 표준 브랜드 저장 버튼 클릭
     */
    $('#saveBrandBtn').click(function() {
        const brandName = $('#brand_name').val().trim();
        if (!brandName) {
            alert('브랜드명을 입력해주세요.');
            $('#brand_name').focus();
            return;
        }
        
        let formData = $('#brandForm').serialize();
        
        // 별칭 데이터 추가
        currentAliases.forEach(function(alias) {
            formData += '&aliases[]=' + encodeURIComponent(alias);
        });
        
        const url = isEditMode ?
            '/dashboard/products/classification/brand/' + currentBrandId + '/update/' :
            '/dashboard/products/classification/brand/create/';
        
        $('#saveBrandBtn').prop('disabled', true).text('저장 중...');
        
        $.post(url, formData)
            .done(function(response) {
                if (response.success) {
                    alert(response.message);
                    closeBrandModal();
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
                $('#saveBrandBtn').prop('disabled', false).text('저장');
            });
    });
    
    /**
     * 표준 브랜드 삭제 버튼 클릭
     */
    $(document).on('click', '.btn-delete-brand', function() {
        const brandId = $(this).data('brand-id');
        const brandName = $(this).data('brand-name');
        
        if (confirm(`"${brandName}" 브랜드를 삭제하시겠습니까?\n\n⚠️ 연결된 상품이나 별칭이 있으면 삭제할 수 없습니다.`)) {
            const deleteUrl = '/dashboard/products/classification/brand/' + brandId + '/delete/';
            
            // 🔐 CSRF 토큰과 함께 POST 요청
            $.post(deleteUrl, {
                'csrfmiddlewaretoken': csrfToken
            })
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
     * 별칭 삭제 버튼 클릭 (별칭 테이블에서)
     */
    $(document).on('click', '.btn-delete-alias', function() {
        const aliasId = $(this).data('alias-id');
        const aliasName = $(this).data('alias-name');
        
        if (confirm(`별칭 "${aliasName}"을(를) 삭제하시겠습니까?`)) {
            const deleteUrl = '/dashboard/products/classification/brand/alias/' + aliasId + '/delete/';
            
            // 🔐 CSRF 토큰과 함께 POST 요청
            $.post(deleteUrl, {
                'csrfmiddlewaretoken': csrfToken
            })
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
    
    // ========================================
    // 🔹 모달창 이벤트 처리
    // ========================================
    
    // 등록/수정 모달 닫기 버튼들
    $('#cancelBrandModalBtn, #closeBrandModalXBtn').click(function() {
        closeBrandModal();
    });
    
    // 상세보기 모달 닫기 버튼들  
    $('#closeDetailModalBtn, #closeDetailModalXBtn').click(function() {
        closeDetailModal();
    });
    
    // 모달 숨김 이벤트
    $('#brandModal').on('hidden.bs.modal', function () {
        resetBrandModal();
    });
    
    $('#brandDetailModal').on('hidden.bs.modal', function () {
        currentBrandId = null;
    });
    
    // ========================================
    // 🔹 키보드 이벤트 처리
    // ========================================
    
    $('#brand_name').keypress(function(e) {
        if (e.which === 13) {
            e.preventDefault();
            $('#saveBrandBtn').click();
        }
    });
    
    // 🔧 검색 초기화 버튼
    $('#reset-search').click(function() {
        $('#search_field').val('name');
        $('#search_value').val('');
        window.location.href = '/dashboard/products/classification/brand/';
    });
    
    // 툴팁 초기화
    $('[data-toggle="tooltip"]').tooltip();
    
    console.log('브랜드 관리 기능 초기화 완료');
    
});