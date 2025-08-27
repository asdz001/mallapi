// dashboard/static/dashboard/js/classification/category_management.js
// 🏷️ 카테고리 관리 전용 JavaScript (원산지 스타일 적용)

$(document).ready(function() {
    
    // ========================================
    // 🔹 전역 변수
    // ========================================
    
    let isEditMode = false;           // 수정 모드 여부
    let currentCategoryId = null;     // 현재 편집중인 카테고리 ID
    let currentAliases = [];          // 현재 등록된 별칭 목록
    
    // 🔐 CSRF 토큰 가져오기
    const csrfToken = $('[name=csrfmiddlewaretoken]').val();
    
    console.log('카테고리 관리 기능 초기화 시작');
    
    // ========================================
    // 🔹 별칭 관리 기능
    // ========================================
    
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
    
    function resetCategoryModal() {
        $('#categoryForm')[0].reset();
        $('#category_id').val('');
        isEditMode = false;
        currentCategoryId = null;
        currentAliases = [];
        updateAliasDisplay();
        console.log('모달 초기화 완료'); // 🔍 디버깅용
    }
    
    function closeCategoryModal() {
        $('#categoryModal').modal('hide');
        resetCategoryModal();
    }
    
    function closeDetailModal() {
        $('#categoryDetailModal').modal('hide');
    }
    
    // ========================================
    // 🔹 카테고리 관리 기능
    // ========================================
    
    /**
     * 카테고리 등록 모달창 열기
     */
    $('[data-target="#categoryModal"]').click(function() {
        console.log('카테고리 추가 버튼 클릭됨');
        resetCategoryModal();
        const currentLevel = $('#current_level').val() || 'level1';
        const levelNames = {
            'level1': '성별',
            'level2': '대분류', 
            'level3': '중분류',
            'level4': '소분류'
        };
        $('#categoryModalLabel').text(levelNames[currentLevel] + ' 등록');
        $('#categoryModal').modal('show');
    });
    
    /**
     * 카테고리 상세보기 버튼 클릭
     */
    $(document).on('click', '.btn-view-category', function() {
        const categoryId = $(this).data('category-id');
        const currentLevel = $('#current_level').val() || 'level1';
        
        // 카테고리 정보 조회
        const detailUrl = '/dashboard/products/classification/category/' + currentLevel + '/' + categoryId + '/detail/';
        
        $.get(detailUrl)
            .done(function(response) {
                if (response.success) {
                    const data = response.data;
                    
                    $('#detail_category_name').text(data.name || '-');
                    $('#detail_category_id').text(data.id || '-');
                    
                    // 🔧 단순하게 테이블에서 보이는 값 가져와서 표시
                    const $currentRow = $(`tr[data-category-id="${categoryId}"]`);
                    const aliasCountText = $currentRow.find('td').eq(2).text().trim(); // alias_count 컬럼
                    const productCountText = $currentRow.find('td').eq(3).text().trim(); // product_count 컬럼
                    
                    $('#detail_alias_count').text(aliasCountText || '0개');
                    $('#detail_product_count').text(productCountText || '0개');
                    
                    // 별칭 목록 표시 (수정: aliases 배열 처리 + 글자크기 증가)
                    if (data.aliases && Array.isArray(data.aliases) && data.aliases.length > 0) {
                        let aliasHtml = '';
                        data.aliases.forEach(function(aliasObj) {
                            if (aliasObj.alias) {
                                aliasHtml += `<span class="badge badge-info mr-2 mb-1" style="font-size: 16px; padding: 8px 12px;">${aliasObj.alias}</span>`;
                            }
                        });
                        $('#detail_alias_list').html(aliasHtml);
                    } else if (data.alias_list && Array.isArray(data.alias_list) && data.alias_list.length > 0) {
                        let aliasHtml = '';
                        data.alias_list.forEach(function(alias) {
                            aliasHtml += `<span class="badge badge-info mr-2 mb-1" style="font-size: 16px; padding: 8px 12px;">${alias}</span>`;
                        });
                        $('#detail_alias_list').html(aliasHtml);
                    } else {
                        $('#detail_alias_list').html('<small class="text-muted" style="font-size: 14px;">등록된 별칭이 없습니다.</small>');
                    }
                    
                    $('#categoryDetailModal').modal('show');
                    
                    // 🔧 상세보기에서 수정 버튼 클릭 시 완전히 새로운 접근 방식
                    $('#editFromDetailBtn').off('click').on('click', function() {
                        // 🔧 모달 닫기 전에 미리 변수들을 백업
                        const backupCategoryId = categoryId;
                        const backupCategoryName = data.name;
                        const backupCurrentLevel = currentLevel;
                        const backupAliases = [];
                        
                        // 별칭 데이터 백업
                        if (data.aliases && Array.isArray(data.aliases)) {
                            data.aliases.forEach(function(aliasObj) {
                                if (aliasObj.alias) {
                                    backupAliases.push(aliasObj.alias);
                                }
                            });
                        } else if (data.alias_list && Array.isArray(data.alias_list)) {
                            backupAliases.push(...data.alias_list);
                        }
                        
                        $('#categoryDetailModal').modal('hide');
                        
                        // 🔧 모달이 완전히 닫힌 후 강제로 수정 모드 설정
                        setTimeout(function() {
                            console.log('🔧 백업된 데이터로 수정 모달 설정:', {
                                backupCategoryId: backupCategoryId,
                                backupCategoryName: backupCategoryName,
                                backupCurrentLevel: backupCurrentLevel,
                                backupAliases: backupAliases
                            });
                            
                            // 🔧 강제로 모든 값 설정
                            isEditMode = true;
                            currentCategoryId = backupCategoryId;
                            currentAliases = [...backupAliases]; // 배열 복사
                            
                            const levelNames = {
                                'level1': '성별',
                                'level2': '대분류', 
                                'level3': '중분류',
                                'level4': '소분류'
                            };
                            
                            // 폼 완전 초기화 후 재설정
                            $('#categoryForm')[0].reset();
                            $('#categoryModalLabel').text(levelNames[backupCurrentLevel] + ' 수정');
                            $('#category_id').val(backupCategoryId);
                            $('#category_name').val(backupCategoryName);
                            $('#current_level').val(backupCurrentLevel);
                            
                            // 별칭 표시 업데이트
                            updateAliasDisplay();
                            
                            // 수정 모달 표시
                            $('#categoryModal').modal('show');
                            
                            console.log('🔧 최종 설정 완료:', {
                                isEditMode: isEditMode,
                                currentCategoryId: currentCategoryId,
                                categoryIdVal: $('#category_id').val(),
                                currentAliases: currentAliases
                            });
                            
                        }, 500); // 더 긴 대기시간으로 안정성 확보
                    });
                    
                } else {
                    alert('카테고리 정보를 불러오는데 실패했습니다: ' + response.message);
                }
            })
            .fail(function() {
                alert('서버 오류가 발생했습니다.');
            });
    });
    
    /**
     * 카테고리 수정 버튼 클릭
     */
    $(document).on('click', '.btn-edit-category', function() {
        isEditMode = true;
        currentCategoryId = $(this).data('category-id');
        const currentLevel = $('#current_level').val() || 'level1';
        const levelNames = {
            'level1': '성별',
            'level2': '대분류', 
            'level3': '중분류',
            'level4': '소분류'
        };
        $('#categoryModalLabel').text(levelNames[currentLevel] + ' 수정');
        
        const detailUrl = '/dashboard/products/classification/category/' + currentLevel + '/' + currentCategoryId + '/detail/';
        
        $.get(detailUrl)
            .done(function(response) {
                if (response.success) {
                    const data = response.data;
                    $('#category_id').val(data.id);
                    $('#category_name').val(data.name);
                    
                    // 기존 별칭 로드 (수정: aliases 배열 처리)
                    currentAliases = [];
                    if (data.aliases && Array.isArray(data.aliases)) {
                        data.aliases.forEach(function(aliasObj) {
                            if (aliasObj.alias) {
                                currentAliases.push(aliasObj.alias);
                            }
                        });
                    } else if (data.alias_list && Array.isArray(data.alias_list)) {
                        currentAliases = data.alias_list.slice(); // 복사
                    }
                    updateAliasDisplay();
                    
                    $('#categoryModal').modal('show');
                } else {
                    alert('카테고리 정보를 불러오는데 실패했습니다: ' + response.message);
                }
            })
            .fail(function(xhr, status, error) {
                console.error('AJAX 오류:', xhr.responseText);
                alert('서버 오류가 발생했습니다: ' + error);
            });
    });
    
    /**
     * 카테고리 저장 버튼 클릭
     */
    $('#saveCategoryBtn').click(function() {
        const categoryName = $('#category_name').val().trim();
        if (!categoryName) {
            alert('카테고리명을 입력해주세요.');
            $('#category_name').focus();
            return;
        }
        
        let formData = $('#categoryForm').serialize();
        
        // 별칭 데이터 추가
        currentAliases.forEach(function(alias) {
            formData += '&aliases[]=' + encodeURIComponent(alias);
        });
        
        const currentLevel = $('#current_level').val() || 'level1';
        
        // 🔍 디버깅: 저장 시 모든 상태 확인
        console.log('=== 저장 버튼 클릭 시 상태 ===');
        console.log('isEditMode:', isEditMode);
        console.log('currentCategoryId:', currentCategoryId);
        console.log('currentLevel:', currentLevel);
        console.log('categoryName:', categoryName);
        console.log('category_id input value:', $('#category_id').val());
        console.log('formData:', formData);
        console.log('currentAliases:', currentAliases);
        
        // 🔧 URL 생성 로직 수정
        let url;
        if (isEditMode && currentCategoryId && $('#category_id').val()) {
            url = '/dashboard/products/classification/category/' + currentLevel + '/' + currentCategoryId + '/update/';
            console.log('🔄 수정 모드 URL:', url);
        } else {
            url = '/dashboard/products/classification/category/create/';
            console.log('🆕 등록 모드 URL:', url);
        }
        
        $('#saveCategoryBtn').prop('disabled', true).text('저장 중...');
        
        $.post(url, formData)
            .done(function(response) {
                console.log('서버 응답:', response);
                if (response.success) {
                    alert(response.message);
                    closeCategoryModal();
                    location.reload();
                } else {
                    alert('오류: ' + response.message);
                }
            })
            .fail(function(xhr, status, error) {
                console.error('AJAX 오류 상세:', {
                    status: xhr.status,
                    statusText: xhr.statusText,
                    responseText: xhr.responseText,
                    error: error
                });
                alert('서버 오류가 발생했습니다: ' + error);
            })
            .always(function() {
                $('#saveCategoryBtn').prop('disabled', false).text('저장');
            });
    });
    
    /**
     * 카테고리 삭제 버튼 클릭
     */
    $(document).on('click', '.btn-delete-category', function() {
        const categoryId = $(this).data('category-id');
        const categoryName = $(this).data('category-name');
        const currentLevel = $('#current_level').val() || 'level1';
        
        if (confirm(`"${categoryName}" 카테고리를 삭제하시겠습니까?\n\n⚠️ 연결된 별칭이나 상품이 있으면 삭제할 수 없습니다.`)) {
            const deleteUrl = '/dashboard/products/classification/category/' + currentLevel + '/' + categoryId + '/delete/';
            
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
    $('#cancelCategoryModalBtn, #closeCategoryModalXBtn').click(function() {
        // 🔧 강제 초기화 후 모달 닫기
        resetCategoryModal();
        $('#categoryModal').modal('hide');
    });
    
    // 상세보기 모달 닫기 버튼들  
    $('#closeDetailModalBtn, #closeDetailModalXBtn').click(function() {
        closeDetailModal();
    });
    
    // 🔧 모달 숨김 이벤트 (완전히 제거하여 초기화 방지)
    $('#categoryModal').on('hidden.bs.modal', function () {
        // 🔧 수정 모드일 때는 절대 초기화하지 않음
        if (!isEditMode) {
            console.log('등록 모달 숨김 - 초기화 실행');
            resetCategoryModal();
        } else {
            console.log('수정 모달 숨김 - 초기화 완전 건너뜀 (isEditMode: true)');
        }
    });
    
    $('#categoryDetailModal').on('hidden.bs.modal', function () {
        console.log('상세보기 모달 숨김');
        // currentCategoryId = null; // 🔧 이 줄 제거하여 값 보존
    });
    
    // ========================================
    // 🔹 키보드 이벤트 처리
    // ========================================
    
    $('#category_name').keypress(function(e) {
        if (e.which === 13) {
            e.preventDefault();
            $('#saveCategoryBtn').click();
        }
    });
    
    // 🔧 검색 초기화 버튼
    $('#reset-search').click(function() {
        $('#search_field').val('name');
        $('#search_value').val('');
        const currentLevel = $('#current_level').val() || 'level1';
        window.location.href = '/dashboard/products/classification/category/?level=' + currentLevel;
    });
    
    // 툴팁 초기화
    $('[data-toggle="tooltip"]').tooltip();
    
    console.log('카테고리 관리 기능 초기화 완료');
    
});