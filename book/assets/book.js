/* ==========================================================================
   AI 바이브 코딩 시대의 파이썬 개념 입문서 — 공용 스크립트
   원칙: 이 파일이 없어도 책은 읽힙니다. 여기 있는 건 전부 편의 기능입니다.
   ========================================================================== */
(function () {
  'use strict';

  var STORE = {
    theme: 'pybook:theme',
    done: 'pybook:done',
    scroll: 'pybook:scroll'
  };

  /* --- localStorage 안전 래퍼 (프라이빗 모드·차단 환경 대응) --- */
  function read(key, fallback) {
    try {
      var v = window.localStorage.getItem(key);
      return v === null ? fallback : v;
    } catch (e) { return fallback; }
  }
  function write(key, value) {
    try { window.localStorage.setItem(key, value); } catch (e) { /* noop */ }
  }
  function readJSON(key, fallback) {
    try { return JSON.parse(read(key, '')) || fallback; } catch (e) { return fallback; }
  }

  var $ = function (sel, ctx) { return (ctx || document).querySelector(sel); };
  var $$ = function (sel, ctx) {
    return Array.prototype.slice.call((ctx || document).querySelectorAll(sel));
  };


  /* ======================================================================
     1. 테마 토글
     ====================================================================== */
  function initTheme() {
    var saved = read(STORE.theme, null);
    if (saved === 'dark' || saved === 'light') {
      document.documentElement.setAttribute('data-theme', saved);
    }
    var btn = $('[data-action="toggle-theme"]');
    if (!btn) return;

    function current() {
      var attr = document.documentElement.getAttribute('data-theme');
      if (attr) return attr;
      return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    }
    function sync() {
      var isDark = current() === 'dark';
      btn.setAttribute('aria-label', isDark ? '밝은 테마로' : '어두운 테마로');
      btn.setAttribute('title', isDark ? '밝은 테마로' : '어두운 테마로');
      var sun = $('.icon-sun', btn), moon = $('.icon-moon', btn);
      if (sun) sun.style.display = isDark ? 'none' : '';
      if (moon) moon.style.display = isDark ? '' : 'none';
    }
    btn.addEventListener('click', function () {
      var next = current() === 'dark' ? 'light' : 'dark';
      document.documentElement.setAttribute('data-theme', next);
      write(STORE.theme, next);
      sync();
    });
    sync();
  }


  /* ======================================================================
     2. 코드 복사 버튼
     ====================================================================== */
  function textOf(el) {
    // 줄 번호는 CSS 카운터라 textContent에 포함되지 않습니다.
    return el.textContent.replace(/ /g, ' ').replace(/\s+$/, '');
  }

  function initCopy() {
    $$('.example__code').forEach(function (block) {
      if ($('.copy-btn', block)) return;
      var pre = $('pre', block);
      if (!pre) return;
      var btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'copy-btn';
      btn.textContent = '복사';
      btn.addEventListener('click', function () { copy(textOf(pre), btn); });
      block.insertBefore(btn, block.firstChild);
    });

    $$('.ai-prompt__text').forEach(function (block) {
      if ($('.copy-btn', block)) return;
      var btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'copy-btn';
      btn.textContent = '복사';
      btn.addEventListener('click', function () {
        var clone = block.cloneNode(true);
        var b = $('.copy-btn', clone);
        if (b) b.remove();
        copy(textOf(clone), btn);
      });
      block.insertBefore(btn, block.firstChild);
    });
  }

  function copy(text, btn) {
    function done() {
      var old = btn.textContent;
      btn.textContent = '복사됨';
      btn.classList.add('is-done');
      setTimeout(function () {
        btn.textContent = old === '복사됨' ? '복사' : old;
        btn.classList.remove('is-done');
      }, 1400);
    }
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(done, function () { fallback(text, done); });
    } else {
      fallback(text, done);
    }
  }

  function fallback(text, done) {
    var ta = document.createElement('textarea');
    ta.value = text;
    ta.setAttribute('readonly', '');
    ta.style.cssText = 'position:fixed;top:-1000px;opacity:0';
    document.body.appendChild(ta);
    ta.select();
    try { document.execCommand('copy'); done(); } catch (e) { /* noop */ }
    document.body.removeChild(ta);
  }


  /* ======================================================================
     3. 사이드바 (모바일 드로어)
     ====================================================================== */
  function initSidebar() {
    var sidebar = $('#sidebar');
    var toggle = $('[data-action="toggle-sidebar"]');
    if (!sidebar || !toggle) return;

    var backdrop = document.createElement('div');
    backdrop.className = 'sidebar-backdrop';
    document.body.appendChild(backdrop);

    function open() {
      sidebar.classList.add('is-open');
      backdrop.classList.add('is-open');
      toggle.setAttribute('aria-expanded', 'true');
    }
    function close() {
      sidebar.classList.remove('is-open');
      backdrop.classList.remove('is-open');
      toggle.setAttribute('aria-expanded', 'false');
    }
    toggle.addEventListener('click', function () {
      sidebar.classList.contains('is-open') ? close() : open();
    });
    backdrop.addEventListener('click', close);
    sidebar.addEventListener('click', function (e) {
      if (e.target.closest('a')) close();
    });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') close();
    });
  }


  /* ======================================================================
     4. 읽기 진도 바 + 스크롤 스파이
     ====================================================================== */
  function initProgress() {
    var bar = $('.reading-progress > i');
    var main = $('#main');
    if (!bar || !main) return;

    var ticking = false;
    function update() {
      var rect = main.getBoundingClientRect();
      var total = rect.height - window.innerHeight;
      var passed = -rect.top;
      var pct = total <= 0 ? 100 : Math.min(100, Math.max(0, (passed / total) * 100));
      bar.style.width = pct.toFixed(1) + '%';
      ticking = false;
    }
    window.addEventListener('scroll', function () {
      if (!ticking) { ticking = true; window.requestAnimationFrame(update); }
    }, { passive: true });
    window.addEventListener('resize', update, { passive: true });
    update();
  }

  /* 활성 항목이 사이드바 밖으로 나가면 사이드바를 스크롤해 보이게 합니다. */
  function keepVisible(el) {
    var sidebar = $('#sidebar');
    if (!sidebar || !el) return;
    // 모바일 드로어가 닫혀 있으면 건드리지 않습니다.
    if (window.innerWidth < 1024 && !sidebar.classList.contains('is-open')) return;

    var box = sidebar.getBoundingClientRect();
    var item = el.getBoundingClientRect();
    var margin = 48;

    if (item.top < box.top + margin) {
      sidebar.scrollTop -= (box.top + margin) - item.top;
    } else if (item.bottom > box.bottom - margin) {
      sidebar.scrollTop += item.bottom - (box.bottom - margin);
    }
  }

  /* 스크롤에 따라 목차의 현재 위치를 옮깁니다.
     - 챕터 페이지: 본문의 각 절(.section)을 따라갑니다.
     - 표지: 목차 목록의 각 장(li[data-id])을 따라갑니다. */
  function initScrollSpy() {
    if (!('IntersectionObserver' in window)) return;

    var targets = [];   // 관찰할 본문 요소
    var marks = [];     // 강조할 사이드바 요소
    var activeClass = 'is-active';

    var subLinks = $$('.sidebar__sub a[href^="#"]');
    if (subLinks.length) {
      subLinks.forEach(function (a) {
        var el = document.getElementById(a.getAttribute('href').slice(1));
        if (el) { targets.push(el); marks.push(a); }
      });
    } else {
      // 표지 — 본문의 장 목록과 사이드바 항목을 data-id로 짝지웁니다.
      $$('#main li[data-id]').forEach(function (row) {
        var id = row.getAttribute('data-id');
        var item = $('.sidebar__item[data-id="' + id + '"]');
        if (item) { targets.push(row); marks.push(item); }
      });
      activeClass = 'is-inview';
    }

    if (!targets.length) return;

    var seen = new Array(targets.length);
    var current = -1;

    function apply() {
      var first = -1;
      for (var i = 0; i < seen.length; i++) {
        if (seen[i]) { first = i; break; }
      }
      if (first === -1 || first === current) return;
      current = first;
      marks.forEach(function (m) { m.classList.remove(activeClass); });
      marks[first].classList.add(activeClass);
      keepVisible(marks[first]);
    }

    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        var i = targets.indexOf(entry.target);
        if (i !== -1) seen[i] = entry.isIntersecting;
      });
      apply();
    }, { rootMargin: '-80px 0px -60% 0px', threshold: 0 });

    targets.forEach(function (el) { observer.observe(el); });

    // 현재 장이 있으면 처음부터 보이게 해 둡니다.
    var currentItem = $('.sidebar__item.is-current');
    if (currentItem) {
      window.requestAnimationFrame(function () { keepVisible(currentItem); });
    }
  }


  /* ======================================================================
     5. 읽음 표시 (장 단위)
     ====================================================================== */
  function initDone() {
    var chapter = document.body.getAttribute('data-chapter');
    var done = readJSON(STORE.done, {});

    // 사이드바에 읽음 표시 반영
    $$('.sidebar__item[data-id]').forEach(function (li) {
      if (done[li.getAttribute('data-id')]) li.classList.add('is-done');
    });

    var btn = $('[data-action="toggle-done"]');
    if (!btn || !chapter) return;

    function sync() {
      var isDone = !!done[chapter];
      btn.classList.toggle('is-done', isDone);
      btn.setAttribute('aria-pressed', isDone ? 'true' : 'false');
      var label = $('.done-label', btn);
      if (label) label.textContent = isDone ? '읽음' : '읽음 표시';
    }
    btn.addEventListener('click', function () {
      done[chapter] ? delete done[chapter] : (done[chapter] = Date.now());
      write(STORE.done, JSON.stringify(done));
      var li = $('.sidebar__item[data-id="' + chapter + '"]');
      if (li) li.classList.toggle('is-done', !!done[chapter]);
      sync();
    });
    sync();
  }


  /* ======================================================================
     6. 검색 (search-index.json)
     ====================================================================== */
  function initSearch() {
    var overlay = $('#search-overlay');
    var openBtn = $('[data-action="open-search"]');
    if (!overlay || !openBtn) return;

    var input = $('input', overlay);
    var results = $('.search-results', overlay);
    var index = null;
    var loading = false;

    function base() {
      // chapters/ch04.html 에서도 appendix/ 에서도 루트를 찾아냅니다.
      var root = document.body.getAttribute('data-root');
      return root ? root : './';
    }

    function load() {
      if (index || loading) return;

      // search-index.js 가 script 태그로 먼저 읽힙니다.
      // 파일을 직접 열었을 때(file://) fetch 는 브라우저가 막으므로
      // 이 전역 변수가 기본 경로입니다.
      if (window.PYBOOK_SEARCH) {
        index = window.PYBOOK_SEARCH;
        render(input.value);
        return;
      }

      // 색인 파일이 없을 때를 대비한 보조 경로
      loading = true;
      fetch(base() + 'assets/search-index.json')
        .then(function (r) { return r.ok ? r.json() : []; })
        .then(function (data) { index = data; loading = false; render(input.value); })
        .catch(function () { index = []; loading = false; render(input.value); });
    }

    function open() {
      overlay.classList.add('is-open');
      load();
      input.value = '';
      render('');
      input.focus();
    }
    function close() { overlay.classList.remove('is-open'); }

    function render(q) {
      q = (q || '').trim().toLowerCase();
      if (!index) { results.innerHTML = '<p class="search-empty">불러오는 중…</p>'; return; }
      if (!q) {
        results.innerHTML = '<p class="search-empty">장 제목, 절 제목, 본문 키워드를 검색합니다.</p>';
        return;
      }
      var hits = index.filter(function (item) {
        return (item.t + ' ' + item.c + ' ' + (item.b || '')).toLowerCase().indexOf(q) !== -1;
      }).slice(0, 30);

      if (!hits.length) {
        results.innerHTML = '<p class="search-empty">결과가 없습니다.</p>';
        return;
      }
      results.innerHTML = hits.map(function (item) {
        return '<a href="' + base() + item.u + '">' +
               '<span class="sr-crumb">' + esc(item.c) + '</span>' +
               '<span class="sr-title">' + esc(item.t) + '</span></a>';
      }).join('');
    }

    function esc(s) {
      return String(s).replace(/[&<>"]/g, function (c) {
        return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c];
      });
    }

    openBtn.addEventListener('click', open);
    overlay.addEventListener('click', function (e) { if (e.target === overlay) close(); });
    input.addEventListener('input', function () { render(input.value); });

    document.addEventListener('keydown', function (e) {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        overlay.classList.contains('is-open') ? close() : open();
      }
      if (e.key === 'Escape' && overlay.classList.contains('is-open')) close();
    });
  }


  /* ======================================================================
     7. 이전/다음 키보드 이동
     ====================================================================== */
  function initKeyNav() {
    document.addEventListener('keydown', function (e) {
      if (e.metaKey || e.ctrlKey || e.altKey) return;
      var tag = (e.target.tagName || '').toLowerCase();
      if (tag === 'input' || tag === 'textarea' || e.target.isContentEditable) return;
      if ($('.search-overlay.is-open')) return;

      var link = null;
      if (e.key === 'ArrowLeft') link = $('.pager__prev');
      if (e.key === 'ArrowRight') link = $('.pager__next');
      if (link && link.getAttribute('href')) window.location.href = link.getAttribute('href');
    });
  }


  /* ======================================================================
     8. 인쇄 직전 details 펼침 (CSS만으로 안 되는 브라우저 대비)
     ====================================================================== */
  function initPrint() {
    var opened = [];
    window.addEventListener('beforeprint', function () {
      opened = $$('details:not([open])');
      opened.forEach(function (d) { d.setAttribute('open', ''); });
    });
    window.addEventListener('afterprint', function () {
      opened.forEach(function (d) { d.removeAttribute('open'); });
      opened = [];
    });
  }


  /* ----------------------------------------------------------------------
     용어에 부록 H 링크 걸기
     23개 장을 일일이 고치지 않고 여기 한 곳에서 처리합니다.
     JS 가 없어도 본문은 그대로 읽힙니다 — 밑줄만 남습니다.
     ---------------------------------------------------------------------- */
  function initKeywords() {
    var root = document.body.getAttribute('data-root') || '';
    var 사전 = root + 'appendix/apx-h-glossary.html';

    // 부록 H 안에서는 자기 자신을 걸지 않습니다
    if (document.body.getAttribute('data-chapter') === 'apx-h-glossary') return;

    $$('span.keyword[data-term]').forEach(function (el) {
      var 용어 = el.getAttribute('data-term');
      if (!용어) return;

      var a = document.createElement('a');
      a.className = 'keyword';
      a.setAttribute('data-term', 용어);
      a.href = 사전 + '#t-' + 용어.trim().replace(/\s+/g, '-');
      a.title = '부록 H — ' + 용어 + ' 뜻 보기';
      a.innerHTML = el.innerHTML;
      el.parentNode.replaceChild(a, el);
    });
  }


  /* ====================================================================== */
  function init() {
    initTheme();
    initCopy();
    initSidebar();
    initProgress();
    initScrollSpy();
    initDone();
    initSearch();
    initKeyNav();
    initKeywords();
    initPrint();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
