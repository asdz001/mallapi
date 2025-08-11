/**
 * ========================================
 * 📁 파일: dashboard/static/dashboard/js/product_list_complete.js
 * 🎯 목적: 상품목록 관리 통합 JavaScript (재고호버 + 컬럼설정 + UI기능)
 * 📅 버전: 2.0 (통합 완성본)
 * ========================================
 */

const ProductListManager = {
    
    // ========================================
    // 🔧 전역 설정
    // ========================================
    config: {
        // 재고 호버 설정
        stockCellClass: '.stock-cell',
        popupId: 'stock-hover-popup',
        hoverDelay: 300,
        hideDelay: 200,
        
        // 컬럼 설정 관련
        columnModalId: 'columnSettingsModal',
        columnListId: 'column-list',
        
        // AJAX 경로 (실제 URLs와 맞춤)
        ajaxUrls: {
            saveColumnSettings: '/dashboard/products/column-settings/save/',
            getColumnSettings: '/dashboard/products/column-settings/get/'
        }
    },
    
    // 전역 변수
    data: {
        columnSettings: {},
        defaultColumns: [],
        timers: {
            showTimer: null,
            hideTimer: null
        }
    },
    
    // ========================================
    // 🚀 초기화
    // ========================================
    init: function() {
        console.log('🎯 상품목록 관리 시스템 초기화 중...');
        
        // 기본 설정
        this.setupCSRF();
        this.initStockHover();
        this.initColumnSettings();
        this.initUIHelpers();
        
        console.log('✅ 상품목록 관리 시스템 초기화 완료');
    },
    
    // ========================================
    // 🔹 CSRF 토큰 설정
    // ========================================
    setupCSRF: function() {
        // Django CSRF 토큰 가져오기
        function getCSRFToken() {
            return $('[name=csrfmiddlewaretoken]').val() || 
                   $('meta[name=csrf-token]').attr('content') ||
                   '';
        }
        
        // AJAX 요청에 CSRF 토큰 자동 추가
        $.ajaxSetup({
            beforeSend: function(xhr, settings) {
                if (!(/^http:.*/.test(settings.url) || /^https:.*/.test(settings.url))) {
                    xhr.setRequestHeader("X-CSRFToken", getCSRFToken());
                }
            }
        });
        
        // 전역 함수로 등록 (다른 함수에서 사용)
        this.getCSRFToken = getCSRFToken;
    },
    
    // ========================================
    // 📦 재고 호버 기능 (simple_stock_hover.js 기반)
    // ========================================
    initStockHover: function() {
        console.log('📦 재고 호버 기능 초기화...');
        
        // 재고 셀이 있는지 확인
        if ($(this.config.stockCellClass).length === 0) {
            console.warn('재고 셀이 없어서 호버 기능을 비활성화합니다.');
            return;
        }
        
        this.createStockPopup();
        this.bindStockEvents();
        console.log('✅ 재고 호버 기능 활성화됨');
    },
    
    createStockPopup: function() {
        // 기존 팝업 제거
        $(`#${this.config.popupId}`).remove();
        
        // 팝업 HTML 생성
        const popupHtml = `
            <div id="${this.config.popupId}" class="stock-hover-popup">
                <div class="popup-header">
                    <span class="popup-title"></span>
                </div>
                <div class="popup-body">
                    <div class="options-container"></div>
                    <div class="total-stock-row">
                        <span class="total-label">총 재고:</span>
                        <span class="total-value"></span>
                    </div>
                </div>
            </div>
        `;
        
        $('body').append(popupHtml);
        this.addStockPopupStyles();
    },
    
    addStockPopupStyles: function() {
        const styles = `
            <style id="stock-hover-styles">
                .stock-hover-popup {
                    position: absolute;
                    background: #fff;
                    border: 1px solid #ddd;
                    border-radius: 8px;
                    box-shadow: 0 4px 15px rgba(0,0,0,0.15);
                    z-index: 9999;
                    min-width: 200px;
                    max-width: 250px;
                    font-size: 13px;
                    display: none;
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif;
                }
                
                .stock-hover-popup .popup-header {
                    background: linear-gradient(135deg, #6c5ce7, #5f3dc4);
                    color: white;
                    padding: 10px 15px;
                    border-radius: 7px 7px 0 0;
                    font-weight: 600;
                    font-size: 14px;
                }
                
                .stock-hover-popup .popup-body {
                    padding: 12px;
                }
                
                .stock-hover-popup .option-row {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    padding: 6px 0;
                    border-bottom: 1px solid #f1f3f4;
                }
                
                .stock-hover-popup .option-row:last-child {
                    border-bottom: none;
                }
                
                .stock-hover-popup .option-name {
                    font-weight: 500;
                    color: #2d3748;
                }
                
                .stock-hover-popup .option-stock {
                    font-weight: 600;
                    font-size: 12px;
                    padding: 3px 8px;
                    border-radius: 10px;
                    min-width: 35px;
                    text-align: center;
                }
                
                .stock-hover-popup .stock-high {
                    background: #d4edda;
                    color: #155724;
                }
                
                .stock-hover-popup .stock-medium {
                    background: #fff3cd;
                    color: #856404;
                }
                
                .stock-hover-popup .stock-low {
                    background: #f8d7da;
                    color: #721c24;
                }
                
                .stock-hover-popup .total-stock-row {
                    margin-top: 10px;
                    padding-top: 10px;
                    border-top: 2px solid #6c5ce7;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    font-weight: 600;
                    color: #6c5ce7;
                }
                
                .stock-hover-popup .total-value {
                    background: #6c5ce7;
                    color: white;
                    padding: 4px 12px;
                    border-radius: 12px;
                    font-size: 13px;
                }
                
                .stock-hover-popup .no-options {
                    text-align: center;
                    color: #6c757d;
                    padding: 20px;
                    font-style: italic;
                }
                
                /* 재고 셀 호버 효과 */
                .stock-cell {
                    cursor: pointer;
                    transition: all 0.2s ease;
                    position: relative;
                }
                
                .stock-cell:hover {
                    background-color: #e8f4f8 !important;
                    transform: scale(1.02);
                    font-weight: 600;
                }
                
                .stock-cell::before {
                    content: "📦";
                    position: absolute;
                    right: 2px;
                    top: 2px;
                    font-size: 10px;
                    opacity: 0;
                    transition: opacity 0.2s ease;
                }
                
                .stock-cell:hover::before {
                    opacity: 0.6;
                }
            </style>
        `;
        
        $('#stock-hover-styles').remove();
        $('head').append(styles);
    },
    
    bindStockEvents: function() {
        const self = this;
        
        // 재고 셀 호버 이벤트
        $(document).on('mouseenter', this.config.stockCellClass, function(e) {
            self.handleStockMouseEnter($(this), e);
        });
        
        $(document).on('mouseleave', this.config.stockCellClass, function(e) {
            self.handleStockMouseLeave();
        });
        
        // 팝업 자체에도 호버 이벤트
        $(document).on('mouseenter', `#${this.config.popupId}`, function() {
            self.cancelHideTimer();
        });
        
        $(document).on('mouseleave', `#${this.config.popupId}`, function() {
            self.scheduleHide();
        });
    },
    
    handleStockMouseEnter: function($cell, event) {
        const self = this;
        
        // 숨김 타이머 취소
        this.cancelHideTimer();
        
        // 표시 타이머 설정
        this.data.timers.showTimer = setTimeout(function() {
            self.showStockPopup($cell, event);
        }, this.config.hoverDelay);
    },
    
    handleStockMouseLeave: function() {
        // 표시 타이머 취소
        if (this.data.timers.showTimer) {
            clearTimeout(this.data.timers.showTimer);
            this.data.timers.showTimer = null;
        }
        
        // 숨김 타이머 설정
        this.scheduleHide();
    },
    
    showStockPopup: function($cell, event) {
        // 옵션 데이터 추출
        const optionsData = this.getStockOptionsData($cell);
        const productName = this.getProductName($cell);
        
        console.log('재고 팝업 표시:', {productName, optionsData});
        
        // 팝업 내용 업데이트
        this.updateStockPopupContent(productName, optionsData);
        
        // 팝업 위치 설정
        this.positionStockPopup($cell);
        
        // 팝업 표시
        $(`#${this.config.popupId}`).fadeIn(200);
    },
    
    getStockOptionsData: function($cell) {
        try {
            // data-options 속성에서 JSON 파싱
            let optionsJson = $cell.attr('data-options');
            
            if (!optionsJson || optionsJson.trim() === '') {
                console.warn('옵션 데이터가 비어있습니다.');
                return [];
            }
            
            // HTML escape된 문자 복원
            optionsJson = optionsJson.replace(/&quot;/g, '"')
                                   .replace(/&#x27;/g, "'")
                                   .replace(/&lt;/g, '<')
                                   .replace(/&gt;/g, '>')
                                   .replace(/&amp;/g, '&');
            
            const parsed = JSON.parse(optionsJson);
            console.log('파싱된 옵션 데이터:', parsed);
            
            return parsed;
        } catch (e) {
            console.error('옵션 데이터 파싱 오류:', e);
            console.error('문제가 된 JSON:', $cell.attr('data-options'));
            return [];
        }
    },
    
    getProductName: function($cell) {
        // 같은 행에서 상품명 찾기 (더 안전한 방법)
        const $row = $cell.closest('tr');
        
        // 여러 방법으로 상품명 찾기
        let productName = '';
        
        // 1. data-product-name 속성이 있다면
        productName = $row.attr('data-product-name');
        if (productName) return productName;
        
        // 2. product_name 클래스가 있는 셀 찾기
        const $nameCell = $row.find('.product-name-cell, [data-field="product_name"]');
        if ($nameCell.length > 0) {
            productName = $nameCell.text().trim();
            if (productName) return productName;
        }
        
        // 3. 순서로 찾기 (5번째 컬럼이라고 가정)
        const $fifthCell = $row.find('td').eq(4);
        if ($fifthCell.length > 0) {
            productName = $fifthCell.text().trim();
            if (productName) return productName;
        }
        
        return '상품명 없음';
    },
    
    updateStockPopupContent: function(productName, optionsData) {
        const popup = $(`#${this.config.popupId}`);
        
        // 헤더 업데이트
        popup.find('.popup-title').text(productName);
        
        // 옵션 리스트 생성
        let optionsHtml = '';
        let totalStock = 0;
        
        if (optionsData && optionsData.length > 0) {
            optionsData.forEach(function(option) {
                const stockClass = ProductListManager.getStockClass(option.stock);
                totalStock += option.stock;
                
                optionsHtml += `
                    <div class="option-row">
                        <span class="option-name">${option.name}</span>
                        <span class="option-stock ${stockClass}">${option.stock}</span>
                    </div>
                `;
            });
        } else {
            optionsHtml = '<div class="no-options">등록된 옵션이 없습니다</div>';
        }
        
        // 내용 업데이트
        popup.find('.options-container').html(optionsHtml);
        popup.find('.total-value').text(totalStock + '개');
    },
    
    getStockClass: function(stock) {
        if (stock === 0) return 'stock-low';
        if (stock <= 5) return 'stock-medium';
        return 'stock-high';
    },
    
    positionStockPopup: function($cell) {
        const popup = $(`#${this.config.popupId}`);
        const cellOffset = $cell.offset();
        const cellWidth = $cell.outerWidth();
        const cellHeight = $cell.outerHeight();
        const popupWidth = popup.outerWidth() || 300;
        const popupHeight = popup.outerHeight() || 200;
        const windowWidth = $(window).width();
        const windowHeight = $(window).height();
        const scrollTop = $(window).scrollTop();
        
        // 기본 위치 (셀 우측)
        let left = cellOffset.left + cellWidth + 10;
        let top = cellOffset.top;
        
        // 화면 경계 검사
        if (left + popupWidth > windowWidth) {
            left = cellOffset.left - popupWidth - 10;
        }
        
        if (top + popupHeight > windowHeight + scrollTop) {
            top = cellOffset.top - popupHeight + cellHeight;
        }
        
        // 최소 여백 보장
        left = Math.max(10, left);
        top = Math.max(scrollTop + 10, top);
        
        popup.css({
            left: left + 'px',
            top: top + 'px'
        });
    },
    
    scheduleHide: function() {
        const self = this;
        this.data.timers.hideTimer = setTimeout(function() {
            $(`#${self.config.popupId}`).fadeOut(150);
        }, this.config.hideDelay);
    },
    
    cancelHideTimer: function() {
        if (this.data.timers.hideTimer) {
            clearTimeout(this.data.timers.hideTimer);
            this.data.timers.hideTimer = null;
        }
    },
    
    // ========================================
    // 📋 컬럼 설정 기능 (product_list_management.js 기반)
    // ========================================
    initColumnSettings: function() {
        console.log('📋 컬럼 설정 기능 초기화...');
        
        // 컬럼설정 버튼 이벤트 (여러 ID 시도)
        const buttonSelectors = [
            '#column-settings',      // 실제 HTML ID (추정)
            '#column-settings-btn',  // 기존 JS ID
            '.btn-column-settings',  // 클래스 방식
            '[data-action="column-settings"]'  // data 속성 방식
        ];
        
        let buttonFound = false;
        buttonSelectors.forEach(selector => {
            if ($(selector).length > 0) {
                console.log(`컬럼설정 버튼 발견: ${selector}`);
                $(selector).off('click.columnSettings').on('click.columnSettings', () => {
                    this.openColumnSettingsModal();
                });
                buttonFound = true;
            }
        });
        
        if (!buttonFound) {
            console.warn('컬럼설정 버튼을 찾을 수 없습니다. 다음 중 하나를 HTML에 추가하세요:', buttonSelectors);
        }
        
        // 모달 이벤트
        this.bindColumnModalEvents();
        
        console.log('✅ 컬럼 설정 기능 초기화 완료');
    },
    
    openColumnSettingsModal: function() {
        console.log('컬럼설정 모달 열기');
        this.loadColumnSettings();
        $(`#${this.config.columnModalId}`).modal('show');
    },
    
    loadColumnSettings: function() {
        console.log('컬럼 설정 로드 중...');
        
        // 기본 컬럼 데이터 가져오기 (여러 방법 시도)
        this.data.defaultColumns = this.getDefaultColumns();
        
        if (this.data.defaultColumns.length === 0) {
            alert('컬럼 정보를 불러올 수 없습니다. HTML에서 컬럼 데이터를 확인해주세요.');
            return;
        }
        
        // 서버에서 사용자 설정 로드 (실패해도 기본값 사용)
        $.get(this.config.ajaxUrls.getColumnSettings)
            .done((response) => {
                console.log('서버 응답:', response);
                if (response.success) {
                    this.data.columnSettings = response.column_settings;
                } else {
                    console.warn('서버에서 설정을 불러올 수 없음, 기본값 사용');
                    this.data.columnSettings = {};
                }
                this.buildColumnList();
                this.initSortable();
            })
            .fail((xhr) => {
                console.warn('AJAX 요청 실패, 기본값 사용:', xhr.responseText);
                this.data.columnSettings = {};
                this.buildColumnList();
                this.initSortable();
            });
    },
    
    getDefaultColumns: function() {
        // 여러 방법으로 기본 컬럼 정보 가져오기
        
        // 1. window 객체에서
        if (typeof window.productColumns !== 'undefined') {
            console.log('window.productColumns에서 컬럼 정보 로드');
            return window.productColumns;
        }
        
        // 2. HTML data 속성에서
        const columnData = $('body').attr('data-product-columns');
        if (columnData) {
            try {
                console.log('HTML data 속성에서 컬럼 정보 로드');
                return JSON.parse(columnData);
            } catch (e) {
                console.error('HTML 컬럼 데이터 파싱 오류:', e);
            }
        }
        
        // 3. 🔧 전체 기본 컬럼 목록 (하드코딩) - 숨겨진 컬럼도 포함
        console.log('하드코딩된 전체 컬럼 정보 사용');
        return [
            { field: 'external_product_id', header: '상품ID' },
            { field: 'retailer', header: '부띠끄' },
            { field: 'image_url_1', header: '썸네일' },
            { field: 'brand_name', header: '브랜드' },
            { field: 'product_name', header: '상품명' },
            { field: 'sku', header: 'SKU' },
            { field: 'gender', header: '성별' },
            { field: 'category_combined', header: '카테고리' },
            { field: 'season', header: '시즌' },
            { field: 'color', header: '색상' },
            { field: 'price_retail', header: '소비자가(€)' },
            { field: 'price_org', header: 'COST' },
            { field: 'markup', header: 'MARKUP' },
            { field: 'price_supply', header: '공급가(€)' },
            { field: 'retail_price_krw', header: '소비자가' },
            { field: 'calculated_price_krw', header: '판매가' },
            { field: 'total_stock', header: '재고' },
            { field: 'status', header: '판매상태' },
            { field: 'sold_out_status', header: '품절상태' },
            { field: 'created_at', header: '등록일' },
            { field: 'updated_at', header: '수정일' }
        ];
    },
    
    buildColumnList: function() {
        console.log('컬럼 목록 생성 중...');
        
        const columnList = $(`#${this.config.columnListId}`);
        columnList.empty();
        
        // 설정에 따라 정렬된 컬럼 목록 생성
        const sortedColumns = [];
        this.data.defaultColumns.forEach((col, index) => {
            const setting = this.data.columnSettings[col.field] || {visible: true, order: index + 1};
            sortedColumns.push({
                field: col.field,
                header: col.header,
                visible: setting.visible,
                order: setting.order
            });
        });
        
        // order 순서대로 정렬
        sortedColumns.sort((a, b) => a.order - b.order);
        
        // HTML 생성
        sortedColumns.forEach(col => {
            const checkedAttr = col.visible ? 'checked' : '';
            const html = `
                <div class="column-item" data-field="${col.field}">
                    <div class="d-flex align-items-center">
                        <i class="fas fa-grip-vertical drag-handle me-2"></i>
                        <div class="form-check flex-grow-1">
                            <input class="form-check-input" type="checkbox" id="col_${col.field}" ${checkedAttr}>
                            <label class="form-check-label" for="col_${col.field}">${col.header}</label>
                        </div>
                    </div>
                </div>
            `;
            columnList.append(html);
        });
        
        console.log('컬럼 목록 생성 완료');
    },
    
    initSortable: function() {
        // jQuery UI Sortable 확인
        if ($.fn.sortable) {
            $(`#${this.config.columnListId}`).sortable({
                handle: '.drag-handle',
                placeholder: 'ui-sortable-placeholder',
                tolerance: 'pointer'
            });
            console.log('드래그 정렬 초기화 완료');
        } else {
            console.warn('jQuery UI Sortable이 로드되지 않음. 드래그 정렬 기능을 사용할 수 없습니다.');
        }
    },
    
    bindColumnModalEvents: function() {
        // 저장 버튼
        $('#save-column-settings').off('click.columnSave').on('click.columnSave', () => {
            this.saveColumnSettings();
        });
        
        // 모달 닫기 이벤트
        $(`#${this.config.columnModalId}`).on('hidden.bs.modal', () => {
            console.log('컬럼설정 모달창 닫힘');
            this.data.columnSettings = {};
        });
        
        // 닫기 버튼들
        $(`#${this.config.columnModalId} .close, #${this.config.columnModalId} [data-dismiss="modal"], #${this.config.columnModalId} [data-bs-dismiss="modal"]`)
            .off('click.columnClose').on('click.columnClose', () => {
                $(`#${this.config.columnModalId}`).modal('hide');
            });
        
        // ESC 키
        $(document).off('keydown.columnEsc').on('keydown.columnEsc', (e) => {
            if (e.keyCode === 27 && $(`#${this.config.columnModalId}`).hasClass('show')) {
                $(`#${this.config.columnModalId}`).modal('hide');
            }
        });
    },
    
    saveColumnSettings: function() {
        console.log('컬럼 설정 저장 중...');
        
        const newColumnSettings = {};
        let order = 1;
        
        $(`#${this.config.columnListId} .column-item`).each(function() {
            const field = $(this).data('field');
            const visible = $(this).find('input[type="checkbox"]').is(':checked');
            
            newColumnSettings[field] = {
                visible: visible,
                order: order++
            };
        });
        
        console.log('저장할 설정:', newColumnSettings);
        
        // 서버로 전송
        $.post(this.config.ajaxUrls.saveColumnSettings, {
            column_settings: JSON.stringify(newColumnSettings),
            csrfmiddlewaretoken: this.getCSRFToken()
        })
        .done((response) => {
            console.log('저장 응답:', response);
            if (response.success) {
                alert('컬럼 설정이 저장되었습니다.');
                $(`#${this.config.columnModalId}`).modal('hide');
                location.reload(); // 페이지 새로고침
            } else {
                alert('저장 실패: ' + response.message);
            }
        })
        .fail((xhr) => {
            console.error('저장 오류:', xhr.responseText);
            alert('서버 오류가 발생했습니다. 컬럼설정 기능이 아직 구현되지 않았을 수 있습니다.');
        });
    },
    
    // ========================================
    // 🎨 기타 UI 도우미 기능들
    // ========================================
    initUIHelpers: function() {
        console.log('🎨 UI 도우미 기능 초기화...');
        
        // 툴팁 초기화
        this.initTooltips();
        
        // 검색어 Enter 키 처리
        this.initSearchKeyboard();
        
        // 이미지 오류 처리
        this.initImageErrorHandling();
        
        // 상품 관리 기능
        this.initProductManagement();
        
        console.log('✅ UI 도우미 기능 초기화 완료');
    },
    
    initTooltips: function() {
        // Bootstrap 툴팁 초기화 (Bootstrap 4/5 호환)
        if ($.fn.tooltip) {
            $('[data-toggle="tooltip"], [data-bs-toggle="tooltip"]').tooltip();
        }
    },
    
    initSearchKeyboard: function() {
        // 검색어 Enter 키 처리
        $('#search_value').off('keypress.search').on('keypress.search', function(e) {
            if (e.which === 13) { // Enter 키
                e.preventDefault();
                $('#search-form, .search-form').submit();
            }
        });
    },
    
    initImageErrorHandling: function() {
        // 상품 이미지 오류 처리
        $('img.img-thumbnail').off('error.productImg').on('error.productImg', function() {
            $(this).attr('src', '/static/images/no-image.png');
        });
    },
    
    initProductManagement: function() {
        // 상품 수정 함수 (전역으로 등록)
        window.editProduct = function(productId) {
            console.log('상품 수정:', productId);
            // TODO: 상품 수정 모달창 구현
            alert('상품 수정 기능은 추후 구현 예정입니다. ID: ' + productId);
        };
    }
};

/**
 * ========================================
 * 🚀 자동 초기화 및 전역 등록
 * ========================================
 */
$(document).ready(function() {
    // 상품목록 페이지에서만 초기화
    if ($('body').hasClass('product-list-page') || $('.dashboard-table').length > 0) {
        ProductListManager.init();
    }
});

// 전역 접근을 위한 등록
window.ProductListManager = ProductListManager;

// 개별 기능들도 전역 접근 가능하도록 (하위 호환성)
window.SimpleStockHover = {
    init: () => ProductListManager.initStockHover(),
    getStockClass: ProductListManager.getStockClass
};