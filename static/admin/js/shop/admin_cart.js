(function() {
    'use strict';
    
    // 장바구니 수량 변경 저장 함수
    window.saveAllCartOptions = function() {
        const inputs = document.querySelectorAll('.cart-qty-input');
        const updates = [];
        let totalAmount = 0;
        
        inputs.forEach(input => {
            const quantity = parseInt(input.value) || 0;
            const optionId = input.dataset.optionId;
            const maxStock = parseInt(input.dataset.maxStock) || 0;
            
            if (quantity > maxStock) {
                alert(`수량이 재고(${maxStock}개)를 초과할 수 없습니다.`);
                input.value = maxStock;
                return;
            }
            
            if (quantity < 0) {
                alert('수량은 0보다 작을 수 없습니다.');
                input.value = 0;
                return;
            }
            
            updates.push({
                optionId: optionId,
                quantity: quantity
            });
        });
        
        // AJAX로 서버에 저장 요청
        if (updates.length > 0) {
            const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
            
            fetch('/shop/cart/update-multiple/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify({
                    updates: updates
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    alert('수량이 저장되었습니다.');
                    // 총 금액 업데이트
                    updateTotalAmount();
                } else {
                    alert('저장 중 오류가 발생했습니다.');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('저장 중 오류가 발생했습니다.');
            });
        }
    };
    
    // 총 금액 계산 및 표시
    function updateTotalAmount() {
        const inputs = document.querySelectorAll('.cart-qty-input');
        let totalKRW = 0;
        
        inputs.forEach(input => {
            const quantity = parseInt(input.value) || 0;
            const priceKRW = parseFloat(input.dataset.priceKrw) || 0;
            totalKRW += quantity * priceKRW;
        });
        
        const totalDisplay = document.getElementById('cart-total-display');
        if (totalDisplay) {
            totalDisplay.textContent = `총 주문금액: ₩${totalKRW.toLocaleString()}`;
        }
    }
    
    // 페이지 로드 시 이벤트 리스너 등록
    document.addEventListener('DOMContentLoaded', function() {
        // 수량 입력 필드에 change 이벤트 리스너 추가
        const inputs = document.querySelectorAll('.cart-qty-input');
        inputs.forEach(input => {
            input.addEventListener('change', function() {
                const maxStock = parseInt(this.dataset.maxStock) || 0;
                const value = parseInt(this.value) || 0;
                
                if (value > maxStock) {
                    alert(`수량이 재고(${maxStock}개)를 초과할 수 없습니다.`);
                    this.value = maxStock;
                } else if (value < 0) {
                    this.value = 0;
                }
                
                updateTotalAmount();
            });
        });
        
        // 초기 총 금액 계산
        updateTotalAmount();
    });
})();