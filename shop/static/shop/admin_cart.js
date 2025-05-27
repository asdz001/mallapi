// ✅ 최상단에 위치 (공통으로 사용)
function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';');
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === (name + '=')) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}


// ✅ DOM 로드 후 이벤트 설정
document.addEventListener('DOMContentLoaded', function () {
  document.querySelectorAll('.cart-qty-input').forEach(input => {
    input.addEventListener('keydown', function (e) {
      if (e.key === 'Enter') {
        const cartOptionId = this.dataset.optionId;
        const quantity = parseInt(this.value.trim(), 10);
        const maxStock = parseInt(this.dataset.maxStock, 10);

        if (isNaN(quantity) || quantity < 0) {
          alert("❌ 0 이상의 숫자만 입력 가능합니다.");
          this.focus();
          return;
        }

        if (quantity > maxStock) {
          alert(`❌ 재고(${maxStock})를 초과할 수 없습니다.`);
          this.focus();
          return;
        }

        fetch('/admin/api/save-cart-option/', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken'),
          },
          body: JSON.stringify({
            cart_option_id: cartOptionId,
            quantity: quantity,
          })
        }).then(res => res.json()).then(data => {
          if (data.success) {
            input.style.border = '2px solid green';
          } else {
            input.style.border = '2px solid red';
            alert('저장 실패: ' + data.error);
          }
        }).catch(err => {
          console.error("❌ 오류:", err);
          alert("❌ 저장 중 오류 발생!");
        });
      }
    });
  });
});


// ✅ 전체 저장 버튼용 함수
function saveAllCartOptions() {
  const inputs = document.querySelectorAll(".cart-qty-input");
  const items = [];
  let valid = true;

  inputs.forEach((input) => {
    const cartOptionId = input.dataset.optionId;
    const quantity = parseInt(input.value.trim(), 10);
    const maxStock = parseInt(input.dataset.maxStock, 10);

    if (isNaN(quantity) || quantity < 0) {
      alert(`❌ 수량은 0 이상 정수만 입력해주세요.`);
      input.focus();
      valid = false;
      return;
    }

    if (quantity > maxStock) {
      alert(`❌ 재고(${maxStock})를 초과할 수 없습니다.`);
      input.focus();
      valid = false;
      return;
    }

    items.push({
      cart_option_id: cartOptionId,
      quantity: quantity,
    });
  });

  if (!valid) return;

  const btn = document.querySelector("button[onclick='saveAllCartOptions()']");
  if (btn) {
    btn.disabled = true;
    btn.innerText = "💾 저장 중...";
  }

  fetch("/admin/api/save-cart-option/", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": getCookie("csrftoken"),
    },
    body: JSON.stringify({ items: items }),
  })
    .then(response => {
      if (btn) {
        btn.disabled = false;
        btn.innerText = "💾 전체 저장";
      }

      if (!response.ok) {
        alert("❌ 서버 오류: 저장 실패");
        return;
      }

      return response.json();
    })
    .then(data => {
      if (data && data.success) {
        alert("✅ 저장이 완료되었습니다!");
        location.reload();
      } else {
        alert("❌ 저장 실패: " + (data?.error || "알 수 없는 오류"));
      }
    })
    .catch(error => {
      console.error("❌ 에러 발생:", error);
      alert("❌ 저장 중 오류 발생!");
      if (btn) {
        btn.disabled = false;
        btn.innerText = "💾 전체 저장";
      }
    });
}


// 장바구니 가격합계
document.querySelectorAll(".cart-qty-input").forEach(input => {
    input.addEventListener("input", updateCartTotal);
});

function updateCartTotal() {
    let total = 0;

    document.querySelectorAll(".cart-qty-input").forEach(input => {
        const qty = parseInt(input.value) || 0;
        const row = input.closest("tr");

        // ✅ 공급가가 들어있는 4번째 td에서 숫자 추출
        const priceText = row.querySelector("td:nth-child(4)").innerText.match(/([\d.,]+)/);
        const price = priceText ? parseFloat(priceText[1].replace(/,/g, '')) : 0;

        total += qty * price;
    });

    const totalDisplay = document.getElementById("cart-total-display");
    if (totalDisplay) {
        totalDisplay.innerText = `총 주문금액: ₩${total.toLocaleString()}`;
    }
}

document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll(".cart-qty-input").forEach(input => {
        input.addEventListener("input", updateCartTotal);
    });

    // 페이지 로딩 시에도 한번 계산
    updateCartTotal();
});