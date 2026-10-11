/* Just Halloween Crafts – small progressive enhancements */
(function () {
  // Days until Halloween (home page)
  var num = document.getElementById('count-num');
  if (num) {
    var label = document.getElementById('count-label');
    var now = new Date();
    var today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    var target = new Date(now.getFullYear(), 9, 31);
    if (today > target) target = new Date(now.getFullYear() + 1, 9, 31);
    var days = Math.round((target - today) / 86400000);
    if (days === 0) {
      num.textContent = 'Today';
      label.textContent = 'Happy Halloween!';
    } else {
      num.textContent = days;
      label.textContent = days === 1 ? 'day until Halloween' : 'days until Halloween';
    }
  }

  // Load YouTube videos only when clicked
  document.addEventListener('click', function (e) {
    var btn = e.target.closest && e.target.closest('.yt-play');
    if (!btn) return;
    var box = btn.parentNode;
    var id = box.getAttribute('data-id');
    var f = document.createElement('iframe');
    f.src = 'https://www.youtube-nocookie.com/embed/' + id + '?autoplay=1&rel=0';
    f.title = 'YouTube video';
    f.allow = 'accelerometer; autoplay; encrypted-media; gyroscope; picture-in-picture';
    f.allowFullscreen = true;
    box.innerHTML = '';
    box.appendChild(f);
  });

  // Cookie notice
  var bar = document.getElementById('cookie');
  if (bar) {
    var seen = false;
    try { seen = localStorage.getItem('jhc-cookie') === '1'; } catch (err) { seen = false; }
    if (!seen) bar.hidden = false;
    document.getElementById('cookie-ok').addEventListener('click', function () {
      bar.hidden = true;
      try { localStorage.setItem('jhc-cookie', '1'); } catch (err) {}
    });
  }
})();
