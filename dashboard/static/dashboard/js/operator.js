/**
 * operator.js — 최소 변경 버전
 * 목적: "수정 모달"에서만 비밀번호를 버튼으로 ON/OFF하여
 *       OFF일 때는 절대 서버로 전송되지 않도록 보장
 *
 * ※ 기존 코드의 셀렉터/URL/흐름을 그대로 유지
 *    - 추가 버튼: #addOperatorBtn
 *    - 행 수정 버튼: .btn-edit-operator (data-operator-id)
 *    - 행 삭제 버튼: .btn-delete-operator (data-operator-id)
 *    - 수정 저장은 /edit/ 엔드포인트 사용
 *    - 모달 닫기: BS4/BS5 모두 폴백 처리
 */

(function ($, window, document) {
  "use strict";

  // =========================
  // 0) 설정 (경로는 프로젝트 기준으로 고정)
  // =========================
  const BASE = "/dashboard/settings/operators";
  const API = {
    detail: (id) => `${BASE}/${id}/detail/`,
    create: `${BASE}/create/`,
    update: (id) => `${BASE}/${id}/edit/`,     // ★ 원본 서버 규칙: /edit/
    delete: (id) => `${BASE}/${id}/delete/`,
  };

  // =========================
  // 1) 셀렉터(원본 명칭 유지)
  // =========================
  const SEL = {
    // 목록 상단 버튼
    openAddBtn: "#addOperatorBtn",

    // 목록 행 버튼
    editRowBtn: ".btn-edit-operator",
    deleteRowBtn: ".btn-delete-operator",

    // 추가 모달
    addModal: "#addOperatorModal",
    addSaveBtn: "#add_save_btn",
    add: {
      username: "#add_username",
      email: "#add_email",
      firstName: "#add_first_name",
      phone: "#add_phone",
      password: "#add_password",
      confirmPassword: "#add_confirm_password",
      allowedRetailers: "#add_allowed_retailers",
      disableLogin: "#add_disable_login",
    },

    // 수정 모달
    editModal: "#editOperatorModal",
    editSaveBtn: "#edit_save_btn",
    editTogglePwdBtn: "#edit_toggle_pwd_btn",   // ★ 토글 버튼(수정 모달 전용)
    editId: "#edit_operator_id",
    edit: {
      username: "#edit_username",
      email: "#edit_email",
      firstName: "#edit_first_name",
      phone: "#edit_phone",
      password: "#edit_password",
      confirmPassword: "#edit_confirm_password",
      allowedRetailers: "#edit_allowed_retailers",
      disableLogin: "#edit_disable_login",
    },

    // 공통: 비번 보임/숨김
    visibilityBtn: ".toggle-visibility",
  };

  // =========================
  // 2) 공통 유틸
  // =========================
  function getCsrf() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    if (meta) return meta.content;
    const input = document.querySelector('input[name="csrfmiddlewaretoken"]');
    if (input) return input.value;
    const m = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
    return m ? decodeURIComponent(m[1]) : null;
  }

  function ajax(method, url, data) {
    const isFD = (data instanceof FormData);
    const headers = {};
    const t = getCsrf();
    if (t) headers["X-CSRFToken"] = t;
    return $.ajax({
      url,
      method,
      data,
      processData: !isFD,
      contentType: isFD ? false : "application/x-www-form-urlencoded; charset=UTF-8",
      headers
    });
  }

  function showAlert(msg, type) {
    alert((type ? type.toUpperCase() + ": " : "") + (msg || "오류가 발생했습니다."));
  }

  function trim($el) { return ($el.val() || "").trim(); }

  function showModal($m) {
    try { $m.modal("show"); }
    catch (e) {
      const el = $m.get(0);
      if (el && window.bootstrap && window.bootstrap.Modal) new window.bootstrap.Modal(el).show();
    }
  }
  function hideModal($m) {
    try { $m.modal("hide"); }
    catch (e) {
      const el = $m.get(0);
      if (el && window.bootstrap && window.bootstrap.Modal) {
        const inst = window.bootstrap.Modal.getInstance(el) || new window.bootstrap.Modal(el);
        inst.hide();
      }
    }
  }

  // 닫기 버튼(데이터 속성) 폴백 — BS4/BS5 모두 닫히게
  $(document).on("click", '[data-dismiss="modal"], [data-bs-dismiss="modal"]', function () {
    const $m = $(this).closest(".modal");
    if ($m.length) hideModal($m);
  });

  // 비밀번호 보임/숨김
  $(document).on("click", SEL.visibilityBtn, function (e) {
    e.preventDefault();
    const $target = $($(this).data("target"));
    if (!$target.length) return;
    const type = $target.attr("type") === "password" ? "text" : "password";
    $target.attr("type", type);
    const $icon = $(this).find("i");
    if ($icon.length) $icon.toggleClass("fa-eye fa-eye-slash");
  });

  // =========================
  // 3) 운영자 추가(원본 흐름 유지)
  // =========================
  function openAddModal() {
    const $m = $(SEL.addModal);
    $(SEL.add.username).val("");
    $(SEL.add.email).val("");
    $(SEL.add.firstName).val("");
    $(SEL.add.phone).val("");
    $(SEL.add.password).val("").prop("disabled", false);
    $(SEL.add.confirmPassword).val("").prop("disabled", false);
    $(SEL.add.allowedRetailers).val([]).trigger("change.select2");
    $(SEL.add.disableLogin).prop("checked", false);
    showModal($m);
  }
  $(document).on("click", SEL.openAddBtn, function (e) {
    e.preventDefault();
    openAddModal();
  });

  $(document).on("click", SEL.addSaveBtn, function (e) {
    e.preventDefault();

    const $u = $(SEL.add.username);
    const $e = $(SEL.add.email);
    const $f = $(SEL.add.firstName);
    const $p = $(SEL.add.phone);
    const $pw = $(SEL.add.password);
    const $pw2 = $(SEL.add.confirmPassword);
    const $ret = $(SEL.add.allowedRetailers);
    const $dl = $(SEL.add.disableLogin);

    const username = trim($u);
    const email = trim($e);
    const pwd = trim($pw);
    const pwd2 = trim($pw2);

    if (!username) return showAlert("아이디를 입력하세요.", "warning");
    if (!email) return showAlert("이메일을 입력하세요.", "warning");
    if (!pwd || !pwd2) return showAlert("비밀번호와 확인을 입력하세요.", "warning");
    if (pwd !== pwd2) return showAlert("비밀번호와 확인이 일치하지 않습니다.", "warning");

    const fd = new FormData();
    fd.append("username", username);
    fd.append("email", email);
    fd.append("first_name", trim($f));
    fd.append("phone", trim($p));
    fd.append("password", pwd);
    fd.append("confirm_password", pwd2);

    ($ret.val() || []).forEach(v => fd.append("allowed_retailers", v));
    if ($dl.is(":checked")) fd.append("disable_login", "1");

    ajax("POST", API.create, fd)
      .done(res => {
        if (res && res.success) {
          hideModal($(SEL.addModal));
          location.reload();
        } else {
          showAlert((res && res.message) || "등록에 실패했습니다.", "error");
          console.error("Create errors:", res && res.errors);
        }
      })
      .fail(xhr => { console.error(xhr); showAlert("등록 중 오류가 발생했습니다.", "error"); });
  });

  // =========================
  // 4) 운영자 수정 — 비번 ON/OFF 토글만 추가
  // =========================
  function setPwdEditMode(on) {
    const $pw = $(SEL.edit.password);
    const $pw2 = $(SEL.edit.confirmPassword);
    const $btn = $(SEL.editTogglePwdBtn);

    if (on) {
      // ON: 활성화 + 값 비움
      $pw.prop("disabled", false).val("").attr("placeholder", "");
      $pw2.prop("disabled", false).val("").attr("placeholder", "");
      $btn.text("비밀번호변경: ON");
      // 보기 버튼도 활성화
      $pw.closest(".input-group").find(SEL.visibilityBtn).prop("disabled", false);
      $pw2.closest(".input-group").find(SEL.visibilityBtn).prop("disabled", false);
    } else {
      // OFF: 비활성화 + 값 비움 → 전송에서 제외
      $pw.prop("disabled", true).val("").attr("placeholder", "비밀번호 변경 버튼을 눌러 활성화");
      $pw2.prop("disabled", true).val("").attr("placeholder", "비밀번호 변경 버튼을 눌러 활성화");
      $btn.text("비밀번호변경");
      // 보기 버튼 비활성화
      $pw.closest(".input-group").find(SEL.visibilityBtn).prop("disabled", true);
      $pw2.closest(".input-group").find(SEL.visibilityBtn).prop("disabled", true);
    }
  }

  function openEditModal(id) {
    const $m = $(SEL.editModal);

    // 기본 OFF(미변경)
    setPwdEditMode(false);

    ajax("GET", API.detail(id), null)
      .done(res => {
        if (!(res && res.success)) {
          showAlert((res && res.message) || "상세 조회 중 오류가 발생했습니다.", "error");
          return;
        }
        const d = res.data || {};
        $(SEL.editId).val(id);
        $(SEL.edit.username).val(d.username || "");
        $(SEL.edit.email).val(d.email || "");
        $(SEL.edit.firstName).val(d.first_name || "");
        $(SEL.edit.phone).val(d.contact_number || d.phone || "");

        // 로그인 차단: disable_login 또는 is_active 기반
        const disabled = (typeof d.disable_login !== "undefined") ? !!d.disable_login : (d.is_active === false);
        $(SEL.edit.disableLogin).prop("checked", !!disabled);

        // 거래처
        $(SEL.edit.allowedRetailers)
          .val((d.allowed_retailers || []).map(String))
          .trigger("change.select2");

        // 수정 모달에서만 토글 버튼 보이도록(추가 모달과 혼동 방지)
        $(SEL.editTogglePwdBtn).show();

        showModal($m);
      })
      .fail(xhr => { console.error(xhr); showAlert("상세 조회 중 오류가 발생했습니다.", "error"); });
  }

  // 행의 수정 버튼
  $(document).on("click", SEL.editRowBtn, function (e) {
    e.preventDefault();
    const id = $(this).data("operator-id") || $(this).data("id");
    if (!id) return showAlert("잘못된 접근입니다(식별자 누락).", "error");
    openEditModal(id);
  });

  // 토글 버튼
  $(document).on("click", SEL.editTogglePwdBtn, function (e) {
    e.preventDefault();
    const isOn = !$(SEL.edit.password).prop("disabled");
    setPwdEditMode(!isOn);
  });

  // 저장
  $(document).on("click", SEL.editSaveBtn, function (e) {
    e.preventDefault();
    const id = $(SEL.editId).val();
    if (!id) return showAlert("잘못된 접근입니다(식별자 누락).", "error");

    const $u = $(SEL.edit.username);
    const $e = $(SEL.edit.email);
    const $f = $(SEL.edit.firstName);
    const $p = $(SEL.edit.phone);
    const $ret = $(SEL.edit.allowedRetailers);
    const $dl = $(SEL.edit.disableLogin);

    const fd = new FormData();
    fd.append("username", trim($u));
    fd.append("email", trim($e));
    fd.append("first_name", trim($f));
    fd.append("phone", trim($p));
    ($ret.val() || []).forEach(v => fd.append("allowed_retailers", v));
    if ($dl.is(":checked")) fd.append("disable_login", "1");

    // ★ 핵심: 비번 입력칸이 비활성화(OFF)면 전송에서 무조건 제외
    const pwdDisabled = $(SEL.edit.password).prop("disabled") && $(SEL.edit.confirmPassword).prop("disabled");
    if (!pwdDisabled) {
      const pwd = trim($(SEL.edit.password));
      const pwd2 = trim($(SEL.edit.confirmPassword));
      if (!pwd || !pwd2) return showAlert("새 비밀번호와 확인을 입력하세요.", "warning");
      if (pwd !== pwd2) return showAlert("비밀번호와 확인이 일치하지 않습니다.", "warning");
      fd.append("password", pwd);
      fd.append("confirm_password", pwd2);
    }

    ajax("POST", API.update(id), fd)
      .done(res => {
        if (res && res.success) {
          hideModal($(SEL.editModal));
          location.reload();
        } else {
          showAlert((res && res.message) || "수정에 실패했습니다.", "error");
          console.error("Update errors:", res && res.errors);
        }
      })
      .fail(xhr => { console.error(xhr); showAlert("수정 중 오류가 발생했습니다.", "error"); });
  });

  // =========================
  // 5) 삭제(원본 흐름 유지)
  // =========================
  $(document).on("click", SEL.deleteRowBtn, function (e) {
    e.preventDefault();
    const id = $(this).data("operator-id") || $(this).data("id");
    if (!id) return;
    if (!confirm("정말 삭제하시겠습니까? 이 작업은 되돌릴 수 없습니다.")) return;

    ajax("POST", API.delete(id), {})
      .done(res => {
        if (res && res.success) location.reload();
        else { showAlert((res && res.message) || "삭제에 실패했습니다.", "error"); console.error("Delete errors:", res && res.errors); }
      })
      .fail(xhr => { console.error(xhr); showAlert("삭제 중 오류가 발생했습니다.", "error"); });
  });

  // =========================
  // 6) 초기화(툴팁 등)
  // =========================
  $(function () {
    try { $('[data-toggle="tooltip"], [data-bs-toggle="tooltip"]').tooltip(); } catch (e) {}
    // 수정 모달 전용 토글 버튼은 기본적으로 숨김(추가 모달과 혼동 방지)
    $(SEL.editTogglePwdBtn).hide();
  });

})(jQuery, window, document);
