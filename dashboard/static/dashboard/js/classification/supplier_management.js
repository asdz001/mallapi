// dashboard/static/dashboard/js/classification/supplier_management.js
// 🏢 거래처 관리 전용 JavaScript (카테고리 방식 적용)

$(document).ready(function() {
    
    // ========================================
    // 🔹 전역 변수
    // ========================================
    
    let isEditMode = false;           // 수정 모드 여부
    let currentSupplierId = null;     // 현재 편집중인 거래처 ID
    
    // 🔐 CSRF 토큰 가져오기
    const csrfToken = $('[name=csrfmiddlewaretoken]').val();
    
    console.log('거래처 관리 기능 초기화 시작');
    
    // ========================================
    // 🔹 모달창 관리 기능
    // ========================================
    
    function resetSupplierModal() {
        $('#supplierForm')[0].reset();
        $('#supplier_id').val('');
        isEditMode = false;
        currentSupplierId = null;
        console.log('모달 초기화 완료');
    }
    
    function closeSupplierModal() {
        $('#supplierModal').modal('hide');
        resetSupplierModal();
    }
    
    function closeDetailModal() {
        $('#supplierDetailModal').modal('hide');
    }
    
    // ========================================
    // 🔹 거래처 관리 기능
    // ========================================
    
    /**
     * 거래처 등록 모달창 열기
     */
    $('[data-target="#supplierModal"]').click(function() {
        console.log('거래처 추가 버튼 클릭됨');
        resetSupplierModal();
        $('#supplierModalLabel').text('거래처 등록');
        $('#supplierModal').modal('show');
    });
    
    /**
     * 거래처 상세보기 버튼 클릭
     */
    $(document).on('click', '.btn-view-supplier', function() {
        const supplierId = $(this).data('supplier-id');
        
        // 거래처 정보 조회
        const detailUrl = '/dashboard/products/classification/supplier/' + supplierId + '/detail/';
        
        $.get(detailUrl)
            .done(function(response) {
                if (response.success) {
                    const data = response.data;
                    
                    $('#detail_supplier_name').text(data.name || '-');
                    $('#detail_supplier_code').html(`<span class="badge badge-primary" style="font-size: 14px; padding: 6px 12px;">${data.code || '-'}</span>`);
                    $('#detail_supplier_id').text(data.id || '-');
                    
                    // 🔧 단순하게 테이블에서 보이는 값 가져와서 표시
                    const $currentRow = $(`tr[data-supplier-id="${supplierId}"]`);
                    const productCountText = $currentRow.find('td').last().prev().prev().text().trim(); // 상품수 컬럼 (관리, 삭제 버튼 앞)
                    $('#detail_product_count').text(productCountText || '0개');
                    
                    $('#detail_supplier_address').text(data.address || '미입력');
                    $('#detail_supplier_phone').text(data.phone || '미입력');
                    $('#detail_supplier_business_number').text(data.business_number || '미입력');
                    $('#detail_supplier_email').text(data.email || '미입력');
                    
                    $('#supplierDetailModal').modal('show');
                    
                    // 🔧 상세보기에서 수정 버튼 클릭 시 백업 방식 적용
                    $('#editFromDetailBtn').off('click').on('click', function() {
                        // 🔧 모달 닫기 전에 미리 변수들을 백업
                        const backupSupplierId = supplierId;
                        const backupSupplierData = {
                            id: data.id,
                            name: data.name,
                            code: data.code,
                            address: data.address,
                            phone: data.phone,
                            business_number: data.business_number,
                            email: data.email
                        };
                        
                        $('#supplierDetailModal').modal('hide');
                        
                        // 🔧 모달이 완전히 닫힌 후 강제로 수정 모드 설정
                        setTimeout(function() {
                            console.log('🔧 백업된 데이터로 수정 모달 설정:', backupSupplierData);
                            
                            // 🔧 강제로 모든 값 설정
                            isEditMode = true;
                            currentSupplierId = backupSupplierId;
                            
                            // 폼 완전 초기화 후 재설정
                            $('#supplierForm')[0].reset();
                            $('#supplierModalLabel').text('거래처 수정');
                            $('#supplier_id').val(backupSupplierData.id);
                            $('#supplier_name').val(backupSupplierData.name);
                            $('#supplier_code').val(backupSupplierData.code);
                            $('#supplier_address').val(backupSupplierData.address);
                            $('#supplier_phone').val(backupSupplierData.phone);
                            $('#supplier_business_number').val(backupSupplierData.business_number);
                            $('#supplier_email').val(backupSupplierData.email);
                            
                            // 수정 모달 표시
                            $('#supplierModal').modal('show');
                            
                            console.log('🔧 최종 설정 완료:', {
                                isEditMode: isEditMode,
                                currentSupplierId: currentSupplierId,
                                supplierIdVal: $('#supplier_id').val()
                            });
                            
                        }, 500); // 더 긴 대기시간으로 안정성 확보
                    });
                    
                } else {
                    alert('거래처 정보를 불러오는데 실패했습니다: ' + response.message);
                }
            })
            .fail(function() {
                alert('서버 오류가 발생했습니다.');
            });
    });
    
    /**
     * 거래처 수정 버튼 클릭
     */
    $(document).on('click', '.btn-edit-supplier', function() {
        isEditMode = true;
        currentSupplierId = $(this).data('supplier-id');
        $('#supplierModalLabel').text('거래처 수정');
        
        const detailUrl = '/dashboard/products/classification/supplier/' + currentSupplierId + '/detail/';
        
        $.get(detailUrl)
            .done(function(response) {
                if (response.success) {
                    const data = response.data;
                    $('#supplier_id').val(data.id);
                    $('#supplier_name').val(data.name);
                    $('#supplier_code').val(data.code);
                    $('#supplier_address').val(data.address);
                    $('#supplier_phone').val(data.phone);
                    $('#supplier_business_number').val(data.business_number);
                    $('#supplier_email').val(data.email);
                    
                    $('#supplierModal').modal('show');
                } else {
                    alert('거래처 정보를 불러오는데 실패했습니다: ' + response.message);
                }
            })
            .fail(function(xhr, status, error) {
                console.error('AJAX 오류:', xhr.responseText);
                alert('서버 오류가 발생했습니다: ' + error);
            });
    });
    
    /**
     * 거래처 저장 버튼 클릭
     */
    $('#saveSupplierBtn').click(function() {
        const supplierName = $('#supplier_name').val().trim();
        const supplierCode = $('#supplier_code').val().trim();
        
        if (!supplierName) {
            alert('업체명을 입력해주세요.');
            $('#supplier_name').focus();
            return;
        }
        
        if (!supplierCode) {
            alert('업체코드를 입력해주세요.');
            $('#supplier_code').focus();
            return;
        }
        
        const formData = $('#supplierForm').serialize();
        
        // 🔍 디버깅: 저장 시 모든 상태 확인
        console.log('=== 저장 버튼 클릭 시 상태 ===');
        console.log('isEditMode:', isEditMode);
        console.log('currentSupplierId:', currentSupplierId);
        console.log('supplierName:', supplierName);
        console.log('supplier_id input value:', $('#supplier_id').val());
        console.log('formData:', formData);
        
        // 🔧 URL 생성 로직
        let url;
        if (isEditMode && currentSupplierId && $('#supplier_id').val()) {
            url = '/dashboard/products/classification/supplier/' + currentSupplierId + '/update/';
            console.log('🔄 수정 모드 URL:', url);
        } else {
            url = '/dashboard/products/classification/supplier/create/';
            console.log('🆕 등록 모드 URL:', url);
        }
        
        $('#saveSupplierBtn').prop('disabled', true).text('저장 중...');
        
        $.post(url, formData)
            .done(function(response) {
                console.log('서버 응답:', response);
                if (response.success) {
                    alert(response.message);
                    closeSupplierModal();
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
                $('#saveSupplierBtn').prop('disabled', false).text('저장');
            });
    });
    
    /**
     * 거래처 삭제 버튼 클릭
     */
    $(document).on('click', '.btn-delete-supplier', function() {
        const supplierId = $(this).data('supplier-id');
        const supplierName = $(this).data('supplier-name');
        
        if (confirm(`"${supplierName}" 거래처를 삭제하시겠습니까?\n\n⚠️ 연결된 상품이 있으면 삭제할 수 없습니다.`)) {
            const deleteUrl = '/dashboard/products/classification/supplier/' + supplierId + '/delete/';
            
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
    $('#cancelSupplierModalBtn, #closeSupplierModalXBtn').click(function() {
        // 🔧 강제 초기화 후 모달 닫기
        resetSupplierModal();
        $('#supplierModal').modal('hide');
    });
    
    // 상세보기 모달 닫기 버튼들  
    $('#closeDetailModalBtn, #closeDetailModalXBtn').click(function() {
        closeDetailModal();
    });
    
    // 🔧 모달 숨김 이벤트 (완전히 제거하여 초기화 방지)
    $('#supplierModal').on('hidden.bs.modal', function () {
        // 🔧 수정 모드일 때는 절대 초기화하지 않음
        if (!isEditMode) {
            console.log('등록 모달 숨김 - 초기화 실행');
            resetSupplierModal();
        } else {
            console.log('수정 모달 숨김 - 초기화 완전 건너뜀 (isEditMode: true)');
        }
    });
    
    $('#supplierDetailModal').on('hidden.bs.modal', function () {
        console.log('상세보기 모달 숨김');
        // currentSupplierId = null; // 🔧 이 줄 제거하여 값 보존
    });
    
    // ========================================
    // 🔹 키보드 이벤트 처리
    // ========================================
    
    $('#supplier_name').keypress(function(e) {
        if (e.which === 13) {
            e.preventDefault();
            $('#saveSupplierBtn').click();
        }
    });
    
    $('#supplier_code').keypress(function(e) {
        if (e.which === 13) {
            e.preventDefault();
            $('#saveSupplierBtn').click();
        }
    });
    
    // 🔧 검색 초기화 버튼
    $('#reset-search').click(function() {
        $('#search_field').val('name');
        $('#search_value').val('');
        window.location.href = '/dashboard/products/classification/supplier/';
    });
    
    // 툴팁 초기화
    $('[data-toggle="tooltip"]').tooltip();
    
    console.log('거래처 관리 기능 초기화 완료');
    
});