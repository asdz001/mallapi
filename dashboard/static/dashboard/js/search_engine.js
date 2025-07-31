/**
 * ========================================
 * 📁 파일 위치: dashboard/static/dashboard/js/search_engine.js
 * 🎯 목적: 공통 검색 엔진 컴포넌트 (확장된 필터 기능 포함)
 * 📅 버전: 3.0 (상품분류 + 날짜필터 추가)
 * 🔄 재사용 가능: 모든 리스트 페이지에서 사용 가능
 * ========================================
 */

/**
 * 🎯 공통 검색엔진 객체
 */
const SearchEngine = {
    
    /**
     * 🔧 검색엔진 초기화
     * @param {Object} config - 설정 객체 (선택사항)
     */
    init: function(config = {}) {
        console.log('🔍 공통 검색엔진 초기화 중...');
        
        // 기본 설정
        this.config = {
            formId: 'search-form',
            searchFieldId: 'search_field',
            searchValueId: 'search_value',
            perPageId: 'per_page',
            resetButtonId: 'reset-search',
            minSearchLength: 2,
            enableCategoryFilter: true,     // 🆕 카테고리 필터 활성화
            enableDateFilter: true,         // 🆕 날짜 필터 활성화
            ...config  // 사용자 설정으로 덮어쓰기
        };
        
        this.bindEvents();
        this.initializeForm();
        this.initializeFilters();  // 🆕 필터 초기화 추가
    },
    
    /**
     * 🔧 이벤트 바인딩
     */
    bindEvents: function() {
        const self = this;
        
        // 📊 페이지당 표시 개수 변경 시 자동 검색
        $(`#${this.config.perPageId}`).on('change', function() {
            $(`#${self.config.formId}`).submit();
        });

        // 🎯 검색 초기화 버튼
        $(`#${this.config.resetButtonId}`).on('click', function() {
            self.resetSearch();
        });

        // ⌨️ Enter 키 검색
        $(`#${this.config.searchValueId}`).on('keypress', function(e) {
            if (e.which === 13) { // Enter 키
                e.preventDefault();
                $(`#${self.config.formId}`).submit();
            }
        });

        // ✅ 폼 제출 전 유효성 검사
        $(`#${this.config.formId}`).on('submit', function(e) {
            return self.validateForm(e);
        });

        // 🆕 카테고리 연동 이벤트
        if (this.config.enableCategoryFilter) {
            $('#category1').on('change', function() {
                self.updateCategory2Options();
            });
        }

        // 🆕 날짜 범위 자동 설정 이벤트
        if (this.config.enableDateFilter) {
            $('#date_range').on('change', function() {
                self.updateDateInputs();
            });
        }
    },
    
    /**
     * 🔧 폼 초기화
     */
    initializeForm: function() {
        // 검색어 입력창에 포커스 (검색어가 없을 때만)
        const searchValue = $(`#${this.config.searchValueId}`).val();
        if (!searchValue || searchValue.trim() === '') {
            $(`#${this.config.searchValueId}`).focus();
        }
    },

    /**
     * 🆕 필터 초기화
     */
    initializeFilters: function() {
        // 날짜 입력창 상태 초기화
        if (this.config.enableDateFilter) {
            this.updateDateInputs();
        }
    },
    
    /**
     * 🎯 검색 초기화 함수
     */
    resetSearch: function() {
        const currentPerPage = $(`#${this.config.perPageId}`).val();
        const baseUrl = window.location.pathname;
        window.location.href = `${baseUrl}?per_page=${currentPerPage}`;
    },
    
    /**
     * ✅ 폼 유효성 검사
     * @param {Event} e - 폼 제출 이벤트
     * @returns {boolean} 유효성 검사 결과
     */
    validateForm: function(e) {
        const searchValue = $(`#${this.config.searchValueId}`).val().trim();
        
        // 검색어가 너무 짧으면 경고
        if (searchValue.length > 0 && searchValue.length < this.config.minSearchLength) {
            e.preventDefault();
            alert(`검색어는 ${this.config.minSearchLength}글자 이상 입력해주세요.`);
            $(`#${this.config.searchValueId}`).focus();
            return false;
        }
        
        // 로딩 상태 표시
        this.showLoadingState();
        return true;
    },
    
    /**
     * 🔄 로딩 상태 표시
     */
    showLoadingState: function() {
        const submitBtn = $(`#${this.config.formId}`).find('button[type="submit"]');
        const originalText = submitBtn.html();
        
        submitBtn.prop('disabled', true);
        submitBtn.html('<i class="fas fa-spinner fa-spin"></i> 검색중...');
        
        // 3초 후 버튼 복구 (타임아웃 방지)
        setTimeout(() => {
            submitBtn.prop('disabled', false);
            submitBtn.html(originalText);
        }, 3000);
    },

    /**
     * 🆕 카테고리2 옵션 업데이트 (AJAX)
     */
    updateCategory2Options: function() {
        const category1Value = $('#category1').val();
        const category2Select = $('#category2');
        
        if (!category1Value) {
            // 카테고리1이 선택되지 않으면 전체 카테고리2 표시
            this.resetCategory2Options();
            return;
        }

        // AJAX로 카테고리2 옵션 가져오기
        $.ajax({
            url: window.location.pathname,
            method: 'GET',
            data: {
                'get_category2': 'true',
                'category1': category1Value
            },
            success: function(response) {
                // 성공 시 옵션 업데이트
                if (response.category2_options) {
                    category2Select.empty();
                    category2Select.append('<option value="">전체</option>');
                    
                    response.category2_options.forEach(function(option) {
                        category2Select.append(`<option value="${option.value}">${option.label}</option>`);
                    });
                }
            },
            error: function() {
                console.log('카테고리2 옵션 로드 실패 - 기본 동작 유지');
            }
        });
    },

    /**
     * 🆕 카테고리2 옵션 초기화
     */
    resetCategory2Options: function() {
        // 전체 카테고리2 옵션으로 복구하는 로직
        // 실제로는 서버에서 받아온 초기 옵션들을 저장해두고 복구
        console.log('카테고리2 옵션 초기화');
    },

    /**
     * 🆕 날짜 입력창 상태 업데이트
     */
    updateDateInputs: function() {
        const dateRange = $('#date_range').val();
        const startDateInput = $('#start_date');
        const endDateInput = $('#end_date');
        
        if (dateRange === '' || dateRange === null) {
            // 직접입력 선택 시 날짜 입력창 활성화
            startDateInput.prop('disabled', false);
            endDateInput.prop('disabled', false);
            startDateInput.removeClass('bg-light');
            endDateInput.removeClass('bg-light');
        } else {
            // 빠른 선택 시 날짜 입력창 비활성화하고 자동 계산
            startDateInput.prop('disabled', true);
            endDateInput.prop('disabled', true);
            startDateInput.addClass('bg-light');
            endDateInput.addClass('bg-light');
            
            // 날짜 자동 계산
            this.calculateDateRange(dateRange);
        }
    },

    /**
     * 🆕 날짜 범위 자동 계산
     * @param {string} range - 날짜 범위 ('today', '7days' 등)
     */
    calculateDateRange: function(range) {
        const today = new Date();
        const startDateInput = $('#start_date');
        const endDateInput = $('#end_date');
        
        let startDate, endDate;
        
        switch(range) {
            case 'today':
                startDate = endDate = today;
                break;
            case 'yesterday':
                startDate = endDate = new Date(today.getTime() - 24 * 60 * 60 * 1000);
                break;
            case '3days':
                startDate = new Date(today.getTime() - 3 * 24 * 60 * 60 * 1000);
                endDate = today;
                break;
            case '7days':
                startDate = new Date(today.getTime() - 7 * 24 * 60 * 60 * 1000);
                endDate = today;
                break;
            case '1month':
                startDate = new Date(today.getTime() - 30 * 24 * 60 * 60 * 1000);
                endDate = today;
                break;
            case '3months':
                startDate = new Date(today.getTime() - 90 * 24 * 60 * 60 * 1000);
                endDate = today;
                break;
            default:
                return;
        }
        
        // 날짜를 YYYY-MM-DD 형식으로 변환
        const formatDate = (date) => {
            return date.getFullYear() + '-' + 
                   String(date.getMonth() + 1).padStart(2, '0') + '-' + 
                   String(date.getDate()).padStart(2, '0');
        };
        
        startDateInput.val(formatDate(startDate));
        endDateInput.val(formatDate(endDate));
    },
    
    /**
     * 🛠️ 현재 검색 데이터 수집
     * @returns {Object} 검색 데이터
     */
    getSearchData: function() {
        return {
            search_field: $(`#${this.config.searchFieldId}`).val(),
            search_value: $(`#${this.config.searchValueId}`).val(),
            per_page: $(`#${this.config.perPageId}`).val(),
            // 🆕 추가 필터 데이터
            gender: $('#gender').val(),
            category1: $('#category1').val(),
            category2: $('#category2').val(),
            include_subcategory: $('#include_subcategory').is(':checked'),
            date_field: $('#date_field').val(),
            date_range: $('#date_range').val(),
            start_date: $('#start_date').val(),
            end_date: $('#end_date').val()
        };
    },
    
    /**
     * 🛠️ URL 파라미터 파싱
     * @param {string} param - 파라미터 이름
     * @returns {string} 파라미터 값
     */
    getUrlParameter: function(param) {
        const urlParams = new URLSearchParams(window.location.search);
        return urlParams.get(param) || '';
    }
};

/**
 * ========================================
 * 🚀 자동 초기화 (DOM 로드 완료 시)
 * ========================================
 */
$(document).ready(function() {
    // 검색 폼이 존재하면 자동으로 초기화
    if ($('#search-form').length > 0) {
        SearchEngine.init();
        console.log('✅ 확장된 검색엔진이 자동 초기화되었습니다.');
    }
});

/**
 * ========================================
 * 🔧 전역 접근용 (다른 스크립트에서 사용 가능)
 * ========================================
 */
window.SearchEngine = SearchEngine;/**
 * ========================================
 * 📁 파일 위치: dashboard/static/dashboard/js/search_engine.js
 * 🎯 목적: 공통 검색 엔진 컴포넌트
 * 📅 버전: 2.0 (공통 컴포넌트로 리팩토링)
 * 🔄 재사용 가능: 모든 리스트 페이지에서 사용 가능
 * ========================================
 */

/**
 * 🎯 공통 검색엔진 객체
 */
const SearchEngine = {
    
    /**
     * 🔧 검색엔진 초기화
     * @param {Object} config - 설정 객체 (선택사항)
     */
    init: function(config = {}) {
        console.log('🔍 공통 검색엔진 초기화 중...');
        
        // 기본 설정
        this.config = {
            formId: 'search-form',
            searchFieldId: 'search_field',
            searchValueId: 'search_value',
            perPageId: 'per_page',
            resetButtonId: 'reset-search',
            minSearchLength: 2,
            ...config  // 사용자 설정으로 덮어쓰기
        };
        
        this.bindEvents();
        this.initializeForm();
    },
    
    /**
     * 🔧 이벤트 바인딩
     */
    bindEvents: function() {
        const self = this;
        
        // 📊 페이지당 표시 개수 변경 시 자동 검색
        $(`#${this.config.perPageId}`).on('change', function() {
            $(`#${self.config.formId}`).submit();
        });

        // 🎯 검색 초기화 버튼
        $(`#${this.config.resetButtonId}`).on('click', function() {
            self.resetSearch();
        });

        // ⌨️ Enter 키 검색
        $(`#${this.config.searchValueId}`).on('keypress', function(e) {
            if (e.which === 13) { // Enter 키
                e.preventDefault();
                $(`#${self.config.formId}`).submit();
            }
        });

        // ✅ 폼 제출 전 유효성 검사
        $(`#${this.config.formId}`).on('submit', function(e) {
            return self.validateForm(e);
        });
    },
    
    /**
     * 🔧 폼 초기화
     */
    initializeForm: function() {
        // 검색어 입력창에 포커스 (검색어가 없을 때만)
        const searchValue = $(`#${this.config.searchValueId}`).val();
        if (!searchValue || searchValue.trim() === '') {
            $(`#${this.config.searchValueId}`).focus();
        }
    },
    
    /**
     * 🎯 검색 초기화 함수
     */
    resetSearch: function() {
        const currentPerPage = $(`#${this.config.perPageId}`).val();
        const baseUrl = window.location.pathname;
        window.location.href = `${baseUrl}?per_page=${currentPerPage}`;
    },
    
    /**
     * ✅ 폼 유효성 검사
     * @param {Event} e - 폼 제출 이벤트
     * @returns {boolean} 유효성 검사 결과
     */
    validateForm: function(e) {
        const searchValue = $(`#${this.config.searchValueId}`).val().trim();
        
        // 검색어가 너무 짧으면 경고
        if (searchValue.length > 0 && searchValue.length < this.config.minSearchLength) {
            e.preventDefault();
            alert(`검색어는 ${this.config.minSearchLength}글자 이상 입력해주세요.`);
            $(`#${this.config.searchValueId}`).focus();
            return false;
        }
        
        // 검색어가 없으면 기본 목록으로 이동
        if (searchValue.length === 0) {
            this.resetSearch();
            e.preventDefault();
            return false;
        }
        
        // 로딩 상태 표시
        this.showLoadingState();
        return true;
    },
    
    /**
     * 🔄 로딩 상태 표시
     */
    showLoadingState: function() {
        const submitBtn = $(`#${this.config.formId}`).find('button[type="submit"]');
        const originalText = submitBtn.html();
        
        submitBtn.prop('disabled', true);
        submitBtn.html('<i class="fas fa-spinner fa-spin"></i> 검색중...');
        
        // 3초 후 버튼 복구 (타임아웃 방지)
        setTimeout(() => {
            submitBtn.prop('disabled', false);
            submitBtn.html(originalText);
        }, 3000);
    },
    
    /**
     * 🛠️ 현재 검색 데이터 수집
     * @returns {Object} 검색 데이터
     */
    getSearchData: function() {
        return {
            search_field: $(`#${this.config.searchFieldId}`).val(),
            search_value: $(`#${this.config.searchValueId}`).val(),
            per_page: $(`#${this.config.perPageId}`).val()
        };
    },
    
    /**
     * 🛠️ URL 파라미터 파싱
     * @param {string} param - 파라미터 이름
     * @returns {string} 파라미터 값
     */
    getUrlParameter: function(param) {
        const urlParams = new URLSearchParams(window.location.search);
        return urlParams.get(param) || '';
    }
};

/**
 * ========================================
 * 🚀 자동 초기화 (DOM 로드 완료 시)
 * ========================================
 */
$(document).ready(function() {
    // 검색 폼이 존재하면 자동으로 초기화
    if ($('#search-form').length > 0) {
        SearchEngine.init();
        console.log('✅ 공통 검색엔진이 자동 초기화되었습니다.');
    }
});

/**
 * ========================================
 * 🔧 전역 접근용 (다른 스크립트에서 사용 가능)
 * ========================================
 */
window.SearchEngine = SearchEngine;