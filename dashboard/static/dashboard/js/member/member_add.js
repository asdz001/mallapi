
/**
 * ========================================
 * 📁 파일 위치: dashboard/static/dashboard/js/member/member_add.js
 * 🎯 목적: 회원 추가 페이지 전용 기능
 * 📅 버전: 1.0
 * 🔄 의존성: search_engine.js, jQuery, AdminLTE(로컬), Bootstrap(로컬)
 * ========================================
 */
/**
 * 회원 추가 화면 UX 보강 스크립트
 * - 비밀번호 눈 아이콘 토글
 * - Bootstrap 4/5 상관없이 탭 전환 지원
 * - B2B 선택 시 B2B 탭 자동 전환
 * - 제출 시 탭별 필수 검증 & 자동 이동
 * - 저장 중 중복 제출 방지 + 스피너
 * - 휴대폰 자동 하이픈, 비밀번호 강도 힌트
 */
(function () {
  const form = document.getElementById("member-add-form");
  const memberTypeSelect = document.getElementById("id_member_type");
  const phoneInput = document.getElementById("id_phone");
  const pw1 = document.getElementById("id_password1");
  const pw2 = document.getElementById("id_password2");
  const pwHint = document.getElementById("pw-hint");

  // ===== 탭 전환 (부트스트랩 없이도 동작) =====
  function showTab(href) {
    const target = document.querySelector(href);
    if (!target) return;
    document.querySelectorAll('.nav-tabs .nav-link').forEach(a => a.classList.remove('active'));
    document.querySelectorAll('.tab-pane').forEach(p => { p.classList.remove('active'); p.classList.remove('show'); });
    const link = document.querySelector(`.nav-tabs .nav-link[href="${href}"]`);
    if (link) link.classList.add('active');
    target.classList.add('active', 'show');
  }
  document.addEventListener('click', function (e) {
    const a = e.target.closest('.nav-tabs .nav-link');
    if (!a) return;
    const href = a.getAttribute('href');
    if (!href || !href.startsWith('#')) return;
    e.preventDefault();
    showTab(href);
  });

  // ===== B2B 선택 시 탭 전환/강조 =====
  function onMemberTypeChange() {
    const v = memberTypeSelect ? memberTypeSelect.value : '';
    const b2bHref = '#tab-b2b';
    const b2bLink = document.querySelector(`.nav-tabs .nav-link[href="${b2bHref}"]`);
    if (v === 'B2B') {
      if (b2bLink) b2bLink.classList.add('text-primary', 'font-weight-bold');
      showTab(b2bHref);
    } else {
      if (b2bLink) b2bLink.classList.remove('text-primary', 'font-weight-bold');
    }
  }

  // ===== 비밀번호 눈 아이콘 토글 =====
  function attachPwToggles() {
    document.querySelectorAll('.pw-toggle').forEach(btn => {
      btn.addEventListener('click', () => {
        const targetSel = btn.getAttribute('data-target');
        const input = document.querySelector(targetSel);
        if (!input) return;
        input.type = (input.type === 'password') ? 'text' : 'password';
        const icon = btn.querySelector('i');
        if (icon) { icon.classList.toggle('fa-eye'); icon.classList.toggle('fa-eye-slash'); }
      });
    });
  }

  // ===== 휴대폰 자동 하이픈 =====
  function autoHyphenPhone(str) {
    const d = (str || '').replace(/[^0-9]/g, '');
    if (d.length < 4) return d;
    if (d.length < 7) return `${d.slice(0,3)}-${d.slice(3)}`;
    return `${d.slice(0,3)}-${d.slice(3,7)}-${d.slice(7,11)}`;
  }

  // ===== 비밀번호 강도 힌트(간단) =====
  function passwordStrength(pw) {
    let s = 0;
    if ((pw || '').length >= 8) s++;
    if (/[A-Z]/.test(pw)) s++;
    if (/[0-9]/.test(pw)) s++;
    if (/[!@#$%^&*]/.test(pw)) s++;
    return ['약함','보통','좋음','강함'][Math.max(0, s-1)];
  }

  // ===== 제출 시 탭별 검증 + 중복 제출 방지 =====
  function validateOnSubmit(e) {
    const requiredBasic = [
      ['#id_username', '#tab-basic'],
      ['#id_password1', '#tab-basic'],
      ['#id_password2', '#tab-basic'],
      ['#id_name', '#tab-basic'],
      ['#id_member_type', '#tab-basic'],
    ];
    for (const [sel, href] of requiredBasic) {
      const el = document.querySelector(sel);
      if (el && !String(el.value || '').trim()) {
        e.preventDefault(); showTab(href); el.focus(); alert('필수 항목을 입력해 주세요.');
        return;
      }
    }
    if (memberTypeSelect && memberTypeSelect.value === 'B2B') {
      const company = document.querySelector('#id_company_name');
      const bizno = document.querySelector('#id_business_number');
      if ((company && !company.value.trim()) || (bizno && !bizno.value.trim())) {
        e.preventDefault(); showTab('#tab-b2b'); (company && !company.value.trim() ? company : bizno).focus();
        alert('B2B 회원은 회사명과 사업자등록번호가 필요합니다.');
        return;
      }
    }
    const btn = form.querySelector('button[type="submit"]');
    if (btn) {
      if (btn.dataset.submitted === '1') { e.preventDefault(); return; }
      btn.dataset.submitted = '1';
      btn.disabled = true;
      btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 저장 중...';
    }
  }

  document.addEventListener('DOMContentLoaded', function () {
    showTab('#tab-basic');
    onMemberTypeChange();
    if (memberTypeSelect) memberTypeSelect.addEventListener('change', onMemberTypeChange);

    if (phoneInput) phoneInput.addEventListener('input', e => e.target.value = autoHyphenPhone(e.target.value));

    if (pw1 && pwHint) pw1.addEventListener('input', () => pwHint.textContent = '비밀번호 강도: ' + passwordStrength(pw1.value));

    attachPwToggles();

    if (form) form.addEventListener('submit', validateOnSubmit);
  });
})();
