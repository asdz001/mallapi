$(document).ready(function () {
    const $form = $('#operatorForm');
    let isEditMode = false;
    let currentOperatorId = null;

    // ✅ 추가 버튼 클릭
    $('#addOperatorBtn').on('click', function () {
        isEditMode = false;
        currentOperatorId = null;

        $form[0].reset();
        $form.find('input[name="id"]').val('');
        $('#operatorModalLabel').text('운영자 추가');

        // ✅ 등록일 경우 비밀번호 영역 항상 보이게
        $('#passwordFields').show();

        $('#operatorModal').modal('show');
    });

    // ✅ 수정 버튼 클릭
    $('.btn-edit-operator').on('click', function () {
        isEditMode = true;
        currentOperatorId = $(this).data('operator-id');

        $.ajax({
            url: `/dashboard/settings/operators/${currentOperatorId}/detail/`,
            method: 'GET',
            success: function (response) {
                if (response.success) {
                    const data = response.data;

                    // 필드 채우기
                    $form.find('input[name="id"]').val(data.id);
                    $form.find('input[name="username"]').val(data.username);
                    $form.find('input[name="first_name"]').val(data.first_name);
                    $form.find('input[name="email"]').val(data.email);
                    $form.find('input[name="contact_number"]').val(data.contact_number);
                    $form.find('select[name="allowed_retailers"]').val(data.allowed_retailers || []);

                    $('#operatorModalLabel').text('운영자 수정');

                    // ✅ 수정 모드일 때 비밀번호 입력창은 기본 숨김
                    $('#passwordFields').hide();

                    $('#operatorModal').modal('show');
                } else {
                    alert('데이터를 불러올 수 없습니다.');
                }
            },
            error: function () {
                alert('서버 오류가 발생했습니다.');
            }
        });
    });

    // 🔐 수정 모드에서 비밀번호 변경 토글
    $(document).on('click', '#togglePasswordFields', function () {
        $('#passwordFields').slideToggle(); // 숨김/보임 전환
    });

    // ✅ [비밀번호 변경] 버튼 눌렀을 때 입력 필드 열기/닫기
    $('#togglePasswordFields').on('click', function () {
        $('#passwordFields').slideToggle();  // 부드럽게 열고 닫기
    });

    // ✅ 기존: 비밀번호 보기/숨기기 기능
    $(document).on('click', '.toggle-password', function () {
        const $input = $($(this).data('target'));
        if ($input.attr('type') === 'password') {
            $input.attr('type', 'text');
            $(this).text('🙈');
        } else {
            $input.attr('type', 'password');
            $(this).text('🔒');
        }
    });


    // ✅ 저장 버튼 제출
    $form.on('submit', function (e) {
        e.preventDefault();

        const password = $('#password').val();
        const confirmPassword = $('#confirm_password').val();

        if (password !== confirmPassword) {
            alert('비밀번호가 일치하지 않습니다.');
            return;
        }

        const formData = $form.serialize();

        const url = isEditMode && currentOperatorId
            ? `/dashboard/settings/operators/${currentOperatorId}/edit/`
            : `/dashboard/settings/operators/create/`;

        $.ajax({
            url: url,
            method: 'POST',
            data: formData,
            success: function (response) {
                if (response.success) {
                    $('#operatorModal').modal('hide');
                    location.reload(); // 목록 갱신
                } else {
                    if (response.errors) {
                        let msg = '저장 실패:\n';
                        for (let field in response.errors) {
                            msg += `- ${field}: ${response.errors[field].join(', ')}\n`;
                        }
                        alert(msg);
                    } else {
                        alert('저장 실패: ' + (response.message || '폼 오류'));
                    }
                }
            },
            error: function () {
                alert('서버 오류로 저장에 실패했습니다.');
            }
        });
    });

    // ✅ 모달 닫힐 때 초기화
    $('#operatorModal').on('hidden.bs.modal', function () {
        isEditMode = false;
        currentOperatorId = null;
        $form[0].reset();
        $('#operatorModalLabel').text('운영자 추가');
    });
});

