/**
 * 쿠폰 생성/수정 폼 JavaScript (교체본)
 * 경로: dashboard/static/dashboard/js/promotion/coupon_form.js
 */

$(document).ready(function () {
  CouponForm.init();
});

const CouponForm = {
  // ✅ 서버가 내려준 수정모드 플래그(없으면 URL로 보조판단)
  isEditMode: !!(window.IS_COUPON_EDIT || /\/edit\/?$/.test(window.location.pathname)),
  originalCode: '',

  init: function () {
    // 원본 코드 저장
    this.originalCode = $('#id_code').val() || '';
    this.bindEvents();
    this.updatePreview();
    this.toggleConditionalFields();
    this.toggleCodeField(); // 초기 자동생성 체크 상태 반영
  },

  bindEvents: function () {
    $('#id_name').on('input', this.updatePreview);
    $('#id_code').on('input', this.updatePreview);
    $('#id_discount_type').on('change', this.updatePreview);
    $('#id_discount_value').on('input', this.updatePreview);
    $('#id_min_purchase_amount').on('input', this.updatePreview);

    $('#id_discount_type').on('change', this.toggleConditionalFields);

    $('#generate-code').on('click', this.generateCode);
    $('#id_auto_generate_code').on('change', this.toggleCodeField);

    $('#coupon-form').on('submit', this.validateForm);

    $('#id_code').on('input', function () { this.value = this.value.toUpperCase(); });
    $('input[type="number"]').on('input', this.validateNumberInput);
  },

  updatePreview: function () {
    const code = $('#id_code').val() || 'SAMPLE123';
    $('#preview-code').text(code);

    const name = $('#id_name').val() || '샘플 쿠폰';
    $('#preview-name').text(name);

    const type = $('#id_discount_type').val();
    const value = $('#id_discount_value').val() || '10';
    if (type === 'fixed') {
      $('#discount-amount').text(parseInt(value).toLocaleString());
      $('#discount-unit').text('원');
    } else {
      $('#discount-amount').text(value);
      $('#discount-unit').text('%');
    }

    const minAmount = $('#id_min_purchase_amount').val() || '0';
    $('#min-amount').text(parseInt(minAmount).toLocaleString());
  },

  toggleConditionalFields: function () {
    const type = $('#id_discount_type').val();
    const $value = $('#id_discount_value');

    if (type === 'percent') {
      $('#id_max_discount_amount').closest('.form-group').show();
      $value.attr({ placeholder: '할인율 (%)', max: '100', step: '0.1' });
    } else {
      $('#id_max_discount_amount').closest('.form-group').hide();
      $('#id_max_discount_amount').val('');
      $value.attr({ placeholder: '할인금액 (원)', step: '1' }).removeAttr('max');
    }
    CouponForm.updatePreview();
  },

  generateCode: function () {
    const length = 8;
    const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';
    let code = '';
    for (let i = 0; i < length; i++) code += chars.charAt(Math.floor(Math.random() * chars.length));
    $('#id_code').val(code).removeClass('is-invalid').siblings('.invalid-feedback').remove();
    CouponForm.updatePreview();
  },

  // ✅ 핵심: 자동생성 체크 토글 시 동작 분기
  toggleCodeField: function () {
    const isAuto = $('#id_auto_generate_code').prop('checked');

    if (CouponForm.isEditMode) {
      // 수정 모드: 항상 기존 코드 유지
      $('#id_code').prop('readonly', false).val(CouponForm.originalCode)
        .attr('placeholder', '기존 코드 유지 (수정 가능)');
      if (isAuto) {
        // 사용자가 실수로 체크하면 해제시키고 안내
        $('#id_auto_generate_code').prop('checked', false);
        CouponForm.showAlert('info', '수정 모드에서는 기존 코드가 유지됩니다.');
      }
    } else {
      // 생성 모드
      if (isAuto) {
        $('#id_code').prop('readonly', true).val('').attr('placeholder', '자동 생성됩니다');
      } else {
        $('#id_code').prop('readonly', false).val('')
          .attr('placeholder', '쿠폰 코드 (영문 대문자, 숫자 조합)');
      }
    }

    $('#id_code').removeClass('is-invalid').siblings('.invalid-feedback').remove();
    CouponForm.updatePreview();
  },

  validateForm: function (e) {
    let isValid = true;
    const errors = [];

    const name = $('#id_name').val().trim();
    const code = $('#id_code').val().trim();
    const isAuto = $('#id_auto_generate_code').prop('checked');
    const discountValue = parseFloat($('#id_discount_value').val());
    const startDate = new Date($('#id_start_date').val());
    const endDate = new Date($('#id_end_date').val());
    const type = $('#id_discount_type').val();

    if (!name) { errors.push('쿠폰명을 입력해주세요.'); isValid = false; }

    if (!isAuto) {
      if (!code) { errors.push('쿠폰 코드를 입력하거나 자동 생성을 선택해주세요.'); isValid = false; }
      else if (!/^[A-Z0-9]{4,20}$/.test(code)) {
        errors.push('쿠폰 코드는 영문 대문자와 숫자만 사용 가능합니다 (4-20자).'); isValid = false;
      }
    } else if (!CouponForm.isEditMode) {
      // 생성 모드 + 자동생성: 서버가 생성하므로 비워둠
      $('#id_code').val('');
    }

    if (!discountValue || discountValue <= 0) { errors.push('유효한 할인 값을 입력해주세요.'); isValid = false; }
    if (type === 'percent' && discountValue > 100) { errors.push('정률할인은 100%를 초과할 수 없습니다.'); isValid = false; }
    if (startDate >= endDate) { errors.push('종료일시는 시작일시보다 늦어야 합니다.'); isValid = false; }

    if (!isValid) {
      e.preventDefault();
      CouponForm.showErrors(errors);
    }
    return isValid;
  },

  validateNumberInput: function (e) {
    const $input = $(e.target);
    const value = parseFloat($input.val());
    if (value < 0) $input.val(0);
    if ($input.attr('name') === 'discount_value' && $('#id_discount_type').val() === 'percent') {
      if (value > 100) { $input.val(100); CouponForm.showAlert('warning', '할인율은 100%를 초과할 수 없습니다.'); }
    }
    CouponForm.updatePreview();
  },

  showErrors: function (errors) {
    let msg = '다음 사항을 확인해주세요:\n\n';
    errors.forEach((e, i) => { msg += `${i + 1}. ${e}\n`; });
    alert(msg);
  },

  showAlert: function (type, message) {
    const cls = type === 'success' ? 'alert-success'
      : type === 'warning' ? 'alert-warning'
      : type === 'info' ? 'alert-info' : 'alert-danger';
    const $el = $(`
      <div class="alert ${cls} alert-dismissible fade show position-fixed"
           style="top:20px; right:20px; z-index:9999; max-width:300px;">
        ${message}
        <button type="button" class="close" data-dismiss="alert"><span>&times;</span></button>
      </div>
    `);
    $('body').append($el); setTimeout(() => $el.alert('close'), 4000);
  }
};

// 전역 노출(디버깅/확장용)
window.CouponForm = CouponForm;
