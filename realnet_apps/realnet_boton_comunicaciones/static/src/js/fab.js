(function(){
  const root   = document.getElementById('fab-root');
  if(!root){ return; }
  const mainBtn= document.getElementById('fab-main');
  const mainIcon = document.getElementById('fab-main-icon');
  const overlay= document.getElementById('fab-overlay');
  const menu   = document.getElementById('fab-menu');
  const bubble = document.getElementById('fab-bubble');
  const chatLink = document.getElementById('fab-chatbot-link');

  const html = document.documentElement;
  const inEditor = html && (html.classList.contains('o_editable') || html.classList.contains('o_is_website_editor'));

  const restartPulse = () => {
    if(!mainBtn) return;
    mainBtn.style.animation = 'none';
    void mainBtn.offsetWidth;
    mainBtn.style.animation = '';
  };

  const openMenu = () => {
    root.classList.add('open');
    mainBtn && mainBtn.setAttribute('aria-expanded','true');
    menu && menu.setAttribute('aria-hidden','false');
    overlay && overlay.setAttribute('aria-hidden','false');
    if (mainIcon && mainIcon.dataset.iconOpen) mainIcon.src = mainIcon.dataset.iconOpen;
    bubble && bubble.classList.remove('show');
  };
  const closeMenu = () => {
    root.classList.remove('open');
    mainBtn && mainBtn.setAttribute('aria-expanded','false');
    menu && menu.setAttribute('aria-hidden','true');
    overlay && overlay.setAttribute('aria-hidden','true');
    if (mainIcon && mainIcon.dataset.iconDefault) mainIcon.src = mainIcon.dataset.iconDefault;
    restartPulse();
  };

  mainBtn && mainBtn.addEventListener('click', () => root.classList.contains('open') ? closeMenu() : openMenu());
  overlay && overlay.addEventListener('click', closeMenu);
  document.addEventListener('keydown', e => { if(e.key==='Escape') closeMenu(); });

  window.addEventListener('load', () => { setTimeout(() => bubble && bubble.classList.add('show'), 1000); });

  document.querySelectorAll('#fab-menu img').forEach(img=>{
    img.addEventListener('error', ()=>{
      img.alt = (img.alt||'icono')+' (no encontrado)';
      img.style.opacity='.7';
    });
  });

  function hideLivechatButtonOnce(host){
    try{
      const shadow = host && host.shadowRoot;
      if(!shadow) return;
      const btn = shadow.querySelector('.o-livechat-LivechatButton');
      if(btn){
        btn.style.setProperty('display','none','important');
        btn.setAttribute('aria-hidden','true');
      }
    }catch(_e){/* no-op */}
  }
  function setupHideDefaultLivechat(){
    const attachShadowObserver = (host) => {
      hideLivechatButtonOnce(host);
      const shadow = host && host.shadowRoot;
      if(!shadow) return;
      const obs = new MutationObserver(() => hideLivechatButtonOnce(host));
      obs.observe(shadow, { childList:true, subtree:true });
    };
    const host = document.querySelector('.o-livechat-root');
    if(host){
      attachShadowObserver(host);
      return;
    }
    const hostObs = new MutationObserver((_, observer) => {
      const h = document.querySelector('.o-livechat-root');
      if(h){
        attachShadowObserver(h);
        observer.disconnect();
      }
    });
    hostObs.observe(document.documentElement || document.body, { childList:true, subtree:true });
  }
  if(document.readyState === 'loading'){
    document.addEventListener('DOMContentLoaded', setupHideDefaultLivechat);
  } else {
    setupHideDefaultLivechat();
  }

  async function openOdooLivechat(){
    const win = window;
    const waitReady = () => new Promise((resolve) => {
      if (win.odoo && win.odoo.livechatReady && typeof win.odoo.livechatReady.then === 'function') {
        win.odoo.livechatReady.then(resolve).catch(resolve);
      } else {
        resolve();
      }
    });
    try {
      await waitReady();
      const svc = win?.odoo?.services?.["im_livechat.livechat"] || win?.odoo?.__owl__?.services?.["im_livechat.livechat"];
      if (svc && typeof svc.open === 'function') {
        await svc.open();
        return true;
      }
      const livechatRoot = document.querySelector('.o-livechat-root');
      const shadow = livechatRoot && livechatRoot.shadowRoot;
      const btn = shadow && shadow.querySelector('.o-livechat-LivechatButton');
      if (btn) {
        btn.click();
        return true;
      }
    } catch(_e) {
    }
    return false;
  }

  chatLink && chatLink.addEventListener('click', async (e) => {
    e.preventDefault();
    if (inEditor) { closeMenu(); return; }
    closeMenu();
    const opened = await openOdooLivechat();
    if (!opened) {
      try {
        const url = new URL(window.location.href);
        url.searchParams.set('chat','open');
        url.hash = 'chatbot';
        window.location.href = url.toString();
      } catch(_) {
      }
    }
  });
})();
