/**
 * 이벤트 폼: 브랜드/카테고리/성별 드롭다운 로드 + Hidden(JSON) 주입
 * - 기존 HTML은 select만, 저장은 Hidden(JSON)으로 처리
 * - 브라우저 기본 멀티선택의 불편함을 해결(클릭 토글)하고,
 *   "전체 적용" 체크와 중복 체크박스 이슈도 안전하게 처리
 */

(function () {
  // ===== 엔드포인트 (환경에 맞게 필요시 경로만 바꾸면 됨) =====
  const ENDPOINTS = {
    brand: '/dashboard/products/classification/brand/brands/',
    category: (level) => `/dashboard/products/classification/category/options/${level}/`,
  };

  // ===== 공통 유틸 =====
  const $ = (sel) => document.querySelector(sel);
  const $$ = (sel) => Array.from(document.querySelectorAll(sel));
  function parseJSON(v) { if (!v) return []; if (Array.isArray(v)) return v; try { return JSON.parse(v); } catch { return []; } }
  async function getJSON(url) {
    try { const r = await fetch(url, { headers: { 'X-Requested-With': 'XMLHttpRequest' } }); return await r.json(); }
    catch { return null; }
  }
  function pickFirst(obj, keys, fallback = []) {
    if (!obj || typeof obj !== 'object') return fallback;
    for (const k of keys) if (obj[k] != null) return obj[k] || fallback;
    return fallback;
  }
  function fillSelect(selectEl, items) {
    if (!selectEl || !Array.isArray(items)) return;
    for (const it of items) {
      const name = it.name ?? it.label ?? it.code ?? it.id;
      const value = it.name ?? it.code ?? it.id;   // 저장용은 문자열 권장
      if (name == null || value == null) continue;
      const opt = document.createElement('option');
      opt.value = String(value);
      opt.textContent = String(name);
      selectEl.appendChild(opt);
    }
  }

  // ===== 핵심 DOM =====
  const form = $('#event-form') || $('form');

  // 중복 렌더링 대비: 같은 ID가 2개면 마지막(보통 화면에 보이는 것)을 사용
  const allCbs = $$('#id_target_all_products');
  const allCb = allCbs.length ? allCbs[allCbs.length - 1] : null;

  const selBrand = $('#event-brand-select');
  const selL1 = $('#event-category-l1');
  const selL2 = $('#event-category-l2');
  const selL3 = $('#event-category-l3');

  // Hidden(JSON) — 서버로 실제 저장되는 필드
  const hidBrands = $('#id_target_brands');
  const hidCats = $('#id_target_categories');

  // (선택) 성별 — 템플릿에 hidden이 있다면 자동 인식
  //  - 우선순위: id_target_member_types → id_target_genders
  const hidGenders = $('#id_target_member_types') || $('#id_target_genders');
  const selGender = $('#event-gender-select'); // 템플릿에 select를 추가했을 때만 동작

  // ===== 멀티선택 UX 개선: 클릭으로 토글(CTRL 불필요) =====
  function enableClickToggle(selectEl) {
    if (!selectEl || !selectEl.multiple) return;
    selectEl.addEventListener('mousedown', function (e) {
      if (e.target && e.target.tagName === 'OPTION') {
        e.preventDefault(); // 기본 선택 방지
        e.target.selected = !e.target.selected; // 토글
        // 선택 상태가 즉시 반영되도록 focus 유지
        selectEl.focus();
      }
    });
  }

  // ===== 전체 적용 체크와 연동 =====
  function toggleTargetsDisabled() {
    const disabled = !!(allCb && allCb.checked);
    [selBrand, selL1, selL2, selL3, selGender].forEach(el => el && (el.disabled = disabled));
  }

  // ===== 옵션 로드 =====
  async function loadOptions() {
    // 브랜드
    if (selBrand) {
      const js = await getJSON(ENDPOINTS.brand);
      const list = pickFirst(js, ['brands', 'data', 'items'], []);
      fillSelect(selBrand, list);
      attachBrandFilter(selBrand, allCb);
    }
    // 카테고리 (level1 / level2 / level3)
    if (selL1) {
      const js = await getJSON(ENDPOINTS.category('level1'));
      const list = pickFirst(js, ['options', 'data', 'items', 'categories'], []);
      fillSelect(selL1, list);
    }
    if (selL2) {
      const js = await getJSON(ENDPOINTS.category('level2'));
      const list = pickFirst(js, ['options', 'data', 'items', 'categories'], []);
      fillSelect(selL2, list);
    }
    if (selL3) {
      const js = await getJSON(ENDPOINTS.category('level3'));
      const list = pickFirst(js, ['options', 'data', 'items', 'categories'], []);
      fillSelect(selL3, list);
    }
  }

  // ===== 초기 선택 반영 =====
  function applyInitialSelections() {
    const initBrands = parseJSON(hidBrands?.value);
    const initCats = parseJSON(hidCats?.value);
    const initGender = parseJSON(hidGenders?.value); // ["M","F"] 등

    if (selBrand) Array.from(selBrand.options).forEach(o => { if (initBrands.includes(o.value)) o.selected = true; });
    if (selL1) Array.from(selL1.options).forEach(o => { if (initCats.includes(o.value)) o.selected = true; });
    if (selL2) Array.from(selL2.options).forEach(o => { if (initCats.includes(o.value)) o.selected = true; });
    if (selL3) Array.from(selL3.options).forEach(o => { if (initCats.includes(o.value)) o.selected = true; });
    if (selGender && initGender.length) {
      Array.from(selGender.options).forEach(o => { if (initGender.includes(o.value)) o.selected = true; });
    }
  }

  // ===== 제출 시 Hidden(JSON) 주입 =====
  function bindFormSubmit() {
    if (!form) return;
    form.addEventListener('submit', function () {
      // 전체 적용이면 제한 없음(빈 배열 저장)
      if (allCb && allCb.checked) {
        if (hidBrands) hidBrands.value = JSON.stringify([]);
        if (hidCats) hidCats.value = JSON.stringify([]);
        if (hidGenders) hidGenders.value = JSON.stringify([]);
        return;
      }
      const pick = (sel) => sel ? Array.from(sel.selectedOptions).map(o => o.value) : [];
      const brands = pick(selBrand);
      const cats = [...new Set([
        ...pick(selL1),
        ...pick(selL2),
        ...pick(selL3)
      ])]; // 중복 제거
      const genders = pick(selGender); // ["M"] or ["F"] or ["M","F"]

      if (hidBrands) hidBrands.value = JSON.stringify(brands);
      if (hidCats) hidCats.value = JSON.stringify(cats);
      if (hidGenders) hidGenders.value = JSON.stringify(genders);
    });
  }

  function attachBrandFilter(selBrand, allCb) {
    const input = document.getElementById('brand-filter');
    if (!input || !selBrand) return;

    const applyFilter = () => {
      const q = (input.value || '').trim().toLowerCase();
      // 옵션을 순회하며 숨김/표시
      Array.from(selBrand.options).forEach(opt => {
        const text = (opt.textContent || '').toLowerCase();
        const matched = !q || text.includes(q);
        // 이미 선택된 옵션은 항상 보이도록 처리(실수로 숨김 방지)
        opt.hidden = !matched && !opt.selected;
      });
      // 필터 후에도 스크롤 가능 (select 기본 동작 유지)
    };

    input.addEventListener('input', applyFilter);

    // "전체 상품 적용" 체크 시 검색창도 같이 disable
    const toggle = () => { input.disabled = !!(allCb && allCb.checked); };
    if (allCb) allCb.addEventListener('change', toggle);

    // 초기 1회 적용
    toggle();
    applyFilter();
  }

  document.addEventListener('DOMContentLoaded', async function () {
    // 멀티 선택 UX 개선
    [selBrand, selL1, selL2, selL3].forEach(enableClickToggle);

    await loadOptions();           // 옵션 채우기
    applyInitialSelections();      // 기존 값 반영
    bindFormSubmit();              // 저장 시 Hidden(JSON) 주입

    toggleTargetsDisabled();       // 전체 적용 반영
    if (allCb) allCb.addEventListener('change', toggleTargetsDisabled);
  });
})();
