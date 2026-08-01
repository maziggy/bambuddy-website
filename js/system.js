/* Bambuddy — progressive enhancement for the new system.
   Everything here is additive: with JS off, the page is a clean stacked
   document (see the base styles in css/system.css). */
(function () {
  'use strict';

  var reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ---- mobile nav disclosure ---- */
  var toggle = document.querySelector('.nav-toggle');
  var links = document.querySelector('.nav-links');
  if (toggle && links) {
    toggle.addEventListener('click', function () {
      var open = links.classList.toggle('is-open');
      toggle.setAttribute('aria-expanded', String(open));
    });
    links.addEventListener('click', function (e) {
      if (e.target.closest('a')) {
        links.classList.remove('is-open');
        toggle.setAttribute('aria-expanded', 'false');
      }
    });
  }

  /* ---- "More" disclosure ----
     Only wired above the mobile breakpoint; below it the panel is laid out
     statically by CSS and the button is hidden, so there is nothing to
     toggle. */
  var moreBtn = document.querySelector('.nav-more-btn');
  var morePanel = document.getElementById('nav-more-panel');
  if (moreBtn && morePanel) {
    var closeMore = function () {
      morePanel.classList.remove('is-open');
      moreBtn.setAttribute('aria-expanded', 'false');
    };

    moreBtn.addEventListener('click', function (e) {
      e.stopPropagation();
      var open = morePanel.classList.toggle('is-open');
      moreBtn.setAttribute('aria-expanded', String(open));
    });

    document.addEventListener('click', function (e) {
      if (!morePanel.contains(e.target) && e.target !== moreBtn) closeMore();
    });

    document.addEventListener('keydown', function (e) {
      if (e.key !== 'Escape' || !morePanel.classList.contains('is-open')) return;
      closeMore();
      moreBtn.focus();
    });

    /* Tabbing out of the panel should close it, or the open menu follows the
       reader down the page. */
    morePanel.addEventListener('focusout', function (e) {
      if (!morePanel.contains(e.relatedTarget) && e.relatedTarget !== moreBtn) closeMore();
    });
  }

  /* ---- reveal on enter ---- */
  var revealables = document.querySelectorAll('.reveal');
  if (revealables.length && 'IntersectionObserver' in window && !reduced) {
    var revealObserver = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) {
            entry.target.classList.add('is-in');
            revealObserver.unobserve(entry.target);
          }
        });
      },
      { rootMargin: '0px 0px -12% 0px', threshold: 0.05 }
    );
    revealables.forEach(function (el) {
      revealObserver.observe(el);
    });
  } else {
    revealables.forEach(function (el) {
      el.classList.add('is-in');
    });
  }

  /* ---- copy-to-clipboard on code blocks ----
     Ported from main.js, which converted pages no longer load: it drives the
     nav and reveal with different class names (.active / .visible) and would
     fight system.js over both. */
  document.querySelectorAll('.code-copy').forEach(function (button) {
    button.addEventListener('click', function () {
      var block = button.closest('.code-block');
      var code = block && block.querySelector('code');
      if (!code || !navigator.clipboard) return;

      navigator.clipboard.writeText(code.textContent.trim()).then(
        function () {
          var original = button.innerHTML;
          button.classList.add('copied');
          button.innerHTML = 'Copied';
          setTimeout(function () {
            button.classList.remove('copied');
            button.innerHTML = original;
          }, 1800);
        },
        function () {
          /* Clipboard denied (insecure origin, or the user refused). Say so
             rather than silently doing nothing — the whole point of the button
             is that the reader does not have to select the text by hand. */
          var original = button.innerHTML;
          button.innerHTML = 'Press Ctrl+C';
          setTimeout(function () {
            button.innerHTML = original;
          }, 2200);
        }
      );
    });
  });

  /* ---- sticky walkthrough ----
     The media column is pinned by CSS `position: sticky`; this only
     decides which frame is showing. No scroll hijacking: the page
     scrolls at the reader's own pace throughout. */
  document.querySelectorAll('[data-walk]').forEach(function (walk) {
    var steps = Array.prototype.slice.call(walk.querySelectorAll('.walk-step'));
    var frames = Array.prototype.slice.call(walk.querySelectorAll('.walk-frame img'));
    if (!steps.length || !frames.length) return;

    function activate(index) {
      steps.forEach(function (step, i) {
        step.classList.toggle('is-active', i === index);
      });
      frames.forEach(function (frame, i) {
        frame.classList.toggle('is-active', i === index);
      });
    }

    activate(0);

    if (!('IntersectionObserver' in window)) return;

    var stepObserver = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) {
            activate(steps.indexOf(entry.target));
          }
        });
      },
      /* A band across the middle of the viewport: a step takes over as
         it crosses the centre line, which is where the reader's eye is. */
      { rootMargin: '-45% 0px -45% 0px', threshold: 0 }
    );
    steps.forEach(function (step) {
      stepObserver.observe(step);
    });
  });
})();
