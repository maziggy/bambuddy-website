/**
 * Anonymous Matomo tracker loader
 * - Server-side enforced: no cookies (Matomo admin: "Force tracking without cookies")
 * - Respects Do Not Track
 * - IPs anonymized server-side (2 bytes)
 * - Raw data deleted after 180 days
 * GDPR basis: Art. 6(1)(f) legitimate interest — no consent required.
 */
(function () {
  'use strict';
  var _paq = window._paq = window._paq || [];
  _paq.push(['setDoNotTrack', true]);
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
})();
