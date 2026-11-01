/**
 * Medicare Interactive JavaScript
 * - Persistent Database-Backed Shopping Cart with CSRF & Drawer UI
 * - Server-side search & Instant UI updates
 * - Symptom Pill filtering for Doctor Cards
 * - Location selector modal/dropdown
 */

function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';');
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === (name + '=')) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}

// Global Cart State
let currentCartData = { items: [], total_items: 0, subtotal: 0, subtotal_formatted: '₹0.00' };

async function fetchCart() {
  try {
    const res = await fetch('/cart/json/');
    if (res.ok) {
      const data = await res.json();
      currentCartData = data;
      renderCartUI();
    }
  } catch (err) {
    console.error('Error fetching cart:', err);
  }
}

function renderCartUI() {
  const badges = document.querySelectorAll('.mc-cart-badge');
  badges.forEach(b => {
    b.textContent = currentCartData.total_items || 0;
  });

  const cartBody = document.getElementById('mcCartItems');
  const subtotalEl = document.getElementById('mcCartSubtotal');

  if (!cartBody) return;

  if (!currentCartData.items || currentCartData.items.length === 0) {
    cartBody.innerHTML = `
      <div class="text-center py-5">
        <div style="font-size: 2.5rem; margin-bottom: 0.75rem;">🛒</div>
        <div class="fw-bold text-dark">Your cart is empty</div>
        <div class="text-muted small mt-1">Add medicines, lab tests, or healthcare products to proceed.</div>
        <a href="/pharmacy/" class="btn btn-sm btn-outline-primary rounded-pill mt-3 px-3">Browse Pharmacy</a>
      </div>
    `;
    if (subtotalEl) subtotalEl.textContent = '₹0.00';
    return;
  }

  cartBody.innerHTML = currentCartData.items.map(item => `
    <div class="mc-cart-item d-flex align-items-center justify-content-between p-2 mb-2 border-bottom">
      <img src="${item.image_url}" alt="${item.name}" class="mc-cart-item-img rounded" style="width: 48px; height: 48px; object-fit: cover;">
      <div class="mc-cart-item-info flex-grow-1 px-3">
        <div class="mc-cart-item-title fw-semibold text-dark small">${item.name}</div>
        <div class="mc-cart-item-price text-muted small">
          ₹${item.price.toFixed(2)} &times; 
          <span class="d-inline-flex align-items-center gap-1">
            <button type="button" class="btn btn-xs btn-outline-secondary p-0 px-1" style="font-size: 0.7rem;" onclick="updateCartItemQty(${item.id}, ${item.quantity - 1})">-</button>
            <span class="fw-bold px-1">${item.quantity}</span>
            <button type="button" class="btn btn-xs btn-outline-secondary p-0 px-1" style="font-size: 0.7rem;" onclick="updateCartItemQty(${item.id}, ${item.quantity + 1})" ${item.quantity >= item.stock ? 'disabled' : ''}>+</button>
          </span>
        </div>
      </div>
      <button type="button" class="mc-cart-item-remove btn btn-sm text-danger p-0 border-0" onclick="removeCartItemBackend(${item.id})" title="Remove item">&times;</button>
    </div>
  `).join('');

  if (subtotalEl) {
    subtotalEl.textContent = currentCartData.subtotal_formatted || `₹${currentCartData.subtotal.toFixed(2)}`;
  }
}

async function addToCart(productId, title, price) {
  const csrftoken = getCookie('csrftoken');
  try {
    const res = await fetch('/cart/add/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrftoken,
        'X-Requested-With': 'XMLHttpRequest'
      },
      body: JSON.stringify({ product_id: productId, quantity: 1 })
    });
    const data = await res.json();
    if (res.ok && data.success) {
      currentCartData = data.cart;
      renderCartUI();
      showToast(data.message || `Added to health cart!`);
      openCartDrawer();
    } else {
      showToast(`⚠️ ${data.error || 'Could not add to cart.'}`);
    }
  } catch (err) {
    console.error('Add to cart error:', err);
    showToast('Could not reach server. Please try again.');
  }
}

async function updateCartItemQty(itemId, newQty) {
  const csrftoken = getCookie('csrftoken');
  try {
    const res = await fetch('/cart/update/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrftoken,
        'X-Requested-With': 'XMLHttpRequest'
      },
      body: JSON.stringify({ item_id: itemId, quantity: newQty })
    });
    const data = await res.json();
    if (res.ok && data.success) {
      currentCartData = data.cart;
      renderCartUI();
    } else {
      showToast(`⚠️ ${data.error || 'Could not update item.'}`);
    }
  } catch (err) {
    console.error('Update cart error:', err);
  }
}

async function removeCartItemBackend(itemId) {
  const csrftoken = getCookie('csrftoken');
  try {
    const res = await fetch(`/cart/remove/${itemId}/`, {
      method: 'POST',
      headers: {
        'X-CSRFToken': csrftoken,
        'X-Requested-With': 'XMLHttpRequest'
      }
    });
    const data = await res.json();
    if (res.ok && data.success) {
      currentCartData = data.cart;
      renderCartUI();
      showToast(data.message || 'Item removed from cart.');
    }
  } catch (err) {
    console.error('Remove cart error:', err);
  }
}

function openCartDrawer() {
  const drawer = document.getElementById('mcCartDrawer');
  const backdrop = document.getElementById('mcCartBackdrop');
  if (drawer && backdrop) {
    drawer.classList.add('open');
    backdrop.classList.add('open');
  }
}

function closeCartDrawer() {
  const drawer = document.getElementById('mcCartDrawer');
  const backdrop = document.getElementById('mcCartBackdrop');
  if (drawer && backdrop) {
    drawer.classList.remove('open');
    backdrop.classList.remove('open');
  }
}

function proceedToCheckout() {
  if (!currentCartData.items || currentCartData.items.length === 0) {
    showToast('Your cart is empty. Please add medicines or products first.');
    return;
  }
  window.location.href = '/checkout/';
}

function showToast(message) {
  let toast = document.getElementById('mcToast');
  if (!toast) {
    toast = document.createElement('div');
    toast.id = 'mcToast';
    toast.className = 'mc-toast';
    document.body.appendChild(toast);
  }
  toast.innerHTML = `<span>✓</span> <span>${message}</span>`;
  toast.classList.add('show');
  setTimeout(() => {
    toast.classList.remove('show');
  }, 2800);
}

// Location Selector
function setLocation(city) {
  const valEl = document.getElementById('mcCurrentLocation');
  if (valEl) {
    valEl.textContent = city;
    localStorage.setItem('medicare_city', city);
    showToast(`Location set to ${city}`);
  }
}

// Symptom Filtering for Doctors
function filterDoctorsBySymptom(pillElement, symptom) {
  document.querySelectorAll('.mc-filter-pill').forEach(p => p.classList.remove('active'));
  pillElement.classList.add('active');

  const cards = document.querySelectorAll('.mc-doctor-card');
  const query = symptom.toLowerCase().trim();

  cards.forEach(card => {
    const spec = (card.getAttribute('data-spec') || '').toLowerCase();
    const name = (card.getAttribute('data-name') || '').toLowerCase();
    const dept = (card.getAttribute('data-dept') || '').toLowerCase();
    const cardSymptoms = (card.getAttribute('data-symptoms') || '').toLowerCase();

    if (query === 'all' || cardSymptoms.includes(query) || spec.includes(query) || dept.includes(query)) {
      card.style.display = 'flex';
      card.style.animation = 'fadeIn 0.3s ease';
    } else {
      card.style.display = 'none';
    }
  });
}

// Newsletter subscription
function handleNewsletterSubmit(e) {
  e.preventDefault();
  const input = document.getElementById('mcNewsletterEmail');
  if (input && input.value) {
    showToast('🎉 Thank you for subscribing to Medicare Health Digest!');
    input.value = '';
  }
}

// Initialize on DOM load
document.addEventListener('DOMContentLoaded', () => {
  fetchCart();

  const savedCity = localStorage.getItem('medicare_city');
  if (savedCity) {
    const valEl = document.getElementById('mcCurrentLocation');
    if (valEl) valEl.textContent = savedCity;
  }

  // Bind Enter key on search bar to trigger server search
  const searchInput = document.getElementById('mcSearchInput');
  if (searchInput) {
    searchInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        const val = searchInput.value.trim();
        if (val) {
          window.location.href = `/search/?q=${encodeURIComponent(val)}`;
        }
      }
    });
  }
});
