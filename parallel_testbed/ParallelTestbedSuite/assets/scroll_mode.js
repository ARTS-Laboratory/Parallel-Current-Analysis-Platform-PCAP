(function () {
  window.latestScrollMode = 'pause';

  window.addEventListener('message', function (event) {
    if (event.data && event.data.type === 'scroll-mode') {
      window.latestScrollMode = event.data.mode;
      console.log("Scroll mode updated:", window.latestScrollMode);
    }
  });

  function postScrollMode(mode) {
    window.postMessage({ type: 'scroll-mode', mode: mode }, '*');
  }

  document.addEventListener('mousedown', function (e) {
    if (e.target.id === 'btn-back') postScrollMode('back');
    if (e.target.id === 'btn-forward') postScrollMode('forward');
  });

  document.addEventListener('mouseup', function (e) {
    if (e.target.id === 'btn-back' || e.target.id === 'btn-forward') {
      postScrollMode('pause');
    }
  });

  document.addEventListener('mouseleave', function (e) {
    if (e.target.id === 'btn-back' || e.target.id === 'btn-forward') {
      postScrollMode('pause');
    }
  });

  document.addEventListener('touchstart', function (e) {
    if (e.target.id === 'btn-back') postScrollMode('back');
    if (e.target.id === 'btn-forward') postScrollMode('forward');
  });

  document.addEventListener('touchend', function (e) {
    if (e.target.id === 'btn-back' || e.target.id === 'btn-forward') {
      postScrollMode('pause');
    }
  });

  console.log("✅ Delegated scroll listeners attached.");
})();