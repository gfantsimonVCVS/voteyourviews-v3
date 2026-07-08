// VoteYourViews.org — Guided Tour modal (shared across pages)
// Usage: <script src="/tutorial.js"></script>  then  window.VYVTutorial.open()
(function () {
  const ISSUES = [
    { id: 'reproductiveRights', label: 'Reproductive Rights' },
    { id: 'immigration',        label: 'Immigration & Border' },
    { id: 'gunPolicy',          label: 'Gun Policy' },
    { id: 'education',          label: 'Public Education' },
    { id: 'healthcare',         label: 'Healthcare' },
    { id: 'climate',            label: 'Climate & Energy' },
    { id: 'electionIntegrity',  label: 'Election Integrity' },
    { id: 'socialSecurity',     label: 'Social Security & Medicare' },
    { id: 'affordability',      label: 'Housing & Affordability' },
  ];

  // Wrap an app screenshot in a phone bezel so it clearly reads as "the app screen"
  function shot(src, caption) {
    return `
      <div class="vyv-shot-stage">
        <div class="vyv-phone">
          <div class="vyv-phone-bar"><span class="vyv-phone-notch"></span></div>
          <img class="vyv-phone-img" src="${src}" alt="${caption}"/>
        </div>
        <div class="vyv-shot-label">${caption}</div>
      </div>`;
  }

  const SLIDES = [
    {
      key: 'issues',
      eyebrow: 'Step 1',
      title: '9 Key Issues.<br/>Pick one — or all nine.',
      body: 'VoteYourViews.org distills every race down to 9 issues that matter most in Texas. You choose which ones matter to <em>you</em>.',
      render: () => `
        <div class="vyv-issue-grid">
          ${ISSUES.map(i => `
            <div class="vyv-issue-tile">
              <div class="vyv-issue-imgwrap">
                <img src="/icons/${i.id}.png" alt="${i.label}" onerror="this.style.display='none'"/>
              </div>
              <span>${i.label}</span>
            </div>`).join('')}
        </div>`,
    },
    {
      key: 'statements',
      eyebrow: 'Step 2',
      title: '3 Statements per Issue.',
      body: 'Each issue is a concise page with 3 belief statements. <strong>Agree</strong>, <strong>disagree</strong>, or <strong>skip</strong> each one. That\'s it — no essays, no jargon.',
      render: () => shot('/images/Tutorial%20Shots/3%20Statements.png', '3 Statements Example'),
    },
    {
      key: 'facts',
      eyebrow: 'Step 3',
      title: 'Get the Facts.',
      body: 'Every issue includes a non-partisan factual overview — one tap away. Know the context before you weigh in.',
      render: () => shot('/images/Tutorial%20Shots/Get%20the%20Facts.png', 'Issue Fact Example'),
    },
    {
      key: 'rank',
      eyebrow: 'Step 4',
      title: 'Rank How Much It Matters.',
      body: 'After the statements, slide the dial to tell us how strongly this issue drives your vote. Deal-breaker? Nice-to-have? You decide.',
      render: () => shot('/images/Tutorial%20Shots/Rank%20Your%20View.png', 'Rank Your View Example'),
    },
    {
      key: 'nine',
      eyebrow: 'Step 5',
      title: 'Answer 1 — or All 9.',
      body: 'Choose the issue(s) important to you and then choose <strong>Build My Ballot</strong>.',
      render: () => shot('/images/Tutorial%20Shots/9%20Views.png', 'Your views, filled in'),
    },
    {
      key: 'address',
      eyebrow: 'Step 6',
      title: 'Match Your Candidates.',
      body: 'Enter your address and we\'ll show only the candidates on <strong>your</strong> ballot — your districts, your races.',
      render: () => `
        <div class="vyv-shot-stage">
          <div class="vyv-xfade">
            <div class="vyv-xfade-slide vyv-xfade-a">
              <div class="vyv-phone">
                <div class="vyv-phone-bar"><span class="vyv-phone-notch"></span></div>
                <img class="vyv-phone-img" src="/images/Tutorial%20Shots/Address%20Modal.png" alt="Address lookup"/>
              </div>
            </div>
            <div class="vyv-xfade-slide vyv-xfade-b">
              <div class="vyv-xfade-or">OR</div>
              <div class="vyv-phone">
                <div class="vyv-phone-bar"><span class="vyv-phone-notch"></span></div>
                <img class="vyv-phone-img" src="/images/Tutorial%20Shots/Exploring.png" alt="Explore a county without an address"/>
              </div>
            </div>
          </div>
          <div class="vyv-xfade-captions">
            <div class="vyv-shot-label vyv-xfade-cap-a">Enter your address…</div>
            <div class="vyv-xfade-cap-b">
              <div class="vyv-shot-label" style="margin-top:10px">…or test drive a county</div>
              <div class="vyv-shot-label" style="margin-top:2px;color:#f59e0b">No address needed</div>
            </div>
          </div>
        </div>`,
    },
    {
      key: 'match',
      eyebrow: 'Step 7',
      title: 'Meet and Compare.',
      body: 'Meet the candidates who share your views and compare them to opponents quickly and easily.',
      render: () => `
        <div class="vyv-shot-stage">
          <div class="vyv-xfade">
            <div class="vyv-xfade-slide vyv-xfade-a">
              <div class="vyv-phone">
                <div class="vyv-phone-bar"><span class="vyv-phone-notch"></span></div>
                <img class="vyv-phone-img" src="/images/Tutorial%20Shots/Pre-Ballot.png" alt="Your matches, race by race"/>
              </div>
            </div>
            <div class="vyv-xfade-slide vyv-xfade-b">
              <div class="vyv-phone">
                <div class="vyv-phone-bar"><span class="vyv-phone-notch"></span></div>
                <img class="vyv-phone-img" src="/images/Tutorial%20Shots/Compare.png" alt="Compare candidates side-by-side"/>
              </div>
            </div>
          </div>
          <div class="vyv-xfade-captions">
            <div class="vyv-shot-label vyv-xfade-cap-a">Your matches — race by race</div>
            <div class="vyv-xfade-cap-b">
              <div class="vyv-shot-label" style="margin-top:10px">Compare side-by-side</div>
            </div>
          </div>
        </div>`,
    },
    {
      key: 'ballot',
      eyebrow: 'The Payoff',
      title: 'A Printable Ballot — With Everything You Need.',
      body: 'Not just your candidates — key election dates, your closest polling locations, and what to bring. All on one printable page you can take with you.',
      render: () => `
        <div class="vyv-shot-stage vyv-payoff-stage">
          <div class="vyv-paper vyv-pan-view">
            <img class="vyv-pan-img" src="/images/Tutorial%20Shots/Printable%20Ballot%20Full.jpg" alt="Printable ballot — picks, dates, polling locations"/>
          </div>
          <div class="vyv-shot-label">Your Picks · Key Dates · Polling Locations · What to Bring</div>
        </div>`,
    },
    {
      key: 'finale',
      eyebrow: "That's It",
      title: 'Ready? Let\'s Go.',
      body: 'This November, don\'t just vote, <strong>Vote Your Views!</strong>',
      render: () => `
        <div class="vyv-finale">
          <img src="/icons/VoteYourViews_SQ%20Logo.png" alt="VoteYourViews.org"/>
        </div>`,
    },
  ];

  const CSS = `
    .vyv-tour-overlay{position:fixed;inset:0;z-index:9999;background:rgba(2,6,23,0.85);backdrop-filter:blur(8px);display:none;align-items:center;justify-content:center;padding:16px;font-family:'Inter',system-ui,sans-serif;}
    .vyv-tour-overlay.open{display:flex;}
    .vyv-tour-modal{width:100%;max-width:480px;max-height:calc(100vh - 32px);background:linear-gradient(160deg,#1e1b4b 0%,#0f172a 100%);border:1px solid rgba(255,255,255,0.15);border-radius:24px;box-shadow:0 30px 80px rgba(0,0,0,0.6);display:flex;flex-direction:column;overflow:hidden;color:#e2e8f0;}
    .vyv-tour-head{display:flex;align-items:center;justify-content:space-between;padding:14px 18px;border-bottom:1px solid rgba(255,255,255,0.08);}
    .vyv-tour-brand{font-family:'Barlow Condensed',sans-serif;font-weight:900;font-size:14px;letter-spacing:0.12em;color:#fff;text-transform:uppercase;}
    .vyv-tour-brand span{color:#f59e0b;}
    .vyv-tour-close{background:rgba(255,255,255,0.08);border:none;color:#fff;width:32px;height:32px;border-radius:50%;font-size:16px;cursor:pointer;display:flex;align-items:center;justify-content:center;transition:background .2s;}
    .vyv-tour-close:hover{background:rgba(255,255,255,0.18);}
    .vyv-tour-body{flex:1;overflow-y:auto;padding:20px 22px 8px;}
    .vyv-slide{display:none;animation:vyvFade .35s ease;}
    .vyv-slide.active{display:block;}
    @keyframes vyvFade{from{opacity:0;transform:translateY(6px);}to{opacity:1;transform:none;}}
    .vyv-eyebrow{font-size:10px;font-weight:800;letter-spacing:0.22em;color:#f59e0b;text-transform:uppercase;margin-bottom:8px;}
    .vyv-title{font-family:'Barlow Condensed',sans-serif;font-weight:900;font-size:26px;line-height:1.05;letter-spacing:0.01em;color:#fff;text-transform:uppercase;margin-bottom:10px;}
    .vyv-body-text{font-size:14.5px;line-height:1.5;color:#cbd5e1;margin-bottom:16px;}
    .vyv-body-text strong{color:#fff;}
    .vyv-body-text em{color:#fbbf24;font-style:normal;font-weight:700;}
    .vyv-issue-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;padding:6px 0 14px;}
    .vyv-issue-tile{display:flex;flex-direction:column;align-items:center;gap:6px;}
    .vyv-issue-imgwrap{width:100%;aspect-ratio:1;border-radius:14px;overflow:hidden;background:linear-gradient(135deg,#1e3a8a,#7c2d12);box-shadow:0 4px 14px rgba(0,0,0,0.4);ring:1px solid rgba(255,255,255,0.1);}
    .vyv-issue-imgwrap img{width:100%;height:100%;object-fit:cover;display:block;}
    .vyv-issue-tile span{font-family:'Barlow Condensed',sans-serif;font-size:11px;font-weight:700;text-align:center;line-height:1.1;color:#cbd5e1;letter-spacing:0.02em;}
    .vyv-shot-stage{background:radial-gradient(ellipse at 50% 30%,rgba(245,158,11,0.14),rgba(59,130,246,0.08) 60%,transparent);border-radius:20px;padding:10px 8px 8px;margin-bottom:8px;}
    .vyv-phone{width:100%;max-width:360px;margin:0 auto;background:#000;border-radius:24px;padding:8px 8px 10px;border:2px solid rgba(255,255,255,0.35);box-shadow:0 18px 44px rgba(0,0,0,0.7),0 0 0 1px rgba(0,0,0,0.8);}
    .vyv-phone-bar{display:flex;justify-content:center;padding:4px 0 7px;}
    .vyv-phone-notch{width:64px;height:5px;border-radius:3px;background:rgba(255,255,255,0.35);}
    .vyv-phone-img{width:100%;display:block;border-radius:14px;}
    .vyv-shot-label{text-align:center;margin-top:10px;font-size:10px;font-weight:800;letter-spacing:0.2em;text-transform:uppercase;color:#94a3b8;}
    .vyv-xfade{position:relative;}
    .vyv-xfade-slide{opacity:0;transition:opacity .3s ease;}
    .vyv-xfade-slide.vyv-show{opacity:1;}
    .vyv-xfade-b{position:absolute;inset:0;display:flex;flex-direction:column;justify-content:center;}
    .vyv-xfade-b .vyv-phone{width:100%;}
    .vyv-xfade-captions{position:relative;height:3.4em;}
    .vyv-xfade-cap-a,.vyv-xfade-cap-b{position:absolute;left:0;right:0;top:0;opacity:0;transition:opacity .3s ease;}
    .vyv-xfade-cap-a.vyv-show,.vyv-xfade-cap-b.vyv-show{opacity:1;}
    .vyv-xfade-cap-a{color:#94a3b8;}
    .vyv-xfade-or{text-align:center;font-family:'Barlow Condensed',sans-serif;font-weight:900;font-size:28px;letter-spacing:0.25em;color:#fff;margin-bottom:10px;text-shadow:0 2px 12px rgba(0,0,0,0.6);}
    .vyv-placeholder{width:100%;padding:36px 20px;background:rgba(255,255,255,0.04);border:1px dashed rgba(255,255,255,0.2);border-radius:18px;text-align:center;font-family:'Barlow Condensed',sans-serif;font-weight:800;font-size:18px;letter-spacing:0.06em;color:#fff;text-transform:uppercase;margin-bottom:10px;}
    .vyv-placeholder span{display:block;font-size:11px;font-weight:600;color:#94a3b8;letter-spacing:0.15em;margin-top:6px;}
    .vyv-payoff{background:linear-gradient(135deg,rgba(245,158,11,0.15),rgba(59,130,246,0.12));border:1px solid rgba(245,158,11,0.4);}
    .vyv-payoff-stage{background:radial-gradient(ellipse at 50% 30%,rgba(245,158,11,0.18),rgba(59,130,246,0.08) 60%,transparent);}
    .vyv-paper{width:100%;max-width:340px;margin:0 auto;background:#fff;border-radius:6px;overflow:hidden;box-shadow:0 16px 40px rgba(0,0,0,0.65),0 2px 8px rgba(0,0,0,0.4);}
    .vyv-paper img{width:100%;display:block;}
    /* Payoff pan: slow tour down the printed ballot — picks, then Key Dates, then Polling + What to Bring */
    .vyv-pan-view{aspect-ratio:734/930;position:relative;}
    .vyv-pan-img{transform-origin:top left;animation:vyvBallotPan 12s ease-in-out infinite;will-change:transform;}
    @keyframes vyvBallotPan{
      0%,8%{transform:scale(1) translateY(0);}
      38%,72%{transform:scale(1.35) translateY(-57%);}
      100%{transform:scale(1) translateY(0);}
    }
    /* Finale: logo reveal */
    .vyv-finale{display:flex;align-items:center;justify-content:center;padding:10px 0 8px;perspective:900px;}
    .vyv-finale img{width:94%;max-width:400px;border-radius:24px;animation:vyvLogoIn 1.7s cubic-bezier(.16,1,.3,1) both, vyvLogoGlow 3s ease-in-out 1.7s infinite;}
    @keyframes vyvLogoIn{
      0%{opacity:0;transform:scale(.12) rotate(-14deg) translateY(60px);filter:blur(10px);}
      45%{opacity:1;filter:blur(0);}
      68%{transform:scale(1.07) rotate(2deg) translateY(-4px);}
      84%{transform:scale(.985) rotate(-.5deg) translateY(0);}
      100%{opacity:1;transform:scale(1) rotate(0) translateY(0);filter:blur(0);}
    }
    @keyframes vyvLogoGlow{0%,100%{box-shadow:0 18px 50px rgba(0,0,0,.6),0 0 0 rgba(245,158,11,0);}50%{box-shadow:0 18px 50px rgba(0,0,0,.6),0 0 56px rgba(245,158,11,.55);}}
    .vyv-tour-foot{padding:12px 18px 18px;border-top:1px solid rgba(255,255,255,0.08);display:flex;flex-direction:column;gap:12px;background:rgba(0,0,0,0.2);}
    .vyv-dots{display:flex;justify-content:center;gap:6px;}
    .vyv-dot{width:7px;height:7px;border-radius:50%;background:rgba(255,255,255,0.2);border:none;padding:0;cursor:pointer;transition:all .2s;}
    .vyv-dot.active{background:#f59e0b;width:22px;border-radius:4px;}
    .vyv-nav{display:flex;gap:10px;}
    .vyv-btn{flex:1;padding:12px 16px;border-radius:999px;border:none;font-weight:900;font-size:12px;letter-spacing:0.14em;text-transform:uppercase;cursor:pointer;transition:all .2s;font-family:'Inter',sans-serif;}
    .vyv-btn-prev{background:rgba(255,255,255,0.08);color:#fff;}
    .vyv-btn-prev:hover{background:rgba(255,255,255,0.15);}
    .vyv-btn-prev:disabled{opacity:0.35;cursor:default;}
    .vyv-btn-next{background:#f59e0b;color:#0f172a;}
    .vyv-btn-next:hover{background:#fbbf24;}
    .vyv-launcher{position:fixed;bottom:20px;right:20px;z-index:9998;background:linear-gradient(135deg,#f59e0b,#d97706);color:#0f172a;border:none;padding:12px 18px;border-radius:999px;font-weight:900;font-size:12px;letter-spacing:0.14em;text-transform:uppercase;cursor:pointer;box-shadow:0 8px 24px rgba(217,119,6,0.5);display:flex;align-items:center;gap:8px;font-family:'Inter',sans-serif;transition:transform .15s;}
    .vyv-launcher:hover{transform:translateY(-2px);}
    @media (max-width:420px){
      .vyv-tour-overlay{padding:10px;}
      .vyv-tour-body{padding:18px 14px 8px;}
      .vyv-title{font-size:22px;}
      .vyv-body-text{font-size:13.5px;}
      .vyv-issue-tile span{font-size:10px;}
      .vyv-launcher{padding:10px 14px;font-size:11px;}
    }
    /* ── Tablet + desktop: wide modal, text left / visual right ── */
    @media (min-width:768px){
      .vyv-tour-modal{max-width:920px;}
      .vyv-tour-body{padding:34px 40px 16px;display:flex;align-items:center;}
      .vyv-slide{width:100%;}
      .vyv-slide.active{display:flex;align-items:center;gap:44px;}
      .vyv-slide-text{flex:0 0 42%;min-width:0;}
      .vyv-slide-visual{flex:1;min-width:0;}
      .vyv-eyebrow{font-size:12px;margin-bottom:12px;}
      .vyv-title{font-size:40px;margin-bottom:14px;}
      .vyv-body-text{font-size:16px;line-height:1.6;margin-bottom:0;}
      .vyv-phone{max-width:380px;}
      .vyv-issue-grid{gap:14px;padding:0;}
      .vyv-issue-tile span{font-size:12px;}
      .vyv-paper{max-width:440px;}
      .vyv-finale img{max-width:400px;}
      .vyv-tour-foot{flex-direction:row;align-items:center;justify-content:space-between;padding:14px 40px 18px;}
      .vyv-dots{order:2;}
      .vyv-nav{order:1;gap:12px;}
      .vyv-btn{flex:none;padding:12px 26px;}
      .vyv-nav .vyv-btn-next{order:3;}
    }
  `;

  let currentIdx = 0;
  let overlay, dotsEl, prevBtn, nextBtn, slidesEls;
  let xfadeTimer = null;
  let xfadeSwapTimer = null;

  // Mini slideshow inside a slide: fade the current shot fully OUT, then fade the
  // next one in — never both visible at once. Restarts whenever the slide is shown.
  function startXfade(slideEl) {
    stopXfade();
    const xf = slideEl.querySelector('.vyv-xfade');
    if (!xf) return;
    const a = [slideEl.querySelector('.vyv-xfade-a'), slideEl.querySelector('.vyv-xfade-cap-a')];
    const b = [slideEl.querySelector('.vyv-xfade-b'), slideEl.querySelector('.vyv-xfade-cap-b')];
    let showA = true;
    a.forEach(el => el.classList.add('vyv-show'));
    b.forEach(el => el.classList.remove('vyv-show'));
    xfadeTimer = setInterval(() => {
      const out = showA ? a : b;
      const inn = showA ? b : a;
      showA = !showA;
      out.forEach(el => el.classList.remove('vyv-show'));
      xfadeSwapTimer = setTimeout(() => inn.forEach(el => el.classList.add('vyv-show')), 320);
    }, 2500);
  }
  function stopXfade() {
    if (xfadeTimer) { clearInterval(xfadeTimer); xfadeTimer = null; }
    if (xfadeSwapTimer) { clearTimeout(xfadeSwapTimer); xfadeSwapTimer = null; }
  }

  function build() {
    const style = document.createElement('style');
    style.textContent = CSS;
    document.head.appendChild(style);

    overlay = document.createElement('div');
    overlay.className = 'vyv-tour-overlay';
    overlay.innerHTML = `
      <div class="vyv-tour-modal" role="dialog" aria-label="VoteYourViews guided tour">
        <div class="vyv-tour-head">
          <span class="vyv-tour-brand">Vote<span>Your</span>Views · Tour</span>
          <button class="vyv-tour-close" aria-label="Close tour">✕</button>
        </div>
        <div class="vyv-tour-body">
          ${SLIDES.map((s, i) => `
            <div class="vyv-slide${i === 0 ? ' active' : ''}" data-idx="${i}">
              <div class="vyv-slide-text">
                <div class="vyv-eyebrow">${s.eyebrow}</div>
                <h2 class="vyv-title">${s.title}</h2>
                <p class="vyv-body-text">${s.body}</p>
              </div>
              <div class="vyv-slide-visual">${s.render()}</div>
            </div>`).join('')}
        </div>
        <div class="vyv-tour-foot">
          <div class="vyv-dots">${SLIDES.map((_, i) => `<button class="vyv-dot${i === 0 ? ' active' : ''}" data-idx="${i}" aria-label="Slide ${i + 1}"></button>`).join('')}</div>
          <div class="vyv-nav">
            <button class="vyv-btn vyv-btn-prev">← Back</button>
            <button class="vyv-btn vyv-btn-next">Next →</button>
          </div>
        </div>
      </div>
    `;
    document.body.appendChild(overlay);

    dotsEl = overlay.querySelectorAll('.vyv-dot');
    slidesEls = overlay.querySelectorAll('.vyv-slide');
    prevBtn = overlay.querySelector('.vyv-btn-prev');
    nextBtn = overlay.querySelector('.vyv-btn-next');

    overlay.querySelector('.vyv-tour-close').addEventListener('click', close);
    overlay.addEventListener('click', e => { if (e.target === overlay) close(); });
    prevBtn.addEventListener('click', () => go(currentIdx - 1));
    nextBtn.addEventListener('click', () => {
      if (currentIdx >= SLIDES.length - 1) return close();
      go(currentIdx + 1);
    });
    dotsEl.forEach(d => d.addEventListener('click', () => go(+d.dataset.idx)));
    document.addEventListener('keydown', e => {
      if (!overlay.classList.contains('open')) return;
      if (e.key === 'Escape') close();
      if (e.key === 'ArrowRight') go(currentIdx + 1);
      if (e.key === 'ArrowLeft') go(currentIdx - 1);
    });
  }

  function go(idx) {
    if (idx < 0 || idx >= SLIDES.length) return;
    currentIdx = idx;
    slidesEls.forEach((s, i) => s.classList.toggle('active', i === idx));
    dotsEl.forEach((d, i) => d.classList.toggle('active', i === idx));
    prevBtn.disabled = idx === 0;
    nextBtn.textContent = idx === SLIDES.length - 1 ? 'Get Started →' : 'Next →';
    overlay.querySelector('.vyv-tour-body').scrollTop = 0;
    startXfade(slidesEls[idx]);
    // Restart per-slide animations (ballot pan, finale logo) whenever their slide is shown
    slidesEls[idx].querySelectorAll('.vyv-pan-img, .vyv-finale img').forEach(el => {
      el.style.animation = 'none'; void el.offsetHeight; el.style.animation = '';
    });
  }

  function open() {
    if (!overlay) build();
    go(0);
    overlay.classList.add('open');
    document.body.style.overflow = 'hidden';
  }
  function close() {
    if (!overlay) return;
    stopXfade();
    overlay.classList.remove('open');
    document.body.style.overflow = '';
  }

  function addLauncher(opts) {
    opts = opts || {};
    const btn = document.createElement('button');
    btn.className = 'vyv-launcher';
    btn.innerHTML = '★ Take the Tour';
    btn.addEventListener('click', open);
    document.body.appendChild(btn);
    return btn;
  }

  window.VYVTutorial = { open, close, addLauncher };
})();
