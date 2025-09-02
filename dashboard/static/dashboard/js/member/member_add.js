/**
 * ========================================
 * 📁 파일 위치: dashboard/static/dashboard/js/member/member_add.js
 * 🎯 목적: 회원 추가 페이지 전용 기능 - 등급 선택 동적 필터링 추가
 * 📅 버전: 2.0 (등급 관리 기능 추가)
 * 🔄 의존성: search_engine.js, jQuery, AdminLTE(로컬), Bootstrap(로컬)
 * ========================================
 */

/**
 * 회원 추가 화면 UX 보강 스크립트
 * - 비밀번호 눈 아이콘 토글
 * - Bootstrap 4/5 상관없이 탭 전환 지원
 * - B2B 선택 시 B2B 탭 자동 전환
 * - ✅ 회원 타입별 등급 동적 필터링
 * - 제출 시 탭별 필수 검증 & 자동 이동
 * - 저장 중 중복 제출 방지 + 스피너
 * - 휴대폰 자동 하이픈, 비밀번호 강도 힌트
 */
(function () {
  const form = document.getElementById("member-add-form");
  const memberTypeSelect = document.getElementById("id_member_type");
  const gradeSelect = document.getElementById("id_grade");  // ✅ 등급 선택
  const phoneInput = document.getElementById("id_phone");
  const pw1 = document.getElementById("id_password1");
  const pw2 = document.getElementById("id_password2");
  const pwHint = document.getElementById("pw-hint");

  // ✅ 전체 등급 데이터 (Django에서 전달받음)
  let allGrades = [];
  
  // Django context에서 등급 데이터 가져오기
  if (typeof window.gradesData !== 'undefined') {
    allGrades = window.gradesData;
  }

  // ===== 초기화 =====
  function init() {
    console.log('회원 추가 페이지 초기화');
    
    // 이벤트 바인딩
    bindEvents();
    
    // 초기 등급 필터링
    if (memberTypeSelect && memberTypeSelect.value) {
      filterGradesByMemberType(memberTypeSelect.value);
    }
    
    // 초기 탭 상태 설정
    onMemberTypeChange();
  }

  // ===== 이벤트 바인딩 =====
  function bindEvents() {
    // 회원 타입 변경 시 등급 필터링
    if (memberTypeSelect) {
      memberTypeSelect.addEventListener('change', function() {
        const memberType = this.value;
        filterGradesByMemberType(memberType);
        onMemberTypeChange();
      });
    }

    // 탭 전환 이벤트
    document.addEventListener('click', function (e) {
      const a = e.target.closest('.nav-tabs .nav-link');
      if (!a) return;
      const href = a.getAttribute('href');
      if (!href || !href.startsWith('#')) return;
      e.preventDefault();
      showTab(href);
    });

    // 비밀번호 토글 이벤트
    attachPwToggles();

    // 전화번호 자동 포맷팅
    if (phoneInput) {
      phoneInput.addEventListener('input', formatPhoneNumber);
    }

    // 비밀번호 강도 체크
    if (pw1) {
      pw1.addEventListener('input', checkPasswordStrength);
    }

    // 폼 제출 검증
    if (form) {
      form.addEventListener('submit', validateAndSubmit);
    }
  }

  // ✅ 회원 타입별 등급 필터링
  function filterGradesByMemberType(memberType) {
    if (!gradeSelect || !allGrades.length) return;

    console.log(`등급 필터링: ${memberType}`, allGrades);

    // 기존 옵션 제거 (첫 번째 기본 옵션 제외)
    while (gradeSelect.children.length > 1) {
      gradeSelect.removeChild(gradeSelect.lastChild);
    }

    if (!memberType) {
      // 회원 타입이 선택되지 않았으면 모든 등급 표시
      allGrades.forEach(grade => {
        const option = document.createElement('option');
        option.value = grade.id;
        option.textContent = `[${grade.member_type}] ${grade.name}${grade.is_default ? ' (기본)' : ''}`;
        gradeSelect.appendChild(option);
      });
      return;
    }

    // 선택된 회원 타입에 맞는 등급들만 필터링
    const filteredGrades = allGrades.filter(grade => 
      grade.member_type === memberType || grade.member_type === 'ALL'
    );

    // 필터된 등급들을 옵션으로 추가
    filteredGrades.forEach(grade => {
      const option = document.createElement('option');
      option.value = grade.id;
      option.textContent = `${grade.name}${grade.is_default ? ' (기본)' : ''}`;
      
      // 기본 등급이면 자동 선택
      if (grade.is_default && grade.member_type === memberType) {
        option.selected = true;
      }
      
      gradeSelect.appendChild(option);
    });

    console.log(`${memberType} 타입의 등급 ${filteredGrades.length}개 로드됨`);
  }

  // ===== 탭 전환 (부트스트랩 없이도 동작) =====
  function showTab(href) {
    const target = document.querySelector(href);
    if (!target) return;
    
    document.querySelectorAll('.nav-tabs .nav-link').forEach(a => a.classList.remove('active'));
    document.querySelectorAll('.tab-pane').forEach(p => { 
      p.classList.remove('active'); 
      p.classList.remove('show'); 
    });
    
    const link = document.querySelector(`.nav-tabs .nav-link[href="${href}"]`);
    if (link) link.classList.add('active');
    target.classList.add('active', 'show');
  }

  // ===== B2B 선택 시 탭 전환/강조 =====
  function onMemberTypeChange() {
    if (!memberTypeSelect) return;
    
    const memberType = memberTypeSelect.value;
    const b2bHref = '#tab-b2b';
    const b2bLink = document.querySelector(`.nav-tabs .nav-link[href="${b2bHref}"]`);
    
    if (memberType === 'B2B') {
      if (b2bLink) {
        b2bLink.classList.add('text-primary', 'font-weight-bold');
      }
      showTab(b2bHref);
    } else {
      if (b2bLink) {
        b2bLink.classList.remove('text-primary', 'font-weight-bold');
      }
    }
  }

  // ===== 비밀번호 눈 아이콘 토글 =====
  function attachPwToggles() {
    document.querySelectorAll('.pw-toggle').forEach(btn => {
      btn.addEventListener('click', () => {
        const targetSel = btn.getAttribute('data-target');
        const input = document.querySelector(targetSel);
        if (!input) return;
        
        const isPassword = input.type === 'password';
        input.type = isPassword ? 'text' : 'password';
        
        const icon = btn.querySelector('i');
        if (icon) {
          icon.className = isPassword ? 'fas fa-eye-slash' : 'fas fa-eye';
        }
      });
    });
  }

  // ===== 전화번호 자동 포맷팅 =====
  function formatPhoneNumber(e) {
    let value = e.target.value.replace(/\D/g, '');
    if (value.length >= 11) {
      value = value.slice(0, 11);
      e.target.value = `${value.slice(0, 3)}-${value.slice(3, 7)}-${value.slice(7)}`;
    } else if (value.length >= 7) {
      e.target.value = `${value.slice(0, 3)}-${value.slice(3, 6)}-${value.slice(6)}`;
    } else if (value.length >= 4) {
      e.target.value = `${value.slice(0, 3)}-${value.slice(3)}`;
    } else {
      e.target.value = value;
    }
  }

  // ===== 비밀번호 강도 체크 =====
  function checkPasswordStrength(e) {
    if (!pwHint) return;
    
    const pw = e.target.value;
    let strength = 0;
    let messages = [];

    if (pw.length >= 8) strength++;
    else messages.push('8자 이상');

    if (/[a-z]/.test(pw) && /[A-Z]/.test(pw)) strength++;
    else messages.push('대소문자 조합');

    if (/\d/.test(pw)) strength++;
    else messages.push('숫자 포함');

    if (/[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(pw)) strength++;
    else messages.push('특수문자 포함');

    const colors = ['danger', 'warning', 'info', 'success'];
    const texts = ['매우 약함', '약함', '보통', '강함'];
    
    pwHint.className = `small text-${colors[Math.min(strength, 3)]}`;
    
    if (pw.length === 0) {
      pwHint.textContent = '';
    } else if (strength >= 3) {
      pwHint.textContent = `✓ ${texts[strength]}`;
    } else {
      pwHint.textContent = `${texts[strength]} (${messages.join(', ')} 필요)`;
    }
  }

  // ===== 폼 제출 검증 =====
  function validateAndSubmit(e) {
    if (!form) return;

    // 기본 검증
    const memberType = memberTypeSelect ? memberTypeSelect.value : '';
    const name = form.querySelector('#id_name')?.value.trim();
    const email = form.querySelector('#id_email')?.value.trim();
    const password1 = pw1 ? pw1.value : '';
    const password2 = pw2 ? pw2.value : '';

    // 필수 항목 검증
    if (!memberType) {
      e.preventDefault();
      alert('회원 유형을 선택해주세요.');
      showTab('#tab-basic');
      memberTypeSelect?.focus();
      return;
    }

    if (!name) {
      e.preventDefault();
      alert('이름을 입력해주세요.');
      showTab('#tab-basic');
      form.querySelector('#id_name')?.focus();
      return;
    }

    if (!email) {
      e.preventDefault();
      alert('이메일을 입력해주세요.');
      showTab('#tab-basic');
      form.querySelector('#id_email')?.focus();
      return;
    }

    if (!password1 || password1.length < 8) {
      e.preventDefault();
      alert('비밀번호는 8자 이상 입력해주세요.');
      showTab('#tab-basic');
      pw1?.focus();
      return;
    }

    if (password1 !== password2) {
      e.preventDefault();
      alert('비밀번호가 일치하지 않습니다.');
      showTab('#tab-basic');
      pw2?.focus();
      return;
    }

    // B2B 필수 항목 검증
    if (memberType === 'B2B') {
      const companyName = form.querySelector('#id_company_name')?.value.trim();
      const businessNumber = form.querySelector('#id_business_number')?.value.trim();
      
      if (!companyName) {
        e.preventDefault();
        alert('회사명을 입력해주세요.');
        showTab('#tab-b2b');
        form.querySelector('#id_company_name')?.focus();
        return;
      }
      
      if (!businessNumber) {
        e.preventDefault();
        alert('사업자번호를 입력해주세요.');
        showTab('#tab-b2b');
        form.querySelector('#id_business_number')?.focus();
        return;
      }
    }

    // ✅ 등급 변경 확인 (선택되어 있는 경우)
    if (gradeSelect && gradeSelect.value) {
      const selectedOption = gradeSelect.options[gradeSelect.selectedIndex];
      const gradeName = selectedOption.textContent;
      
      if (!confirm(`선택한 등급 "${gradeName}"으로 회원을 등록하시겠습니까?`)) {
        e.preventDefault();
        return;
      }
    }

    // 제출 중 상태 표시
    const submitBtn = form.querySelector('button[type="submit"]');
    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 등록 중...';
    }

    console.log('회원 등록 폼 제출');
  }

  // ===== 페이지 로드 완료 시 초기화 =====
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  // ✅ 전역에서 접근 가능하도록 export
  window.MemberAddManager = {
    filterGradesByMemberType: filterGradesByMemberType,
    showTab: showTab
  };
})();