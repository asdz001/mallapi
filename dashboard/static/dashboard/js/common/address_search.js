/**
 * 공용 주소검색 모듈 (카카오/다음 우편번호)
 * - 이벤트 위임으로 버튼/주소칸이 늦게 떠도 동작
 * - zip(우편번호) 인풋은 옵션(null 가능)
 */
(function (global) {
  const KAKAO_SRC = "//t1.daumcdn.net/mapjsapi/bundle/postcode/prod/postcode.v2.js";

  const AddressSearch = {
    _loaded: false,
    _loading: false,
    _queue: [],
    _inited: false,
    _configs: [],   // 등록된 인스턴스 설정을 저장

    loadScript(cb) {
      if (this._loaded) return cb();
      this._queue.push(cb);
      if (this._loading) return;
      this._loading = true;

      const s = document.createElement("script");
      s.src = KAKAO_SRC;
      s.onload = () => {
        this._loaded = true;
        this._loading = false;
        this._queue.splice(0).forEach(fn => fn());
      };
      s.onerror = () => {
        this._loading = false;
        alert("우편번호 스크립트 로드에 실패했습니다.");
      };
      document.head.appendChild(s);
    },

    _ensureLayer() {
      let layer = document.getElementById("postcode-layer");
      if (!layer) {
        layer = document.createElement("div");
        layer.id = "postcode-layer";
        layer.style.cssText = "position:fixed;z-index:1050;left:50%;top:50%;transform:translate(-50%,-50%);width:100%;max-width:420px;height:480px;background:#fff;border-radius:8px;box-shadow:0 6px 20px rgba(0,0,0,.2);display:none";
        layer.innerHTML = '<div id="postcode-close" style="position:absolute;right:8px;top:6px;cursor:pointer;font-size:20px">✕</div><div id="postcode-embed" style="width:100%;height:100%"></div>';
        document.body.appendChild(layer);
        document.getElementById("postcode-close").addEventListener("click", () => (layer.style.display = "none"));
      }
      return layer;
    },

    /**
     * 페이지별 초기화 등록
     * - button: 버튼 셀렉터 (필수)
     * - zip: 우편번호 input 셀렉터 (선택; 없으면 null)
     * - addr1: 기본주소 input 셀렉터 (필수)
     * - addr2: 상세주소 input 셀렉터 (선택)
     * - mode: 'layer' | 'popup'
     * - readonly: 주소/우편번호 읽기전용 여부
     * - onSelected: 선택 후 콜백
     */
    init(opts) {
      const cfg = { button: null, zip: null, addr1: null, addr2: null, mode: "layer", readonly: true, onSelected: null, ...opts };
      if (!cfg.button || !cfg.addr1) {
        console.warn("[AddressSearch] button/addr1 선택자가 필요합니다.", cfg);
        return;
      }
      this._configs.push(cfg);

      // 입력칸이 이미 존재하면 readonly 적용
      const $addr1 = document.querySelector(cfg.addr1);
      const $zip   = cfg.zip ? document.querySelector(cfg.zip) : null;
      if (cfg.readonly) {
        if ($addr1) $addr1.setAttribute("readonly", "readonly");
        if ($zip)   $zip.setAttribute("readonly", "readonly");
      }

      // 이벤트 위임을 한 번만 설치
      if (!this._inited) {
        this._installDelegation();
        this._inited = true;
      }
    },

    _installDelegation() {
      // 버튼 클릭 위임
      document.addEventListener("click", (e) => {
        // 등록된 모든 cfg 중, 현재 클릭이 해당 버튼인가?
        for (const cfg of this._configs) {
          const btn = e.target.closest(cfg.button);
          if (!btn) continue;
          e.preventDefault();
          this._openPostcode(cfg);
          return;
        }
      });

      // 주소칸 포커스 시에도 검색 열기(UX)
      document.addEventListener("focusin", (e) => {
        for (const cfg of this._configs) {
          const addr1 = e.target.closest(cfg.addr1);
          if (!addr1) continue;
          // readonly 주소칸 포커스일 때만 동작
          if (addr1.hasAttribute("readonly")) {
            this._openPostcode(cfg);
          }
          return;
        }
      });
    },

    _openPostcode(cfg) {
      this.loadScript(() => {
        if (cfg.mode === "popup") {
          new daum.Postcode({
            oncomplete: (d) => this._fill(d, cfg)
          }).open();
        } else {
          const layer = this._ensureLayer();
          layer.style.display = "block";
          new daum.Postcode({
            oncomplete: (d) => { this._fill(d, cfg); layer.style.display = "none"; },
            width: "100%", height: "100%"
          }).embed(document.getElementById("postcode-embed"));
        }
      });
    },

    _fill(d, cfg) {
      const $zip   = cfg.zip   ? document.querySelector(cfg.zip)   : null;
      const $addr1 =            document.querySelector(cfg.addr1);
      const $addr2 = cfg.addr2 ? document.querySelector(cfg.addr2) : null;

      const addr = d.roadAddress || d.jibunAddress || "";
      if ($zip)   $zip.value = d.zonecode || "";
      if ($addr1) $addr1.value = addr;
      if ($addr2) $addr2.focus();

      if (typeof cfg.onSelected === "function") {
        cfg.onSelected({
          type: d.userSelectedType, zonecode: d.zonecode,
          roadAddress: d.roadAddress, jibunAddress: d.jibunAddress,
          sido: d.sido, sigungu: d.sigungu, bname: d.bname,
          bcode: d.bcode, buildingName: d.buildingName, apartment: d.apartment
        });
      }
    }
  };

  global.AddressSearch = AddressSearch;
})(window);
