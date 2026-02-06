/* ============================================
   Bambuddy Website - Reviews Module
   Supabase REST client + review UI logic
   ============================================ */

const SUPABASE_CONFIG = {
  url: 'https://YOUR_PROJECT.supabase.co',
  anonKey: 'YOUR_ANON_KEY'
};

/* ---- Supabase REST helpers ---- */

function supabaseRequest(endpoint, options = {}) {
  const url = `${SUPABASE_CONFIG.url}/rest/v1/${endpoint}`;
  const headers = {
    'apikey': SUPABASE_CONFIG.anonKey,
    'Authorization': `Bearer ${SUPABASE_CONFIG.anonKey}`,
    'Content-Type': 'application/json',
    ...options.headers
  };
  return fetch(url, { ...options, headers });
}

async function fetchReviews({ featuredOnly = false, limit = 50 } = {}) {
  let endpoint = 'reviews?approved=eq.true&order=created_at.desc';
  if (featuredOnly) endpoint += '&featured=eq.true';
  if (limit) endpoint += `&limit=${limit}`;

  const res = await supabaseRequest(endpoint, {
    headers: { 'Accept': 'application/json' }
  });
  if (!res.ok) throw new Error(`Failed to fetch reviews: ${res.status}`);
  return res.json();
}

async function submitReview({ rating, review_text, reviewer_name }) {
  const body = {
    rating,
    review_text,
    reviewer_name: reviewer_name || null,
    approved: false,
    featured: false
  };
  const res = await supabaseRequest('reviews', {
    method: 'POST',
    headers: { 'Prefer': 'return=minimal' },
    body: JSON.stringify(body)
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `Submit failed: ${res.status}`);
  }
}

/* ---- XSS prevention ---- */

function escapeHTML(str) {
  const div = document.createElement('div');
  div.appendChild(document.createTextNode(str));
  return div.innerHTML;
}

/* ---- Date formatting ---- */

function formatReviewDate(isoDate) {
  const d = new Date(isoDate);
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

/* ---- Star rendering ---- */

function renderStars(rating) {
  let html = '';
  for (let i = 1; i <= 5; i++) {
    if (i <= rating) {
      html += '<svg class="review-star star-filled" viewBox="0 0 24 24" fill="currentColor"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>';
    } else {
      html += '<svg class="review-star star-empty" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>';
    }
  }
  return html;
}

/* ---- Card HTML ---- */

function createReviewCardHTML(review, index) {
  const name = review.reviewer_name ? escapeHTML(review.reviewer_name) : 'Anonymous';
  const initial = name.charAt(0).toUpperCase();
  const text = escapeHTML(review.review_text);
  const date = formatReviewDate(review.created_at);
  const delay = Math.min(index * 0.1, 0.6);

  return `
    <div class="review-card reveal" style="transition-delay: ${delay}s;">
      <div class="review-stars">${renderStars(review.rating)}</div>
      <p class="review-text">${text}</p>
      <div class="review-author">
        <div class="review-avatar">${initial}</div>
        <div>
          <span class="review-name">${name}</span>
          <span class="review-date">${date}</span>
        </div>
      </div>
    </div>`;
}

/* ---- Render cards into container ---- */

function renderReviewCards(reviews, container) {
  if (!reviews || reviews.length === 0) {
    container.innerHTML = `
      <div class="reviews-empty-state">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="48" height="48">
          <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/>
        </svg>
        <h3>No Reviews Yet</h3>
        <p>Be the first to share your experience with Bambuddy!</p>
      </div>`;
    return;
  }
  container.innerHTML = reviews.map((r, i) => createReviewCardHTML(r, i)).join('');
  initScrollRevealForNew(container);
}

/* ---- Review stats ---- */

function renderReviewStats(reviews) {
  const container = document.getElementById('review-stats');
  if (!container) return;

  if (!reviews || reviews.length === 0) {
    container.style.display = 'none';
    return;
  }

  const total = reviews.length;
  const avg = (reviews.reduce((sum, r) => sum + r.rating, 0) / total).toFixed(1);

  container.innerHTML = `
    <div class="review-stats reveal">
      <div class="review-stat-item">
        <span class="review-stat-value">${avg}</span>
        <div class="review-stars">${renderStars(Math.round(avg))}</div>
        <span class="review-stat-label">Average Rating</span>
      </div>
      <div class="review-stat-item">
        <span class="review-stat-value">${total}</span>
        <span class="review-stat-label">Total Review${total !== 1 ? 's' : ''}</span>
      </div>
    </div>`;
  initScrollRevealForNew(container);
}

/* ---- Skeleton loading placeholders ---- */

function showSkeletons(container, count) {
  let html = '';
  for (let i = 0; i < count; i++) {
    html += `
      <div class="review-card review-card-skeleton">
        <div class="shimmer" style="height: 20px; width: 120px; border-radius: 4px; margin-bottom: 12px;"></div>
        <div class="shimmer" style="height: 14px; width: 100%; border-radius: 4px; margin-bottom: 8px;"></div>
        <div class="shimmer" style="height: 14px; width: 80%; border-radius: 4px; margin-bottom: 16px;"></div>
        <div style="display: flex; align-items: center; gap: 10px;">
          <div class="shimmer" style="width: 36px; height: 36px; border-radius: 50%;"></div>
          <div class="shimmer" style="height: 14px; width: 100px; border-radius: 4px;"></div>
        </div>
      </div>`;
  }
  container.innerHTML = html;
}

/* ---- Page loaders ---- */

async function loadFeaturedReviews() {
  const grid = document.getElementById('featured-reviews-grid');
  if (!grid) return;

  const section = grid.closest('.section');

  try {
    showSkeletons(grid, 3);
    const reviews = await fetchReviews({ featuredOnly: true, limit: 6 });

    if (!reviews || reviews.length === 0) {
      if (section) section.style.display = 'none';
      return;
    }

    renderReviewCards(reviews, grid);
  } catch (err) {
    console.error('Failed to load featured reviews:', err);
    if (section) section.style.display = 'none';
  }
}

async function loadAllReviews() {
  const grid = document.getElementById('all-reviews-grid');
  if (!grid) return;

  try {
    showSkeletons(grid, 6);
    const reviews = await fetchReviews({ limit: 100 });
    renderReviewCards(reviews, grid);
    renderReviewStats(reviews);
  } catch (err) {
    console.error('Failed to load reviews:', err);
    grid.innerHTML = `
      <div class="reviews-empty-state">
        <h3>Unable to Load Reviews</h3>
        <p>Please try again later.</p>
      </div>`;
  }
}

/* ---- Interactive star selector ---- */

function initStarRatingSelector() {
  const container = document.querySelector('.star-selector');
  if (!container) return;

  const buttons = container.querySelectorAll('.star-select-btn');
  const hiddenInput = document.getElementById('review-rating');
  let selectedRating = 0;

  buttons.forEach(btn => {
    const value = parseInt(btn.dataset.value, 10);

    btn.addEventListener('mouseenter', () => {
      buttons.forEach(b => {
        const v = parseInt(b.dataset.value, 10);
        b.classList.toggle('hovered', v <= value);
      });
    });

    btn.addEventListener('mouseleave', () => {
      buttons.forEach(b => b.classList.remove('hovered'));
    });

    btn.addEventListener('click', () => {
      selectedRating = value;
      if (hiddenInput) hiddenInput.value = value;
      buttons.forEach(b => {
        const v = parseInt(b.dataset.value, 10);
        b.classList.toggle('selected', v <= value);
      });
    });
  });
}

/* ---- Form handling ---- */

function initReviewForm() {
  const form = document.getElementById('review-form');
  if (!form) return;

  initStarRatingSelector();

  form.addEventListener('submit', async (e) => {
    e.preventDefault();

    const rating = parseInt(document.getElementById('review-rating').value, 10);
    const review_text = document.getElementById('review-text').value.trim();
    const reviewer_name = document.getElementById('review-name').value.trim();
    const submitBtn = form.querySelector('.review-submit-btn');

    // Validation
    if (!rating || rating < 1 || rating > 5) {
      showReviewToast('Please select a star rating.', 'error');
      return;
    }
    if (review_text.length < 10) {
      showReviewToast('Review must be at least 10 characters.', 'error');
      return;
    }
    if (review_text.length > 2000) {
      showReviewToast('Review must be under 2000 characters.', 'error');
      return;
    }

    // Loading state
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<span class="spinner"></span> Submitting...';

    try {
      await submitReview({ rating, review_text, reviewer_name });
      showReviewToast('Thank you! Your review has been submitted and is pending approval.', 'success');
      form.reset();
      // Reset star selector
      document.querySelectorAll('.star-select-btn').forEach(b => b.classList.remove('selected'));
      document.getElementById('review-rating').value = '';
    } catch (err) {
      console.error('Submit error:', err);
      showReviewToast('Failed to submit review. Please try again.', 'error');
    } finally {
      submitBtn.disabled = false;
      submitBtn.innerHTML = 'Submit Review';
    }
  });
}

/* ---- Toast notifications ---- */

function showReviewToast(message, type) {
  let container = document.getElementById('review-toast-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'review-toast-container';
    container.className = 'review-toast-container';
    document.body.appendChild(container);
  }

  const toast = document.createElement('div');
  toast.className = `review-toast review-toast-${type} toast`;
  toast.textContent = message;
  container.appendChild(toast);

  setTimeout(() => {
    toast.classList.add('hide');
    toast.addEventListener('animationend', () => toast.remove());
  }, 4000);
}

/* ---- Scroll reveal for dynamic content ---- */

function initScrollRevealForNew(container) {
  const elements = container.querySelectorAll('.reveal:not(.visible)');
  if (elements.length === 0) return;

  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('visible');
      }
    });
  }, {
    threshold: 0.1,
    rootMargin: '0px 0px -50px 0px'
  });

  elements.forEach(el => observer.observe(el));
}

/* ---- Init on DOMContentLoaded ---- */

document.addEventListener('DOMContentLoaded', () => {
  if (document.getElementById('featured-reviews-grid')) loadFeaturedReviews();
  if (document.getElementById('all-reviews-grid')) loadAllReviews();
  if (document.getElementById('review-form')) initReviewForm();
});
