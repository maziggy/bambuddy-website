/**
 * Commercial lead form handler (appliance / business pages).
 *
 * Progressive enhancement: the <form> works as a normal element, and this
 * script upgrades it to an async submit with inline status and Matomo
 * conversion tracking. If JS is off, the form still POSTs to /api/lead and the
 * endpoint returns JSON — not pretty, but not a dead end.
 *
 * Matomo: fires events under the "Lead" category so the funnel steps
 * (attempt -> success/error) are visible. It does NOT record the goal — the
 * relay does that server-side, because a browser with Do Not Track, a tracker
 * blocker or JS disabled still submits a lead but reports nothing. Firing the
 * goal in both places would double-count every lead from a tracked browser.
 */
(function () {
  'use strict';

  var ENDPOINT = '/api/lead';

  function track(action, name) {
    if (!window._paq) return;
    // value 4th arg omitted; name carries the interest bucket.
    window._paq.push(['trackEvent', 'Lead', action, name || '']);
  }

  function setStatus(el, kind, msg) {
    el.textContent = msg;
    el.className = 'lead-status is-visible is-' + kind;
  }

  /**
   * Qualifying answers, folded into the message body.
   *
   * The relay reads a fixed set of keys (interest, printers, timeframe, region,
   * email, message, website, context) and silently ignores anything else — and
   * `api/` is deliberately not carried by the website rsync, so a new field
   * would need a separate relay deploy to be seen at all. Until then it would
   * look like it worked and reach nobody. Prepending the answers to `message`
   * keeps them in the email that already gets sent, with no server change.
   *
   * With JS off the native POST carries the raw fields instead, and these two
   * answers are lost — the lead itself still arrives, exactly as before.
   */
  var EXTRA_FIELDS = [
    { name: 'use', label: 'Business or personal' },
    { name: 'trigger', label: 'What prompted this' }
  ];

  var LABELS = {
    business: 'Business — part of how they earn',
    institution: 'A school, university or makerspace',
    personal: 'Personal / hobby',
    outgrew: 'Outgrew how they track things today',
    incident: 'Something went wrong; wants cover',
    cloud: 'Needs to keep files off the cloud',
    evaluating: 'Evaluating options, nothing urgent',
    missing: 'Bambuddy is missing something they need'
  };

  function composeMessage(fd) {
    var body = fd.get('message') || '';
    var lines = [];
    for (var i = 0; i < EXTRA_FIELDS.length; i++) {
      var f = EXTRA_FIELDS[i];
      var v = fd.get(f.name);
      if (v) lines.push(f.label + ': ' + (LABELS[v] || v));
    }
    if (!lines.length) return body;
    return lines.join('\n') + (body ? '\n\n' + body : '');
  }

  /**
   * The two "what prompted this" answers that have historically arrived as bug
   * reports or feature requests rather than commercial enquiries. Picking one
   * reveals the GitHub route inline, at the moment before the person types the
   * report into the message box.
   *
   * Only the business form carries the hint element; the appliance form has no
   * .lead-route-hint and this is a no-op there. With JS off nothing is revealed
   * and the banner above the form carries the same message.
   */
  var ROUTE_HINT_TRIGGERS = ['missing', 'incident'];

  function wireRouteHint(form) {
    var hint = form.querySelector('.lead-route-hint');
    var trigger = form.querySelector('[name="trigger"]');
    if (!hint || !trigger) return null;

    function sync() {
      var show = ROUTE_HINT_TRIGGERS.indexOf(trigger.value) !== -1;
      hint.className = 'lead-route-hint' + (show ? ' is-visible' : '');
    }

    trigger.addEventListener('change', sync);
    // A back/forward navigation restores the previous selection without firing
    // change, so the hint would be out of step with the visible answer.
    sync();
    return sync;
  }

  function enhance(form) {
    var syncRouteHint = wireRouteHint(form);

    var btn = form.querySelector('.lead-submit-btn');
    var btnLabel = btn ? btn.querySelector('.lead-btn-label') : null;
    var status = form.querySelector('.lead-status');
    var context = form.getAttribute('data-context') || 'unknown';

    form.addEventListener('submit', function (e) {
      e.preventDefault();

      var fd = new FormData(form);
      var payload = {
        interest: fd.get('interest') || '',
        printers: fd.get('printers') || '',
        timeframe: fd.get('timeframe') || '',
        region: fd.get('region') || '',
        email: fd.get('email') || '',
        message: composeMessage(fd),
        website: fd.get('website') || '', // honeypot
        context: context
      };

      // Let the browser's native validation handle empties/format first.
      if (!form.reportValidity()) return;

      track('submit_attempt', payload.interest);

      if (btn) {
        btn.disabled = true;
        if (btnLabel) btnLabel.textContent = 'Sending...';
        var sp = document.createElement('span');
        sp.className = 'lead-spinner';
        btn.insertBefore(sp, btn.firstChild);
      }
      if (status) status.className = 'lead-status';

      fetch(ENDPOINT, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      })
        .then(function (res) {
          return res.json().then(function (body) {
            return { ok: res.ok, body: body };
          });
        })
        .then(function (r) {
          var msg = (r.body && r.body.message) || '';
          if (r.ok && r.body && r.body.success) {
            // Funnel step only. The "Commercial lead" goal is recorded by the
            // relay on a confirmed send — see the note at the top of this file.
            track('submit_success', payload.interest);
            form.reset();
            // reset() clears the select without firing change, which would
            // leave the hint visible under a blank answer.
            if (syncRouteHint) syncRouteHint();
            setStatus(status, 'success', msg || "Thanks — we'll be in touch shortly.");
            // Leave the button disabled (prevents an accidental resubmit) but
            // clear the spinner and show a settled label.
            if (btn) {
              var done = btn.querySelector('.lead-spinner');
              if (done) done.remove();
              if (btnLabel) btnLabel.textContent = 'Sent';
            }
          } else {
            track('submit_error', payload.interest);
            setStatus(status, 'error', msg || 'Something went wrong. Please email us directly.');
            restore();
          }
        })
        .catch(function () {
          track('submit_error', payload.interest);
          setStatus(status, 'error', 'Network error. Please email us directly.');
          restore();
        });

      function restore() {
        if (!btn) return;
        btn.disabled = false;
        var sp = btn.querySelector('.lead-spinner');
        if (sp) sp.remove();
        if (btnLabel) btnLabel.textContent = btn.getAttribute('data-label') || 'Send';
      }
    });
  }

  document.addEventListener('DOMContentLoaded', function () {
    var forms = document.querySelectorAll('form.lead-form');
    for (var i = 0; i < forms.length; i++) enhance(forms[i]);
  });
})();
