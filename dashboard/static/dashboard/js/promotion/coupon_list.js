/* 쿠폰 목록 전용 스크립트
 * - 목록 토글/삭제, 상세보기(모달) 열기
 * - 비개발자용 주석 포함
 */

(function () {
  // ✅ CSRF 토큰 추출 (Django 기본 쿠키에서)
  function getCSRFToken() {
    const match = document.cookie.match(/(^|;)\s*csrftoken=([^;]+)/);
    return match ? decodeURIComponent(match[2]) : '';
  }

  // ✅ 공통 POST(JSON) 헬퍼
  function postJSON(url, data) {
    return fetch(url, {
      method: 'POST',
      headers: {
        'X-CSRFToken': getCSRFToken(),
        'Content-Type': 'application/json',
        'X-Requested-With': 'XMLHttpRequest', // 서버에서 AJAX 분기용
      },
      body: JSON.stringify(data || {}),
    }).then(res => res.json());
  }

  // ✅ 활성화/비활성 토글 버튼 바인딩
  function bindToggle() {
    document.querySelectorAll('.toggle-status').forEach(btn => {
      btn.addEventListener('click', function () {
        const id = this.getAttribute('data-coupon-id');
        if (!id) return;
        const url = this.getAttribute('data-url') || `/dashboard/promotions/coupons/${id}/toggle`;

        this.disabled = true;

        postJSON(url, {})
          .then(json => {
            this.disabled = false;
            if (!json || json.success !== true) {
              alert(json && json.message ? json.message : '상태 변경에 실패했습니다.');
              return;
            }
            const active = json.is_active === true;
            this.classList.toggle('btn-success', active);
            this.classList.toggle('btn-secondary', !active);
            this.innerHTML = `<i class="fas fa-toggle-${active ? 'on' : 'off'}"></i>`;
          })
          .catch(err => {
            this.disabled = false;
            alert('네트워크 오류: ' + err);
          });
      });
    });
  }

  // ✅ 삭제 모달 트리거 및 삭제 실행
  function bindDelete() {
    const modal = document.getElementById('deleteModal');
    const confirmBtn = document.getElementById('confirm-delete');
    const nameEl = document.getElementById('delete-coupon-name');

    // 전역: 템플릿에서 onclick으로 호출
    window.deleteCoupon = function (id, name) {
      confirmBtn.setAttribute('data-id', id);
      nameEl.textContent = name;
      $(modal).modal('show'); // Bootstrap 모달 열기
    };

    // 실제 삭제 실행
    if (confirmBtn) {
      confirmBtn.addEventListener('click', function () {
        const id = this.getAttribute('data-id');
        if (!id) return;

        // 템플릿의 삭제 a태그에 data-delete-url이 있으면 우선 사용
        const trigger = document.querySelector(`[onclick*="deleteCoupon(${id}"]`);
        const url =
          (trigger && trigger.getAttribute('data-delete-url')) ||
          `/dashboard/promotions/coupons/${id}/delete`;

        this.disabled = true;

        postJSON(url, {})
          .then(json => {
            this.disabled = false;
            if (!json || json.success === false) {
              // 서버가 메시지를 리다이렉트로만 전달하더라도 화면을 맞추기 위해 리로드
              window.location.reload();
              return;
            }
            window.location.reload(); // 성공 시 목록 갱신
          })
          .catch(err => {
            this.disabled = false;
            alert('삭제 중 오류: ' + err);
          });
      });
    }
  }

  // ✅ 검색 초기화 버튼
  function bindResetSearch() {
    const btn = document.getElementById('reset-search');
    if (!btn) return;
    btn.addEventListener('click', function () {
      const base = window.location.pathname; // 쿼리 제거
      window.location.href = base;
    });
  }

  // ✅ 상세보기(모달) 열기 - 전역 노출 (템플릿에서 onclick으로 호출)
  window.viewCouponDetail = function (couponId) {
    fetch(`/dashboard/promotions/coupons/${couponId}/detail-modal/`, {
      headers: { 'X-Requested-With': 'XMLHttpRequest' },
    })
      .then(res => res.text())
      .then(html => {
        // 기존 모달이 있으면 제거
        const existing = document.getElementById('couponDetailModal');
        if (existing) existing.remove();
        // 모달 HTML 주입 후 표시
        document.body.insertAdjacentHTML('beforeend', html);
        $('#couponDetailModal').modal('show');
      })
      .catch(err => {
        console.error('상세보기 오류:', err);
        alert('쿠폰 정보를 불러오지 못했습니다.');
      });
  };

  // ✅ 상세보기 모달 내 "수정" 버튼 - 전역 노출
  window.editCoupon = function (couponId) {
    $('#couponDetailModal').modal('hide');
    window.location.href = `/dashboard/promotions/coupons/${couponId}/edit`;
  };

  // 문서 로드 후 한 번만 바인딩
  document.addEventListener('DOMContentLoaded', function () {
    bindToggle();
    bindDelete();
    bindResetSearch();
  });
})();
