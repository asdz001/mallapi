/**
 * ========================================
 * 📁 파일 위치: dashboard/static/dashboard/js/product_list_management.js
 * 🎯 목적: 상품목록 관리 JavaScript (원산지 관리 방식 참조)
 * 📅 버전: 1.0
 * ========================================
 */

$(document).ready(function() {
    
    // 🎯 전역 변수
    let columnSettings = {};
    let defaultColumns = [];
    
    console.log('상품목록 관리 JavaScript 로드 완료');
    
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
    // 🔹 상품 관리 기능
    // ========================================
    
    /**
     * 상품 수정 함수 (상품명 클릭 시)
     */
    window.editProduct = function(productId) {
        console.log('상품 수정:', productId);
        // TODO: 상품 수정 모달창 구현
        alert('상품 수정 기능은 추후 구현 예정입니다. ID: ' + productId);
    };
    
    // ========================================
    // 🔹 컬럼 설정 관리 기능
    // ========================================
    
    /**
     * 컬럼설정 버튼 클릭 이벤트
     */
    $('#column-settings-btn').click(function() {
        console.log('컬럼설정 버튼 클릭됨');
        loadColumnSettings();
        $('#columnSettingsModal').modal('show');
    });
    
    /**
     * 컬럼 설정 로드
     */
    function loadColumnSettings() {
        console.log('컬럼 설정 로드 시작...');
        
        $.get('/dashboard/products/column-settings/get/')
            .done(function(response) {
                console.log('컬럼 설정 응답:', response);
                if (response.success) {
                    columnSettings = response.column_settings;
                    buildColumnList(columnSettings);
                    initSortable();
                } else {
                    alert('설정을 불러올 수 없습니다: ' + response.message);
                }
            })
            .fail(function(xhr, status, error) {
                console.error('컬럼 설정 로드 오류:', xhr.responseText);
                alert('서버 오류가 발생했습니다: ' + error);
            });
    }
    
    /**
     * 컬럼 목록 생성 (HTML에서 전달받은 데이터 사용)
     */
    function buildColumnList(columnSettings) {
        console.log('컬럼 목록 생성 중...', columnSettings);
        
        var columnList = $('#column-list');
        columnList.empty();
        
        // 기본 컬럼 정보는 window 객체에서 가져오기 (HTML에서 설정)
        if (typeof window.productColumns === 'undefined') {
            console.error('window.productColumns가 정의되지 않음');
            alert('컬럼 정보를 불러올 수 없습니다.');
            return;
        }
        
        defaultColumns = window.productColumns;
        
        // 설정에 따라 정렬된 컬럼 목록 생성
        var sortedColumns = [];
        for (var i = 0; i < defaultColumns.length; i++) {
            var col = defaultColumns[i];
            var setting = columnSettings[col.field] || {visible: true, order: i + 1};
            sortedColumns.push({
                field: col.field,
                header: col.header,
                visible: setting.visible,
                order: setting.order
            });
        }
        
        // order 순서대로 정렬
        sortedColumns.sort(function(a, b) { return a.order - b.order; });
        
        // HTML 생성
        for (var j = 0; j < sortedColumns.length; j++) {
            var col = sortedColumns[j];
            var checkedAttr = col.visible ? 'checked' : '';
            var html = '<div class="column-item" data-field="' + col.field + '">' +
                '<div class="d-flex align-items-center">' +
                '<i class="fas fa-grip-vertical drag-handle"></i>' +
                '<div class="form-check flex-grow-1">' +
                '<input class="form-check-input" type="checkbox" id="col_' + col.field + '" ' + checkedAttr + '>' +
                '<label class="form-check-label" for="col_' + col.field + '">' + col.header + '</label>' +
                '</div></div></div>';
            columnList.append(html);
        }
        
        console.log('컬럼 목록 생성 완료');
    }
    
    /**
     * 드래그 정렬 초기화 (jQuery UI 필요)
     */
    function initSortable() {
        if ($.fn.sortable) {
            $('#column-list').sortable({
                handle: '.drag-handle',
                placeholder: 'ui-sortable-placeholder',
                tolerance: 'pointer'
            });
            console.log('드래그 정렬 초기화 완료');
        } else {
            console.warn('jQuery UI Sortable이 로드되지 않음');
        }
    }
    
    /**
     * 컬럼 설정 저장
     */
    $('#save-column-settings').click(function() {
        console.log('컬럼 설정 저장 시작...');
        
        var newColumnSettings = {};
        var order = 1;
        
        $('#column-list .column-item').each(function() {
            var field = $(this).data('field');
            var visible = $(this).find('input[type="checkbox"]').is(':checked');
            
            newColumnSettings[field] = {
                visible: visible,
                order: order++
            };
        });
        
        console.log('저장할 설정:', newColumnSettings);
        
        // 서버로 전송
        $.post('/dashboard/products/column-settings/save/', {
            column_settings: JSON.stringify(newColumnSettings),
            csrfmiddlewaretoken: getCSRFToken()
        })
        .done(function(response) {
            console.log('저장 응답:', response);
            if (response.success) {
                alert('컬럼 설정이 저장되었습니다.');
                $('#columnSettingsModal').modal('hide');
                location.reload(); // 페이지 새로고침
            } else {
                alert('저장 실패: ' + response.message);
            }
        })
        .fail(function(xhr, status, error) {
            console.error('저장 오류:', xhr.responseText);
            alert('서버 오류가 발생했습니다: ' + error);
        });
    });
    
    // ========================================
    // 🔹 모달창 이벤트 처리
    // ========================================
    
    /**
     * 모달창 닫기 이벤트
     */
    $('#columnSettingsModal').on('hidden.bs.modal', function () {
        console.log('컬럼설정 모달창 닫힘');
        columnSettings = {};
    });
    
    // ========================================
    // 🔹 키보드 이벤트 처리
    // ========================================
    
    /**
     * 검색어 Enter 키 처리 (search_engine.js와 연동)
     */
    $('#search_value').keypress(function(e) {
        if (e.which === 13) { // Enter 키
            e.preventDefault();
            $('#search-form').submit();
        }
    });
    
    // ========================================
    // 🔹 기타 UI 개선 기능
    // ========================================
    
    /**
     * 툴팁 초기화
     */
    $('[data-toggle="tooltip"]').tooltip();
    
    /**
     * 재고 셀 호버 이벤트 (옵션 재고 표시)
     */
    $('.stock-cell, [data-options]').hover(
        function() {
            var optionsData = $(this).data('options');
            if (optionsData) {
                try {
                    var options = JSON.parse(optionsData);
                    var tooltipContent = '<div style="text-align: left;">';
                    for (var i = 0; i < options.length && i < 5; i++) { // 최대 5개까지만 표시
                        var option = options[i];
                        tooltipContent += '<div>' + option.name + ': ' + option.stock + '개</div>';
                    }
                    if (options.length > 5) {
                        tooltipContent += '<div>... 외 ' + (options.length - 5) + '개</div>';
                    }
                    tooltipContent += '</div>';
                    
                    $(this).attr('data-original-title', tooltipContent);
                    $(this).tooltip({html: true}).tooltip('show');
                } catch (e) {
                    console.error('옵션 데이터 파싱 오류:', e);
                }
            }
        },
        function() {
            $(this).tooltip('hide');
        }
    );
    
    /**
     * 상품 이미지 오류 처리
     */
    $('img.img-thumbnail').on('error', function() {
        $(this).attr('src', '/static/images/no-image.png');
    });
    
    /**
     * 페이지 로드 완료 로그
     */
    console.log('상품목록 관리 기능 초기화 완료');
    
});