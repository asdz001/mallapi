/**
 * ========================================
 * 📁 파일: dashboard/static/dashboard/js/simple_stock_hover.js
 * 🎯 목적: 재고 셀 호버 시 옵션별 재고 표시 (간단 버전)
 * 📅 버전: 1.0 (Simple & Fast)
 * ========================================
 */

const SimpleStockHover = {
    
    // 설정
    config: {
        stockCellClass: '.stock-cell',
        popupId: 'stock-hover-popup',
        hoverDelay: 300,        // 호버 지연시간 (ms)
        hideDelay: 200          // 숨김 지연시간 (ms)
    },
    
    // 타이머 관리
    timers: {
        showTimer: null,
        hideTimer: null
    },
    
    /**
     * 🚀 초기화
     */
    init: function() {
        console.log('🎯 간단 재고 호버 기능 초기화 중...');
        this.createPopup();
        this.bindEvents();
        console.log('✅ 재고 호버 기능 활성화됨');
    },
    
    /**
     * 🎨 팝업 엘리먼트 생성
     */
    createPopup: function() {
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
        this.addStyles();
    },
    
    /**
     * 🎨 스타일 추가
     */
    addStyles: function() {
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
    
    /**
     * 🔗 이벤트 바인딩
     */
    bindEvents: function() {
        const self = this;
        
        // 재고 셀 호버 이벤트
        $(document).on('mouseenter', this.config.stockCellClass, function(e) {
            self.handleMouseEnter($(this), e);
        });
        
        $(document).on('mouseleave', this.config.stockCellClass, function(e) {
            self.handleMouseLeave();
        });
        
        // 팝업 자체에도 호버 이벤트 (팝업에 마우스 올리면 유지)
        $(document).on('mouseenter', `#${this.config.popupId}`, function() {
            self.cancelHideTimer();
        });
        
        $(document).on('mouseleave', `#${this.config.popupId}`, function() {
            self.scheduleHide();
        });
    },
    
    /**
     * 🖱️ 마우스 진입 처리
     */
    handleMouseEnter: function($cell, event) {
        const self = this;
        
        // 숨김 타이머 취소
        this.cancelHideTimer();
        
        // 표시 타이머 설정
        this.timers.showTimer = setTimeout(function() {
            self.showPopup($cell, event);
        }, this.config.hoverDelay);
    },
    
    /**
     * 🖱️ 마우스 나감 처리
     */
    handleMouseLeave: function() {
        // 표시 타이머 취소
        if (this.timers.showTimer) {
            clearTimeout(this.timers.showTimer);
            this.timers.showTimer = null;
        }
        
        // 숨김 타이머 설정
        this.scheduleHide();
    },
    
    /**
     * 🎈 팝업 표시
     */
    showPopup: function($cell, event) {
        // 옵션 데이터 추출
        const optionsData = this.getOptionsData($cell);
        const productName = this.getProductName($cell);
        
        console.log('팝업 표시 시도:', {productName, optionsData}); // 디버깅용
        
        if (!optionsData || optionsData.length === 0) {
            console.warn('옵션 데이터가 없어서 팝업을 표시하지 않습니다.');
            // 빈 데이터라도 팝업은 표시
        }
        
        // 팝업 내용 업데이트
        this.updatePopupContent(productName, optionsData);
        
        // 팝업 위치 설정
        this.positionPopup($cell);
        
        // 팝업 표시
        $(`#${this.config.popupId}`).fadeIn(200);
    },
    
    /**
     * 📊 옵션 데이터 추출
     */
    getOptionsData: function($cell) {
        try {
            // data-options 속성에서 JSON 파싱
            const optionsJson = $cell.attr('data-options');
            console.log('원본 JSON 데이터:', optionsJson); // 디버깅용
            
            if (!optionsJson || optionsJson.trim() === '') {
                console.warn('옵션 데이터가 비어있습니다.');
                return [];
            }
            
            // JSON 문자열 정리 (불필요한 문자 제거)
            const cleanJson = optionsJson.trim();
            
            const parsed = JSON.parse(cleanJson);
            console.log('파싱된 데이터:', parsed); // 디버깅용
            
            return parsed;
        } catch (e) {
            console.error('옵션 데이터 파싱 오류:', e);
            console.error('문제가 된 JSON 문자열:', $cell.attr('data-options'));
            return [];
        }
    },
    
    /**
     * 📝 상품명 추출
     */
    getProductName: function($cell) {
        // 같은 행의 상품명 셀에서 추출
        const $row = $cell.closest('tr');
        const $productNameCell = $row.find('td').eq(4); // product_name 컬럼 (5번째)
        return $productNameCell.text().trim() || '상품명 없음';
    },
    
    /**
     * 🎨 팝업 내용 업데이트
     */
    updatePopupContent: function(productName, optionsData) {
        const popup = $(`#${this.config.popupId}`);
        
        // 헤더 업데이트
        popup.find('.popup-title').text(productName);
        
        // 옵션 리스트 생성
        let optionsHtml = '';
        let totalStock = 0;
        
        if (optionsData && optionsData.length > 0) {
            optionsData.forEach(function(option) {
                const stockClass = SimpleStockHover.getStockClass(option.stock);
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
    
    /**
     * 🎨 재고 수준별 클래스 반환
     */
    getStockClass: function(stock) {
        if (stock === 0) return 'stock-low';
        if (stock <= 5) return 'stock-medium';
        return 'stock-high';
    },
    
    /**
     * 📍 팝업 위치 설정
     */
    positionPopup: function($cell) {
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
            left = cellOffset.left - popupWidth - 10; // 좌측으로 이동
        }
        
        if (top + popupHeight > windowHeight + scrollTop) {
            top = cellOffset.top - popupHeight + cellHeight; // 상단으로 이동
        }
        
        // 최소 여백 보장
        left = Math.max(10, left);
        top = Math.max(scrollTop + 10, top);
        
        popup.css({
            left: left + 'px',
            top: top + 'px'
        });
    },
    
    /**
     * ⏰ 숨김 예약
     */
    scheduleHide: function() {
        const self = this;
        this.timers.hideTimer = setTimeout(function() {
            $(`#${self.config.popupId}`).fadeOut(150);
        }, this.config.hideDelay);
    },
    
    /**
     * ⏰ 숨김 타이머 취소
     */
    cancelHideTimer: function() {
        if (this.timers.hideTimer) {
            clearTimeout(this.timers.hideTimer);
            this.timers.hideTimer = null;
        }
    }
};

/**
 * ========================================
 * 🚀 자동 초기화
 * ========================================
 */
$(document).ready(function() {
    // 재고 셀이 있는 경우에만 초기화
    if ($('.stock-cell').length > 0) {
        SimpleStockHover.init();
    }
});

/**
 * ========================================
 * 🌏 전역 접근
 * ========================================
 */
window.SimpleStockHover = SimpleStockHover;