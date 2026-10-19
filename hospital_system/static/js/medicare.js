/**
 * Medicare Interactive JavaScript
 * Supports:
 * - Dynamic Shopping Cart with Drawer and badge counters
 * - Symptom Pill filtering for Doctor Cards
 * - Location selector modal/dropdown
 * - Live Search Filtering
 */

// Cart State
let medicareCart = JSON.parse(localStorage.getItem('medicare_cart') || '[]');

function saveCart() {
  localStorage.setItem('medicare_cart', JSON.stringify(medicareCart));
  updateCartUI();
}

function updateCartUI() {
  const badges = document.querySelectorAll('.mc-cart-badge');
  const totalCount = medicareCart.reduce((acc, item) => acc + item.qty, 0);
  badges.forEach(b => {
    b.textContent = totalCount;
  });

  const cartBody = document.getElementById('mcCartItems');
  const subtotalEl = document.getElementById('mcCartSubtotal');
  
  if (!cartBody) return;

  if (medicareCart.length === 0) {
    cartBody.innerHTML = `
      <div class="text-center py-5">
        <div style="font-size: 2.5rem; margin-bottom: 0.75rem;">🛒</div>
        <div class="fw-bold text-dark">Your cart is empty</div>
        <div class="text-muted small mt-1">Add medicines, lab tests, or healthcare products to proceed.</div>
      </div>
    `;
    if (subtotalEl) subtotalEl.textContent = '₹0.00';
    return;
  }

  let total = 0;
  cartBody.innerHTML = medicareCart.map((item, idx) => {
    total += item.price * item.qty;
    return `
      <div class="mc-cart-item">
        <img src="${item.image}" alt="${item.title}" class="mc-cart-item-img">
        <div class="mc-cart-item-info">
          <div class="mc-cart-item-title">${item.title}</div>
          <div class="mc-cart-item-price">₹${item.price.toFixed(2)} &times; ${item.qty}</div>
        </div>
        <button type="button" class="mc-cart-item-remove" onclick="removeCartItem(${idx})">&times;</button>
      </div>
    `;
  }).join('');

  if (subtotalEl) {
    subtotalEl.textContent = `₹${total.toFixed(2)}`;
  }
}

function addToCart(title, price, image) {
  const existing = medicareCart.find(item => item.title === title);
  if (existing) {
    existing.qty += 1;
  } else {
    medicareCart.push({ title, price: parseFloat(price), image, qty: 1 });
  }
  saveCart();
  showToast(`Added "${title}" to cart!`);
  openCartDrawer();
}

function removeCartItem(index) {
  medicareCart.splice(index, 1);
  saveCart();
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

// Search functionality
function handleSearchInput(e) {
  const query = e.target.value.toLowerCase().trim();
  const doctorCards = document.querySelectorAll('.mc-doctor-card');
  const productCards = document.querySelectorAll('.mc-product-card');

  if (!query) {
    doctorCards.forEach(c => c.style.display = 'flex');
    productCards.forEach(c => c.style.display = 'flex');
    return;
  }

  doctorCards.forEach(card => {
    const text = card.textContent.toLowerCase();
    card.style.display = text.includes(query) ? 'flex' : 'none';
  });

  productCards.forEach(card => {
    const text = card.textContent.toLowerCase();
    card.style.display = text.includes(query) ? 'flex' : 'none';
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
  updateCartUI();

  const savedCity = localStorage.getItem('medicare_city');
  if (savedCity) {
    const valEl = document.getElementById('mcCurrentLocation');
    if (valEl) valEl.textContent = savedCity;
  }

  const searchInput = document.getElementById('mcSearchInput');
  if (searchInput) {
    searchInput.addEventListener('input', handleSearchInput);
  }
});
