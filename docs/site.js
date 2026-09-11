'use strict';
function presetFor(key) {
  const presets = {
    portal: {name:'Portal', limit:'500 KB', paper:'Original', margin:'0 pt', profile:'Small File', note:'A tighter starting point for upload portals.'},
    application: {name:'Application', limit:'2 MB', paper:'A4', margin:'24 pt', profile:'Balanced', note:'Consistent pages for your next application.'},
    photo: {name:'Photo', limit:'10 MB', paper:'Original', margin:'0 pt', profile:'Balanced', note:'Keep the image proportions. Give detail more room.'}
  };
  return Object.hasOwn(presets, key) ? presets[key] : null;
}
if (typeof module !== 'undefined') module.exports = {presetFor};
if (typeof document !== 'undefined') {
  const buttons = document.querySelectorAll('[data-preset]');
  for (const button of buttons) button.addEventListener('click', () => {
    const preset = presetFor(button.dataset.preset);
    if (!preset) return;
    for (const peer of buttons) peer.setAttribute('aria-pressed', String(peer === button));
    for (const field of ['name','limit','paper','margin','profile','note']) {
      document.getElementById('demo-' + field).textContent = preset[field];
    }
    document.querySelector('.demo').dataset.mode = button.dataset.preset;
  });
}
