"""Build get.bambuddy.cool from the main-site pages.

The appliance is sold through Paddle, whose domain review wants a site about the
product it sells and nothing else. So the subdomain gets its own copy of the
appliance page and the legal pages, with a header and footer that carry only the
appliance, and every other link pointing back to bambuddy.cool.

It also writes pay.html, the page Paddle opens checkouts on (Paddle's "default
payment link"). The Paddle settings for it are in PADDLE below.

Run after editing appliance.html, privacy-policy.html or legal-notice.html:

    python3 tools/build_appliance_site.py

The terms and refund pages are generated into appliance/ by
bambuddy-appliance/docs/legal/build_terms_pages.py and build_refund_page.py,
which use appliance/legal-notice.html as their template -- so run this first.
Then build_terms_pdfs.py there prints them to assets/downloads/ for the licence
key email.
"""

import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "appliance")
MAIN = "https://bambuddy.cool"
SUB = "https://get.bambuddy.cool"

# source page on the main site -> page on the subdomain
PAGES = {
    "appliance.html": "index.html",
    "privacy-policy.html": "privacy-policy.html",
    "legal-notice.html": "legal-notice.html",
}

# Paddle checkout. The client-side token is public by design -- it ends up in the
# page source either way. The API key and the webhook secret never go here.
PADDLE = {
    "environment": "sandbox",  # "sandbox" or "production"
    "token": "test_25eddac35c0daf9d5a49937875b",  # client-side token: test_... for sandbox, live_... for production
}

# Pages that exist on the subdomain, so relative links to them stay relative.
LOCAL = {"privacy-policy.html", "legal-notice.html", "terms.html", "terms-de.html", "refund-policy.html"}

HEADER = """<header class="nav">
    <div class="shell nav-inner">
      <a href="/" class="nav-logo" aria-label="Bambuddy Appliance home">
        <img src="assets/img/logo_transparent.png" alt="Bambuddy">
      </a>

      <nav class="nav-links" id="nav-links">
        <a href="/#hardware" class="nav-link">Hardware</a>
        <a href="/#guide" class="nav-link">Setup</a>
        <a href="/#pricing" class="nav-link">Pricing</a>
        <a href="/#support" class="nav-link">Support</a>
        <a href="/#telemetry" class="nav-link">What it sends</a>

        <span class="nav-sep" aria-hidden="true"></span>

        <a href="https://bambuddy.cool/" class="nav-pill">Bambuddy</a>
      </nav>

      <div class="nav-actions">
        <a href="/#buy" class="btn btn-primary">Get notified</a>
        <button class="nav-toggle" aria-label="Toggle navigation" aria-expanded="false" aria-controls="nav-links">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="22" height="22" aria-hidden="true">
            <line x1="3" y1="7" x2="21" y2="7"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="17" x2="21" y2="17"/>
          </svg>
        </button>
      </div>
    </div>
  </header>"""

FOOTER = """<footer class="footer">
    <div class="shell">
      <div class="footer-grid">
        <div class="footer-brand">
          <a href="/" aria-label="Bambuddy Appliance home">
            <img src="assets/img/logo_transparent.png" alt="Bambuddy">
          </a>
          <p>The Bambuddy Appliance: a Raspberry Pi 5 image you flash yourself, with updates that undo themselves.</p>
        </div>

        <div class="footer-col">
          <h4>Appliance</h4>
          <a href="/#hardware">Hardware</a>
          <a href="/#guide">Setup</a>
          <a href="/#pricing">Pricing</a>
          <a href="/#support">Support</a>
          <a href="assets/downloads/bambuddy-appliance-quickstart.pdf">Quickstart (PDF)</a>
        </div>
        <div class="footer-col">
          <h4>Bambuddy</h4>
          <a href="https://bambuddy.cool/">bambuddy.cool</a>
          <a href="https://bambuddy.cool/installation.html">Install it yourself, free</a>
          <a href="http://wiki.bambuddy.cool" target="_blank" rel="noopener">Documentation</a>
          <a href="https://github.com/maziggy/bambuddy" target="_blank" rel="noopener">GitHub</a>
        </div>
        <div class="footer-col">
          <h4>Contact</h4>
          <a href="mailto:support@bambuddy.cool">support@bambuddy.cool</a>
          <a href="/#buy">Questions before buying</a>
        </div>
      </div>

      <div class="footer-bottom">
        <p>
          Sold through our online reseller Paddle.com, the Merchant of Record for all our orders.<br>
          &copy; 2026 Martin Ziegler. Bambuddy is released under the AGPL-3.0 License. Not affiliated with Bambu Lab.
        </p>
        <div class="footer-legal">
          <a href="legal-notice.html">Legal notice</a>
          <a href="privacy-policy.html">Privacy policy</a>
          <a href="terms.html">Terms</a>
          <a href="refund-policy.html">Refund policy</a>
        </div>
      </div>
    </div>
  </footer>"""


def rewrite_link(match: re.Match) -> str:
    attr, target = match.group(1), match.group(2)
    page, _, anchor = target.partition("#")
    anchor = f"#{anchor}" if anchor else ""
    if page == "appliance.html":
        return f'{attr}="/{anchor}"'
    if page == "index.html":
        return f'{attr}="{MAIN}/{anchor}"'
    if page in LOCAL:
        return match.group(0)
    return f'{attr}="{MAIN}/{page}{anchor}"'


def build(source: str, target: str) -> None:
    html = open(os.path.join(ROOT, source)).read()

    head_end = html.index("<header")
    header_end = html.index("</header>") + len("</header>")
    footer_start = html.index('<footer class="footer">')
    footer_end = html.index("</footer>") + len("</footer>")

    head = html[:head_end]
    main = html[header_end:footer_start]
    tail = html[footer_end:]

    sub_url = f"{SUB}/" if target == "index.html" else f"{SUB}/{target}"
    head = head.replace(f"{MAIN}/{source}", sub_url).replace(f"{SUB}/appliance.html", sub_url)

    main = re.sub(r'(href)="((?!https?:|mailto:|#|/|assets/|css/|js/|img/|fonts/)[\w-]+\.html(?:#[\w-]*)?)"', rewrite_link, main)
    main = main.replace(f"{SUB}/terms.html", "terms.html").replace(f"{SUB}/refund-policy.html", "refund-policy.html")

    open(os.path.join(OUT, target), "w").write(head + HEADER + main + FOOTER + tail)


PAY_MAIN = """<main>
    <section class="page-head">
      <div class="shell">
        <p class="label label-signal">Checkout</p>
        <h1 id="pay-title">Opening secure checkout&hellip;</h1>
      </div>
    </section>

    <section class="band-tight">
      <div class="shell">
        <div class="article" style="max-width: 78ch;">
        <p class="lead" id="pay-text">The payment form is provided by Paddle.com, our online reseller and the Merchant of Record for all our orders. It opens on top of this page.</p>
        <p id="pay-fallback">If nothing opens, check that your browser is not blocking scripts from cdn.paddle.com, or go back to the <a href="/#pricing">pricing</a> and try again. Questions: <a href="mailto:support@bambuddy.cool">support@bambuddy.cool</a>.</p>
        <p class="svc-note">By paying you agree to the <a href="terms.html">subscription terms</a>. Full refund within 14 days, no reason needed: <a href="refund-policy.html">refund policy</a>.</p>
        </div>
      </div>
    </section>
  </main>"""

PAY_SCRIPT = """
  <script src="https://cdn.paddle.com/paddle/v2/paddle.js"></script>
  <script>
  (function () {
    var config = __PADDLE__;
    var title = document.getElementById('pay-title');
    var text = document.getElementById('pay-text');
    var params = new URLSearchParams(window.location.search);
    var transaction = params.get('_ptxn');
    var price = params.get('price');

    function show(heading, body) {
      title.textContent = heading;
      text.textContent = body;
    }

    if (!config.token || typeof Paddle === 'undefined') {
      show('Checkout is not available right now',
        'Please try again later, or write to support@bambuddy.cool.');
      return;
    }
    if (!transaction && !/^pri_[a-z0-9]{26}$/.test(price || '')) {
      show('Nothing to pay here',
        'Choose a plan on the pricing section to start a checkout.');
      return;
    }

    if (config.environment === 'sandbox') Paddle.Environment.set('sandbox');
    Paddle.Initialize({
      token: config.token,
      checkout: { settings: { displayMode: 'overlay', theme: 'dark', locale: 'en' } },
      eventCallback: function (event) {
        if (event.name === 'checkout.completed') {
          show('Thank you',
            'Your order is complete. Your licence key and the download link arrive by email within a few minutes.');
        } else if (event.name === 'checkout.closed') {
          show('Checkout closed', 'Nothing was charged. You can go back to the pricing and start again.');
        }
      }
    });

    // With _ptxn in the URL Paddle.js opens that transaction by itself.
    if (!transaction) Paddle.Checkout.open({ items: [{ priceId: price, quantity: 1 }] });
  })();
  </script>
"""


def build_pay() -> None:
    """pay.html: the legal notice's head and chrome around the checkout page."""
    import json

    html = open(os.path.join(OUT, "legal-notice.html")).read()
    head = html[: html.index("<main>")]
    tail = html[html.index("</main>") + len("</main>") :]

    head = head.replace(f"{SUB}/legal-notice.html", f"{SUB}/pay.html")
    head = head.replace("Legal Notice - Bambuddy", "Checkout - Bambuddy Appliance")
    head = re.sub(r'content="Legal notice and provider identification[^"]*"', 'content="Checkout for the Bambuddy Appliance subscription."', head)
    head = head.replace('<meta name="viewport"', '<meta name="robots" content="noindex">\n  <meta name="viewport"', 1)

    script = PAY_SCRIPT.replace("__PADDLE__", json.dumps(PADDLE))
    tail = tail.replace("</body>", script + "</body>", 1)
    open(os.path.join(OUT, "pay.html"), "w").write(head + PAY_MAIN + tail)


def main() -> None:
    for source, target in PAGES.items():
        build(source, target)
    build_pay()
    print(f"built {len(PAGES) + 1} pages into {OUT}")


if __name__ == "__main__":
    main()
