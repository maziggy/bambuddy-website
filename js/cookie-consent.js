/**
 * Cookie Consent Banner
 * GDPR-compliant: Matomo tracking only starts after explicit consent.
 */
(function () {
  'use strict';

  var CONSENT_KEY = 'bb_cookie_consent';

  function getConsent() {
    try { return localStorage.getItem(CONSENT_KEY); } catch (e) { return null; }
  }

  function setConsent(value) {
    try { localStorage.setItem(CONSENT_KEY, value); } catch (e) { /* ignore */ }
  }

  function enableMatomo() {
    var _paq = window._paq = window._paq || [];
    _paq.push(['setDocumentTitle', document.domain + '/' + document.title]);
    _paq.push(['trackPageView']);
    _paq.push(['enableLinkTracking']);
    (function () {
      var u = '/t/';
      _paq.push(['setTrackerUrl', u + 't.php']);
      _paq.push(['setSiteId', window.__matomoSiteId || '1']);
      var d = document, g = d.createElement('script'), s = d.getElementsByTagName('script')[0];
      g.async = true; g.src = u + 't.js'; s.parentNode.insertBefore(g, s);
    })();
  }

  function disableMatomo() {
    var _paq = window._paq = window._paq || [];
    _paq.push(['optUserOut']);
  }

  function hideBanner() {
    var el = document.getElementById('cookie-banner');
    if (el) el.style.display = 'none';
  }

  function showBanner() {
    var el = document.getElementById('cookie-banner');
    if (el) el.style.display = '';
  }

  // Create the banner HTML
  function createBanner() {
    var banner = document.createElement('div');
    banner.id = 'cookie-banner';
    banner.setAttribute('role', 'dialog');
    banner.setAttribute('aria-label', 'Cookie consent');
    banner.innerHTML =
      '<div class="cookie-banner-inner">' +
        '<p>We use cookies to analyze website traffic with <strong>Matomo</strong> (self-hosted, no third-party sharing). ' +
        'See our <a href="privacy-policy.html">Privacy Policy</a> for details.</p>' +
        '<div class="cookie-banner-buttons">' +
          '<button id="cookie-reject" class="cookie-btn cookie-btn-reject">Reject</button>' +
          '<button id="cookie-accept" class="cookie-btn cookie-btn-accept">Accept</button>' +
        '</div>' +
      '</div>';
    document.body.appendChild(banner);

    document.getElementById('cookie-accept').addEventListener('click', function () {
      setConsent('accepted');
      hideBanner();
      enableMatomo();
    });

    document.getElementById('cookie-reject').addEventListener('click', function () {
      setConsent('rejected');
      hideBanner();
      disableMatomo();
    });
  }

  // Init
  var consent = getConsent();
  if (consent === 'accepted') {
    enableMatomo();
  } else if (consent === 'rejected') {
    // Do nothing — no tracking
  } else {
    // No choice yet — show banner, don't track
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', function () { createBanner(); });
    } else {
      createBanner();
    }
  }
})();
