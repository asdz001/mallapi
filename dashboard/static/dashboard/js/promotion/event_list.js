/* 이벤트 목록 전용 스크립트 (쿠폰 관리와 동일한 기능)
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

  // ✅ 활성화/비활성 토글 버튼 바인딩 (문제 코드 수정)
  function bindToggle() {
    document.querySelectorAll('.toggle-status').forEach(btn => {
      btn.addEventListener('click', function () {
        const id = this.getAttribute('data-event-id');
        if (!id) return;
        const url = this.getAttribute('data-url') || `/dashboard/promotions/events/${id}/toggle`;

        this.disabled = true;

        postJSON(url, {})
          .then(json => {
            this.disabled = false;
            if (!json || json.success !== true) {
              alert(json && json.message ? json.message : '상태 변경에 실패했습니다.');
              return;
            }

            const active = json.is_active === true;

            // 1. 토글 버튼 상태 업데이트
            this.classList.toggle('btn-success', active);
            this.classList.toggle('btn-secondary', !active);
            this.innerHTML = `<i class="fas fa-toggle-${active ? 'on' : 'off'}"></i>`;

            // 2. 상태 뱃지 업데이트 (수정된 안전한 로직)
            const statusBadge = document.querySelector(`.event-status-badge[data-event-id="${id}"]`);
            if (statusBadge) {
              // 기존 클래스 제거
              statusBadge.classList.remove('badge-success', 'badge-warning', 'badge-secondary');

              if (active) {
                // 활성화된 경우 - 안전한 방식으로 기간 정보 찾기
                try {
                  const card = statusBadge.closest('.card');
                  const tableRows = card.querySelectorAll('table tr');
                  let periodText = '';

                  // "기간"이 포함된 행을 안전하게 찾기
                  for (const row of tableRows) {
                    if (row.cells && row.cells[0] && row.cells[0].textContent.includes('기간')) {
                      periodText = row.cells[1] ? row.cells[1].textContent.trim() : '';
                      break;
                    }
                  }

                  if (periodText && periodText.includes(' ~ ')) {
                    // 기간 정보가 있는 경우 현재 시간과 비교
                    const [startStr, endStr] = periodText.split(' ~ ');
                    const now = new Date();

                    // 날짜 파싱 (YYYY-MM-DD HH:MM 형식)
                    const startDate = new Date(startStr.replace(/(\d{4})-(\d{2})-(\d{2}) (\d{2}):(\d{2})/, '$1-$2-$3T$4:$5:00'));
                    const endDate = new Date(endStr.replace(/(\d{4})-(\d{2})-(\d{2}) (\d{2}):(\d{2})/, '$1-$2-$3T$4:$5:00'));

                    if (isNaN(startDate.getTime()) || isNaN(endDate.getTime())) {
                      // 날짜 파싱 실패 시 기본 활성 상태
                      statusBadge.classList.add('badge-success');
                      statusBadge.textContent = '활성';
                    } else if (now < startDate) {
                      // 시작 전
                      statusBadge.classList.add('badge-warning');
                      statusBadge.textContent = '대기';
                    } else if (now > endDate) {
                      // 종료 후
                      statusBadge.classList.add('badge-secondary');
                      statusBadge.textContent = '종료';
                    } else {
                      // 진행 중
                      statusBadge.classList.add('badge-success');
                      statusBadge.textContent = '진행중';
                    }
                  } else {
                    // 기간 정보가 없거나 파싱 실패 시 기본 활성 상태
                    statusBadge.classList.add('badge-success');
                    statusBadge.textContent = '활성';
                  }
                } catch (error) {
                  // 모든 오류를 안전하게 처리
                  console.warn('상태 업데이트 중 오류:', error);
                  statusBadge.classList.add('badge-success');
                  statusBadge.textContent = '활성';
                }
              } else {
                // 비활성화된 경우
                statusBadge.classList.add('badge-secondary');
                statusBadge.textContent = '비활성';
              }
            }
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
    const nameEl = document.getElementById('delete-event-name');

    // 전역: 템플릿에서 onclick으로 호출
    window.deleteEvent = function (id, name) {
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
        const trigger = document.querySelector(`[onclick*="deleteEvent(${id}"]`);
        const url =
          (trigger && trigger.getAttribute('data-delete-url')) ||
          `/dashboard/promotions/events/${id}/delete`;

        this.disabled = true;

        fetch(url, {
          method: 'POST',
          headers: {
            'X-CSRFToken': getCSRFToken(),
          }
        }).then(response => {
          this.disabled = false;
          // 서버가 리다이렉트로만 전달하므로 성공/실패 상관없이 리로드
          window.location.reload();
        }).catch(err => {
          this.disabled = false;
          alert('삭제 중 오류: ' + err);
        });
      });
    }
  }

  // ✅ 검색 초기화 버튼
  function bindResetSearch() {
    const btn = document.querySelector('.btn-secondary[href*="event_list"]');
    // 이미 URL이 설정되어 있어서 별도 바인딩 불필요
  }

  // ✅ 상세보기(모달) 열기 - 전역 노출 (템플릿에서 onclick으로 호출)
  window.viewEventDetail = function (eventId) {
    fetch(`/dashboard/promotions/events/${eventId}/detail-modal/`, {
      headers: { 'X-Requested-With': 'XMLHttpRequest' },
    })
      .then(res => res.text())
      .then(html => {
        // 기존 모달이 있으면 제거
        const existing = document.getElementById('eventDetailModal');
        if (existing) existing.remove();
        // 모달 HTML 주입 후 표시
        document.body.insertAdjacentHTML('beforeend', html);
        $('#eventDetailModal').modal('show');
      })
      .catch(err => {
        console.error('상세보기 오류:', err);
        alert('이벤트 정보를 불러오지 못했습니다.');
      });
  };

  // ✅ 상세보기 모달 내 "수정" 버튼 - 전역 노출
  window.editEvent = function (eventId) {
    $('#eventDetailModal').modal('hide');
    window.location.href = `/dashboard/promotions/events/${eventId}/edit`;
  };

  // 문서 로드 후 한 번만 바인딩
  document.addEventListener('DOMContentLoaded', function () {
    bindToggle();
    bindDelete();
    bindResetSearch();
  });
})();