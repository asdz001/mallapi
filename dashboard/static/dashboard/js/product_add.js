// dashboard/static/dashboard/js/product_add.js

/**
 * 🎯 상품등록 페이지 JavaScript
 * - 일반등록 / 엑셀등록 탭 관리
 * - 동적 옵션 추가/삭제
 * - 모달 선택 기능 (부띠끄, 브랜드, 성별, 카테고리, 원산지)
 * - 실시간 검증
 * - 미리보기 기능
 */

$(document).ready(function() {
    ProductAdd.init();
});

const ProductAdd = {
    // ========================================
    // 🔧 설정 및 변수
    // ========================================
    config: {
        maxOptions: 20,           // 최대 옵션 개수
        maxImages: 4,             // 최대 이미지 개수  
        maxFileSize: 5 * 1024 * 1024,  // 5MB
        allowedImageTypes: ['image/jpeg', 'image/jpg', 'image/png', 'image/webp']
    },
    
    currentTab: 'manual',         // 현재 활성 탭
    optionCount: 1,              // 현재 옵션 개수
    
    // ========================================
    // 🔧 초기화
    // ========================================
    init: function() {
        console.log('🚀 상품등록 페이지 초기화');
        
        this.bindEvents();
        this.initializeOptions();
        this.initializeValidation();
        this.setupImagePreview();
        this.initializeModals(); // ✅ 모달 초기화 추가
        
        // 기본값 설정
        this.switchTab('manual');
    },
    
    // ========================================
    // 🔧 이벤트 바인딩
    // ========================================
    bindEvents: function() {
        // 탭 전환
        $('.register-tab').on('click', this.handleTabClick.bind(this));
        
        // 옵션 관리
        $('#add-option-btn').on('click', this.addOptionRow.bind(this));
        $(document).on('click', '.remove-option-btn', this.removeOptionRow.bind(this));
        
        // 빠른 옵션 템플릿
        $('.quick-template-btn').on('click', this.applyQuickTemplate.bind(this));
        
        // 토글 선택
        $('.toggle-item').on('click', this.handleToggleClick.bind(this));
        
        // 실시간 검증
        $('#sku').on('blur', this.validateSKU.bind(this));
        $('#external_product_id').on('blur', this.validateProductID.bind(this));
        
        // 이미지 업로드
        $('.image-input').on('change', this.handleImageUpload.bind(this));
        
        // 폼 제출 전 검증
        $('#product-form').on('submit', this.validateForm.bind(this));
        
        // 미리보기
        $('#preview-btn').on('click', this.showPreview.bind(this));
        
        // 엑셀 업로드
        $('#excel-file').on('change', this.handleExcelUpload.bind(this));
        $('#download-template-btn').on('click', this.downloadTemplate.bind(this));
    },
    
    // ========================================
    // ✅ 모달 초기화 (새로 추가)
    // ========================================
    initializeModals: function() {
        console.log('🔧 모달 초기화');
        
        // 모달 열림 이벤트 바인딩
        $('#retailerModal').on('shown.bs.modal', function () {
            $('#retailer-search').val('').focus();
            $('.retailer-item').show();
        });

        $('#brandModal').on('shown.bs.modal', function () {
            $('#brand-search').val('').focus();
            $('.brand-item').show();
        });

        $('#genderModal').on('shown.bs.modal', function () {
            $('#gender-search').val('').focus();
            $('.gender-item').show();
        });

        $('#category1Modal').on('shown.bs.modal', function () {
            $('#category1-search').val('').focus();
            $('.category1-item').show();
        });

        $('#category2Modal').on('shown.bs.modal', function () {
            $('#category2-search').val('').focus();
            $('.category2-item').show();
        });

        $('#originModal').on('shown.bs.modal', function () {
            $('#origin-search').val('').focus();
            $('.origin-item').show();
        });
    },
    
    // ========================================
    // ✅ 모달 관련 함수들 (새로 추가)
    // ========================================
    
    // 부띠끄 관련 함수들
    openRetailerModal: function() {
        $('#retailerModal').modal('show');
    },
    
    filterRetailers: function() {
        const searchValue = document.getElementById('retailer-search').value.toLowerCase();
        const items = document.querySelectorAll('.retailer-item');

        items.forEach(item => {
            const text = item.textContent.toLowerCase();
            if (text.includes(searchValue)) {
                item.style.display = 'block';
            } else {
                item.style.display = 'none';
            }
        });
    },
    
    selectRetailer: function(id, name) {
        document.getElementById('retailer_display').value = name;
        document.getElementById('retailer_text').value = name;
        document.getElementById('retailer_id').value = id;
        $('#retailerModal').modal('hide');
        console.log(`🎯 부띠끄 선택: ${name} (ID: ${id})`);
    },
    
    // 브랜드 관련 함수들
    openBrandModal: function() {
        $('#brandModal').modal('show');
    },
    
    filterBrands: function() {
        const searchValue = document.getElementById('brand-search').value.toLowerCase();
        const items = document.querySelectorAll('.brand-item');

        items.forEach(item => {
            const text = item.textContent.toLowerCase();
            if (text.includes(searchValue)) {
                item.style.display = 'block';
            } else {
                item.style.display = 'none';
            }
        });
    },
    
    selectBrand: function(id, name) {
        document.getElementById('brand_display').value = name;
        document.getElementById('brand_name_text').value = name;
        document.getElementById('brand_name_id').value = id;
        $('#brandModal').modal('hide');
        console.log(`🎯 브랜드 선택: ${name} (ID: ${id})`);
    },
    
    addNewBrand: function() {
        const searchValue = document.getElementById('brand-search').value;
        if (searchValue) {
            document.getElementById('brand_display').value = searchValue;
            document.getElementById('brand_name_text').value = searchValue;
            $('#brandModal').modal('hide');
        } else {
            this.showAlert('info', '새 브랜드 등록 기능은 추후 구현 예정입니다.');
        }
    },
    
    // 성별 관련 함수들
    openGenderModal: function() {
        $('#genderModal').modal('show');
    },
    
    filterGenders: function() {
        const searchValue = document.getElementById('gender-search').value.toLowerCase();
        const items = document.querySelectorAll('.gender-item');

        items.forEach(item => {
            const text = item.textContent.toLowerCase();
            if (text.includes(searchValue)) {
                item.style.display = 'block';
            } else {
                item.style.display = 'none';
            }
        });
    },
    
    selectGenderFromModal: function(id, name) {
        document.getElementById('gender_display').value = name;
        document.getElementById('gender_text').value = name;
        document.getElementById('gender_id').value = id;
        $('#genderModal').modal('hide');
        console.log(`🎯 성별 선택: ${name} (ID: ${id})`);
    },
    
    // 카테고리1 관련 함수들
    openCategory1Modal: function() {
        $('#category1Modal').modal('show');
    },
    
    filterCategory1: function() {
        const searchValue = document.getElementById('category1-search').value.toLowerCase();
        const items = document.querySelectorAll('.category1-item');

        items.forEach(item => {
            const text = item.textContent.toLowerCase();
            if (text.includes(searchValue)) {
                item.style.display = 'block';
            } else {
                item.style.display = 'none';
            }
        });
    },
    
    selectCategory1: function(id, name) {
        document.getElementById('category1_display').value = name;
        document.getElementById('category1_text').value = name;
        document.getElementById('category1_id').value = id;
        $('#category1Modal').modal('hide');
        console.log(`🎯 카테고리1 선택: ${name} (ID: ${id})`);
    },
    
    // 카테고리2 관련 함수들
    openCategory2Modal: function() {
        $('#category2Modal').modal('show');
    },
    
    filterCategory2: function() {
        const searchValue = document.getElementById('category2-search').value.toLowerCase();
        const items = document.querySelectorAll('.category2-item');

        items.forEach(item => {
            const text = item.textContent.toLowerCase();
            if (text.includes(searchValue)) {
                item.style.display = 'block';
            } else {
                item.style.display = 'none';
            }
        });
    },
    
    selectCategory2: function(id, name) {
        document.getElementById('category2_display').value = name;
        document.getElementById('category2_text').value = name;
        document.getElementById('category2_id').value = id;
        $('#category2Modal').modal('hide');
        console.log(`🎯 카테고리2 선택: ${name} (ID: ${id})`);
    },
    
    // 원산지 관련 함수들
    openOriginModal: function() {
        $('#originModal').modal('show');
    },
    
    filterOrigins: function() {
        const searchValue = document.getElementById('origin-search').value.toLowerCase();
        const items = document.querySelectorAll('.origin-item');

        items.forEach(item => {
            const text = item.textContent.toLowerCase();
            if (text.includes(searchValue)) {
                item.style.display = 'block';
            } else {
                item.style.display = 'none';
            }
        });
    },
    
    selectOrigin: function(id, name) {
        document.getElementById('origin_display').value = name;
        document.getElementById('origin_text').value = name;
        document.getElementById('origin_id').value = id;
        $('#originModal').modal('hide');
        console.log(`🎯 원산지 선택: ${name} (ID: ${id})`);
    },
    
    addNewOrigin: function() {
        const searchValue = document.getElementById('origin-search').value;
        if (searchValue) {
            document.getElementById('origin_display').value = searchValue;
            document.getElementById('origin_text').value = searchValue;
            $('#originModal').modal('hide');
        } else {
            this.showAlert('info', '새 원산지 등록 기능은 추후 구현 예정입니다.');
        }
    },
    
    // ========================================
    // ✅ 기존 옵션 관리 함수들 수정 (addOption, removeOption 함수명 통일)
    // ========================================
    addOption: function() {
        this.addOptionRow();
    },
    
    removeOption: function(index) {
        // HTML에서 호출되는 함수이므로 유지
        if ($('#options-list .option-row').length <= 1) {
            this.showAlert('warning', '최소 1개의 옵션은 필요합니다.');
            return;
        }
        
        document.getElementById('option-' + index).remove();
        this.optionCount--;
        this.updateOptionNumbers();
        
        console.log(`🗑️ 옵션 행 삭제: ${this.optionCount}개`);
    },
    
    applyTemplate: function(type) {
        // HTML에서 호출되는 함수이므로 유지하되 기존 함수 활용
        this.applyQuickTemplate({target: {dataset: {template: type}}});
    },
    
    // ========================================
    // 🔧 탭 관리 (기존 코드 유지)
    // ========================================
    handleTabClick: function(e) {
        const tabType = $(e.target).data('tab');
        this.switchTab(tabType);
    },
    
    switchTab: function(tabType) {
        console.log(`🔄 탭 전환: ${tabType}`);
        
        this.currentTab = tabType;
        
        // 탭 버튼 상태 변경
        $('.register-tab').removeClass('active');
        $(`.register-tab[data-tab="${tabType}"]`).addClass('active');
        
        // 콘텐츠 영역 전환
        $('.tab-content').hide();
        $(`#${tabType}-register`).show();
        
        // 탭별 초기화
        if (tabType === 'manual') {
            this.initManualTab();
        } else if (tabType === 'excel') {
            this.initExcelTab();
        }
    },
    
    initManualTab: function() {
        console.log('📝 일반등록 탭 초기화');
        // 첫 번째 옵션 행이 없으면 추가
        if ($('#options-list .option-row').length === 0) {
            this.addOptionRow();
        }
    },
    
    initExcelTab: function() {
        console.log('📊 엑셀등록 탭 초기화');
        this.resetExcelForm();
    },
    
    // ========================================
    // 🔧 옵션 관리 (기존 코드 유지)
    // ========================================
    initializeOptions: function() {
        // 기본 옵션 행 1개 추가
        this.addOptionRow();
    },
    
    addOptionRow: function() {
        if (this.optionCount >= this.config.maxOptions) {
            this.showAlert('warning', `최대 ${this.config.maxOptions}개까지만 추가할 수 있습니다.`);
            return;
        }
        
        // ✅ HTML 템플릿과 맞추기 위해 수정
        const optionHtml = `
            <div class="row mb-2 option-row" id="option-${this.optionCount + 1}">
                <div class="col-md-6">
                    <input type="text" name="option_name[]" class="form-control option-name-input" placeholder="옵션명 입력 (예: BLACK-M)">
                </div>
                <div class="col-md-3">
                    <input type="number" name="option_stock[]" class="form-control option-stock-input" placeholder="재고" min="0" value="0">
                </div>
                <div class="col-md-3">
                    <button type="button" class="btn btn-danger btn-sm" onclick="ProductAdd.removeOption(${this.optionCount + 1})">
                        <i class="fas fa-trash"></i> 삭제
                    </button>
                </div>
            </div>
        `;
        
        $('#options-list').append(optionHtml);
        this.optionCount++;
        this.updateOptionNumbers();
        
        console.log(`✅ 옵션 행 추가: ${this.optionCount}개`);
    },
    
    removeOptionRow: function(e) {
        if ($('#options-list .option-row').length <= 1) {
            this.showAlert('warning', '최소 1개의 옵션은 필요합니다.');
            return;
        }
        
        $(e.target).closest('.option-row').remove();
        this.optionCount--;
        this.updateOptionNumbers();
        
        console.log(`🗑️ 옵션 행 삭제: ${this.optionCount}개`);
    },
    
    updateOptionNumbers: function() {
        $('#options-list .option-row').each(function(index) {
            $(this).find('.option-index').text(`#${index + 1}`);
            $(this).attr('data-index', index);
        });
    },
    
    // ========================================
    // 🔧 빠른 옵션 템플릿 (기존 코드 유지)
    // ========================================
    applyQuickTemplate: function(e) {
        const templateType = $(e.target).data('template');
        
        console.log(`🎯 빠른 템플릿 적용: ${templateType}`);
        
        // 기본 템플릿 (서버 요청 실패시 사용)
        const fallbackTemplates = {
            'clothing': ['XS', 'S', 'M', 'L', 'XL'],
            'shoes': ['220', '225', '230', '235', '240', '245', '250'],
            'color': ['BLACK', 'WHITE', 'NAVY', 'GRAY'],
            'onesize': ['FREE SIZE']
        };
        
        // 기존 옵션 초기화
        $('#options-list').empty();
        this.optionCount = 0;
        
        // 서버에서 템플릿 가져오기 시도
        $.get('/dashboard/products/quick-option-templates/', {
            type: templateType
        })
        .done((response) => {
            if (response.success) {
                response.template.forEach(option => {
                    this.addOptionRow();
                    const lastRow = $('#options-list .option-row:last');
                    lastRow.find('.option-name-input').val(option.name);
                    lastRow.find('.option-stock-input').val(option.stock);
                });
                
                this.showAlert('success', `${response.type_name} 템플릿이 적용되었습니다.`);
            }
        })
        .fail(() => {
            // 서버 요청 실패시 기본 템플릿 사용
            console.log('서버 템플릿 요청 실패, 기본 템플릿 사용');
            
            if (fallbackTemplates[templateType]) {
                fallbackTemplates[templateType].forEach(option => {
                    this.addOptionRow();
                    const lastRow = $('#options-list .option-row:last');
                    lastRow.find('.option-name-input').val(option);
                });
                
                this.showAlert('success', `${templateType} 템플릿이 적용되었습니다.`);
            } else {
                this.showAlert('error', '템플릿 로딩에 실패했습니다.');
            }
        });
    },
    
    // ========================================
    // 🔧 토글 선택 기능 (기존 코드 유지)
    // ========================================
    handleToggleClick: function(e) {
        const $item = $(e.currentTarget);
        const fieldName = $item.data('field');
        const value = $item.data('value');
        const text = $item.text().trim();
        
        // 토글 상태 변경
        $item.siblings().removeClass('active');
        $item.addClass('active');
        
        // 숨겨진 input에 값 저장
        $(`#${fieldName}_text`).val(text);
        $(`#${fieldName}_id`).val(value);
        
        console.log(`🎯 토글 선택: ${fieldName} = ${text} (${value})`);
    },
    
    // ========================================
    // 🔧 실시간 검증 (기존 코드 유지)
    // ========================================
    initializeValidation: function() {
        // 실시간 검증 설정
        this.validationRules = {
            'external_product_id': {
                required: true,
                minlength: 3,
                maxlength: 50
            },
            'product_name': {
                required: true,
                minlength: 2,
                maxlength: 100
            },
            'sku': {
                required: true,
                pattern: /^[A-Z0-9-_]+$/,
                minlength: 3,
                maxlength: 30
            }
        };
    },
    
    validateSKU: function(e) {
        const sku = $(e.target).val().trim();
        const $feedback = $(e.target).siblings('.validation-feedback');
        
        if (!sku) {
            this.showFieldError($(e.target), 'SKU는 필수입니다.');
            return;
        }
        
        if (!/^[A-Z0-9-_]+$/.test(sku)) {
            this.showFieldError($(e.target), 'SKU는 영문 대문자, 숫자, -, _ 만 사용 가능합니다.');
            return;
        }
        
        // 서버에서 중복 검사
        $.get('/dashboard/products/validate-sku/', { sku: sku })
        .done((response) => {
            if (response.valid) {
                this.showFieldSuccess($(e.target), response.message);
            } else {
                this.showFieldError($(e.target), response.message);
            }
        })
        .fail(() => {
            this.showFieldError($(e.target), 'SKU 검증 중 오류가 발생했습니다.');
        });
    },
    
    validateProductID: function(e) {
        const productId = $(e.target).val().trim();
        
        if (!productId) {
            this.showFieldError($(e.target), '고유상품ID는 필수입니다.');
            return;
        }
        
        if (productId.length < 3) {
            this.showFieldError($(e.target), '고유상품ID는 3자 이상이어야 합니다.');
            return;
        }
        
        this.showFieldSuccess($(e.target), '올바른 형식입니다.');
    },
    
    showFieldError: function($field, message) {
        $field.removeClass('is-valid').addClass('is-invalid');
        $field.siblings('.invalid-feedback').remove();
        $field.after(`<div class="invalid-feedback">${message}</div>`);
    },
    
    showFieldSuccess: function($field, message) {
        $field.removeClass('is-invalid').addClass('is-valid');
        $field.siblings('.valid-feedback').remove();
        $field.siblings('.invalid-feedback').remove();
        $field.after(`<div class="valid-feedback">${message}</div>`);
    },
    
    // ========================================
    // 🔧 이미지 업로드 (기존 코드 유지)
    // ========================================
    setupImagePreview: function() {
        // 이미지 미리보기 초기화
        for (let i = 1; i <= this.config.maxImages; i++) {
            this.createImageUploadArea(i);
        }
    },
    
    createImageUploadArea: function(index) {
        const $container = $(`#image-upload-${index}`);
        if ($container.length === 0) return;
        
        $container.html(`
            <div class="image-upload-area" data-index="${index}">
                <input type="file" 
                       id="image_file_${index}" 
                       name="image_file_${index}" 
                       class="image-input d-none" 
                       accept="image/*">
                <div class="upload-placeholder" onclick="$('#image_file_${index}').click()">
                    <i class="fas fa-camera fa-2x text-muted"></i>
                    <p class="mt-2 text-muted">이미지 ${index}</p>
                    <small class="text-muted">클릭하여 업로드</small>
                </div>
                <div class="image-preview d-none">
                    <img src="" alt="미리보기" class="preview-image">
                    <div class="image-actions">
                        <button type="button" class="btn btn-sm btn-danger remove-image-btn">삭제</button>
                    </div>
                </div>
            </div>
        `);
    },
    
    handleImageUpload: function(e) {
        const file = e.target.files[0];
        const index = $(e.target).data('index') || $(e.target).attr('id').split('_').pop();
        const $container = $(e.target).closest('.image-upload-area');
        
        if (!file) return;
        
        // 파일 검증
        if (!this.validateImageFile(file)) {
            $(e.target).val(''); // 파일 선택 취소
            return;
        }
        
        // 미리보기 생성
        const reader = new FileReader();
        reader.onload = (e) => {
            $container.find('.upload-placeholder').hide();
            $container.find('.preview-image').attr('src', e.target.result);
            $container.find('.image-preview').show();
        };
        reader.readAsDataURL(file);
        
        console.log(`📷 이미지 ${index} 업로드: ${file.name}`);
    },
    
    validateImageFile: function(file) {
        // 파일 크기 검사
        if (file.size > this.config.maxFileSize) {
            this.showAlert('error', '이미지 크기는 5MB 이하여야 합니다.');
            return false;
        }
        
        // 파일 형식 검사
        if (!this.config.allowedImageTypes.includes(file.type)) {
            this.showAlert('error', '지원하지 않는 이미지 형식입니다. (JPEG, PNG, WEBP만 가능)');
            return false;
        }
        
        return true;
    },
    
    // ========================================
    // 🔧 폼 검증 및 제출 (기존 코드 유지)
    // ========================================
    validateForm: function(e) {
        console.log('🔍 폼 검증 시작');
        
        let isValid = true;
        const errors = [];
        
        // 필수 필드 검증
        const requiredFields = ['external_product_id', 'product_name', 'sku'];
        requiredFields.forEach(field => {
            const value = $(`#${field}`).val().trim();
            if (!value) {
                errors.push(`${field}는 필수 입력 항목입니다.`);
                isValid = false;
            }
        });
        
        // 옵션 검증
        const optionValidation = this.validateOptions();
        if (!optionValidation.valid) {
            errors.push(...optionValidation.errors);
            isValid = false;
        }
        
        // 검증 실패시 제출 중단
        if (!isValid) {
            e.preventDefault();
            this.showAlert('error', '입력 정보를 확인해주세요:\n' + errors.join('\n'));
            return false;
        }
        
        // 제출 전 로딩 표시
        this.showLoadingState();
        return true;
    },
    
    validateOptions: function() {
        const optionNames = [];
        const errors = [];
        let hasValidOption = false;
        
        $('#options-list .option-row').each(function() {
            const name = $(this).find('.option-name-input').val().trim();
            const stock = $(this).find('.option-stock-input').val();
            
            if (name) {
                hasValidOption = true;
                
                // 중복 옵션명 검사
                if (optionNames.includes(name)) {
                    errors.push(`중복된 옵션명: ${name}`);
                } else {
                    optionNames.push(name);
                }
                
                // 재고 검사
                if (stock < 0) {
                    errors.push(`재고는 음수일 수 없습니다: ${name}`);
                }
            }
        });
        
        if (!hasValidOption) {
            errors.push('최소 1개 이상의 옵션을 입력해주세요.');
        }
        
        return {
            valid: errors.length === 0,
            errors: errors
        };
    },
    
    // ========================================
    // 🔧 미리보기 기능 (기존 코드 유지)
    // ========================================
    showPreview: function() {
        console.log('👀 상품 미리보기 요청');
        
        const formData = new FormData($('#product-form')[0]);
        
        $.ajax({
            url: '/dashboard/products/preview/',
            type: 'POST',
            data: formData,
            processData: false,
            contentType: false,
            success: (response) => {
                if (response.success) {
                    this.displayPreview(response.preview);
                } else {
                    this.showAlert('error', response.message);
                }
            },
            error: () => {
                this.showAlert('error', '미리보기 생성 중 오류가 발생했습니다.');
            }
        });
    },
    
    displayPreview: function(previewData) {
        const previewHtml = `
            <div class="preview-content">
                <h5>상품 정보 미리보기</h5>
                <div class="row">
                    <div class="col-md-6">
                        <p><strong>고유상품ID:</strong> ${previewData.external_product_id}</p>
                        <p><strong>상품명:</strong> ${previewData.product_name}</p>
                        <p><strong>SKU:</strong> ${previewData.sku}</p>
                        <p><strong>브랜드:</strong> ${previewData.brand_name}</p>
                        <p><strong>부띠끄:</strong> ${previewData.retailer}</p>
                    </div>
                    <div class="col-md-6">
                        <p><strong>소비자가:</strong> €${previewData.price_retail}</p>
                        <p><strong>COST:</strong> €${previewData.price_org}</p>
                        <p><strong>총 재고:</strong> ${previewData.total_stock}개</p>
                    </div>
                </div>
                <div class="options-preview">
                    <h6>옵션 정보</h6>
                    <div class="row">
                        ${previewData.options.map(option => 
                            `<div class="col-md-3 mb-2">
                                <div class="card card-sm">
                                    <div class="card-body p-2">
                                        <strong>${option.name}</strong><br>
                                        <small class="text-muted">재고: ${option.stock}개</small>
                                    </div>
                                </div>
                            </div>`
                        ).join('')}
                    </div>
                </div>
            </div>
        `;
        
        // 모달로 표시
        $('#preview-modal .modal-body').html(previewHtml);
        $('#preview-modal').modal('show');
    },
    
    // ========================================
    // 🔧 엑셀 업로드 (기존 코드 유지)
    // ========================================
    handleExcelUpload: function(e) {
        const file = e.target.files[0];
        if (!file) return;
        
        // 파일 형식 검증
        const allowedTypes = [
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'application/vnd.ms-excel'
        ];
        
        if (!allowedTypes.includes(file.type)) {
            this.showAlert('error', 'Excel 파일만 업로드 가능합니다. (.xlsx, .xls)');
            $(e.target).val('');
            return;
        }
        
        // 파일 크기 검증 (10MB)
        if (file.size > 10 * 1024 * 1024) {
            this.showAlert('error', '파일 크기는 10MB 이하여야 합니다.');
            $(e.target).val('');
            return;
        }
        
        // 파일 정보 표시
        $('#excel-file-info').html(`
            <div class="alert alert-info">
                <i class="fas fa-file-excel"></i> 
                선택된 파일: <strong>${file.name}</strong> 
                (${this.formatFileSize(file.size)})
            </div>
        `);
        
        console.log(`📊 엑셀 파일 선택: ${file.name}`);
    },
    
    downloadTemplate: function() {
        console.log('📥 엑셀 템플릿 다운로드');
        window.location.href = '/dashboard/products/excel-template/';
    },
    
    resetExcelForm: function() {
        $('#excel-file').val('');
        $('#excel-file-info').empty();
    },
    
    // ========================================
    // 🔧 유틸리티 함수 (기존 코드 유지)
    // ========================================
    showAlert: function(type, message) {
        const alertClass = {
            'success': 'alert-success',
            'error': 'alert-danger', 
            'warning': 'alert-warning',
            'info': 'alert-info'
        }[type] || 'alert-info';
        
        const alertHtml = `
            <div class="alert ${alertClass} alert-dismissible fade show" role="alert">
                <i class="fas fa-${type === 'success' ? 'check' : type === 'error' ? 'times' : 'info'}-circle"></i>
                ${message.replace(/\n/g, '<br>')}
                <button type="button" class="close" data-dismiss="alert">
                    <span>&times;</span>
                </button>
            </div>
        `;
        
        $('#alert-container').html(alertHtml);
        
        // 5초 후 자동 제거
        setTimeout(() => {
            $('#alert-container .alert').fadeOut();
        }, 5000);
    },
    
    showLoadingState: function() {
        $('#submit-btn').prop('disabled', true).html(
            '<i class="fas fa-spinner fa-spin"></i> 등록 중...'
        );
    },
    
    formatFileSize: function(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
};

// ========================================
// ✅ 글로벌 함수들 (HTML에서 직접 호출되는 함수들) - 기존 HTML 구조 유지
// ========================================

// 부띠끄 관련 (기존 함수명 유지)
function openRetailerModal() {
    $('#retailerModal').modal('show');
    $('#retailer-search').focus();
}

function filterRetailers() {
    const searchValue = document.getElementById('retailer-search').value.toLowerCase();
    const items = document.querySelectorAll('.retailer-item');

    items.forEach(item => {
        const text = item.textContent.toLowerCase();
        if (text.includes(searchValue)) {
            item.style.display = 'block';
        } else {
            item.style.display = 'none';
        }
    });
}

function selectRetailer(id, name) {
    document.getElementById('retailer_display').value = name;
    document.getElementById('retailer_text').value = name;
    document.getElementById('retailer_id').value = id;
    $('#retailerModal').modal('hide');
    console.log(`🎯 부띠끄 선택: ${name} (ID: ${id})`);
}

// 브랜드 관련 (기존 함수명 유지)
function openBrandModal() {
    $('#brandModal').modal('show');
    $('#brand-search').focus();
}

function filterBrands() {
    const searchValue = document.getElementById('brand-search').value.toLowerCase();
    const items = document.querySelectorAll('.brand-item');

    items.forEach(item => {
        const text = item.textContent.toLowerCase();
        if (text.includes(searchValue)) {
            item.style.display = 'block';
        } else {
            item.style.display = 'none';
        }
    });
}

function selectBrand(id, name) {
    document.getElementById('brand_display').value = name;
    document.getElementById('brand_name_text').value = name;
    document.getElementById('brand_name_id').value = id;
    $('#brandModal').modal('hide');
    console.log(`🎯 브랜드 선택: ${name} (ID: ${id})`);
}

function addNewBrand() {
    const searchValue = document.getElementById('brand-search').value;
    if (searchValue) {
        document.getElementById('brand_display').value = searchValue;
        document.getElementById('brand_name_text').value = searchValue;
        $('#brandModal').modal('hide');
    } else {
        alert('새 브랜드 등록 기능은 추후 구현 예정입니다.');
    }
}

// 성별 관련 (기존 함수명 유지)
function openGenderModal() {
    $('#genderModal').modal('show');
    $('#gender-search').focus();
}

function filterGenders() {
    const searchValue = document.getElementById('gender-search').value.toLowerCase();
    const items = document.querySelectorAll('.gender-item');

    items.forEach(item => {
        const text = item.textContent.toLowerCase();
        if (text.includes(searchValue)) {
            item.style.display = 'block';
        } else {
            item.style.display = 'none';
        }
    });
}

function selectGenderFromModal(id, name) {
    document.getElementById('gender_display').value = name;
    document.getElementById('gender_text').value = name;
    document.getElementById('gender_id').value = id;
    $('#genderModal').modal('hide');
    console.log(`🎯 성별 선택: ${name} (ID: ${id})`);
}

// 카테고리1 관련 (기존 함수명 유지)
function openCategory1Modal() {
    $('#category1Modal').modal('show');
    $('#category1-search').focus();
}

function filterCategory1() {
    const searchValue = document.getElementById('category1-search').value.toLowerCase();
    const items = document.querySelectorAll('.category1-item');

    items.forEach(item => {
        const text = item.textContent.toLowerCase();
        if (text.includes(searchValue)) {
            item.style.display = 'block';
        } else {
            item.style.display = 'none';
        }
    });
}

function selectCategory1(id, name) {
    document.getElementById('category1_display').value = name;
    document.getElementById('category1_text').value = name;
    document.getElementById('category1_id').value = id;
    $('#category1Modal').modal('hide');
    console.log(`🎯 카테고리1 선택: ${name} (ID: ${id})`);
}

// 카테고리2 관련 (기존 함수명 유지)
function openCategory2Modal() {
    $('#category2Modal').modal('show');
    $('#category2-search').focus();
}

function filterCategory2() {
    const searchValue = document.getElementById('category2-search').value.toLowerCase();
    const items = document.querySelectorAll('.category2-item');

    items.forEach(item => {
        const text = item.textContent.toLowerCase();
        if (text.includes(searchValue)) {
            item.style.display = 'block';
        } else {
            item.style.display = 'none';
        }
    });
}

function selectCategory2(id, name) {
    document.getElementById('category2_display').value = name;
    document.getElementById('category2_text').value = name;
    document.getElementById('category2_id').value = id;
    $('#category2Modal').modal('hide');
    console.log(`🎯 카테고리2 선택: ${name} (ID: ${id})`);
}

// 원산지 관련 (기존 함수명 유지)
function openOriginModal() {
    $('#originModal').modal('show');
    $('#origin-search').focus();
}

function filterOrigins() {
    const searchValue = document.getElementById('origin-search').value.toLowerCase();
    const items = document.querySelectorAll('.origin-item');

    items.forEach(item => {
        const text = item.textContent.toLowerCase();
        if (text.includes(searchValue)) {
            item.style.display = 'block';
        } else {
            item.style.display = 'none';
        }
    });
}

function selectOrigin(id, name) {
    document.getElementById('origin_display').value = name;
    document.getElementById('origin_text').value = name;
    document.getElementById('origin_id').value = id;
    $('#originModal').modal('hide');
    console.log(`🎯 원산지 선택: ${name} (ID: ${id})`);
}

function addNewOrigin() {
    const searchValue = document.getElementById('origin-search').value;
    if (searchValue) {
        document.getElementById('origin_display').value = searchValue;
        document.getElementById('origin_text').value = searchValue;
        $('#originModal').modal('hide');
    } else {
        alert('새 원산지 등록 기능은 추후 구현 예정입니다.');
    }
}

// 옵션 관련 (기존 함수명 유지)
function addOption() {
    ProductAdd.addOption();
}

function removeOption(index) {
    ProductAdd.removeOption(index);
}

function applyTemplate(type) {
    ProductAdd.applyTemplate(type);
}