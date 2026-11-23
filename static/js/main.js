/**
 * Civic Connects - Main Client-side Architecture & Interactions
 * Vanilla JavaScript (Anti-Generic Implementation)
 */

document.addEventListener('DOMContentLoaded', () => {
  initRoleToggle();
  initPasswordToggles();
  initFileDropzone();
  initGeolocation();
  initFormValidation();
  initModalHandlers();
});

/* ==========================================================================
   1. SEGMENTED ROLE TOGGLE COMPONENT
   ========================================================================== */
function initRoleToggle() {
  const toggleContainer = document.querySelector('.role-toggle-container');
  if (!toggleContainer) return;

  const buttons = toggleContainer.querySelectorAll('.role-toggle-btn');
  const roleInput = document.getElementById('roleInput');
  const submitBtn = document.getElementById('submitBtn');
  const registerPrompt = document.getElementById('registerPrompt');
  const adminNotice = document.getElementById('adminNotice');

  buttons.forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      const targetRole = btn.dataset.role;

      // Update active toggle state
      buttons.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');

      // Update hidden form field
      if (roleInput) {
        roleInput.value = targetRole;
      }

      // Update submit button text dynamically
      if (submitBtn) {
        submitBtn.textContent = targetRole === 'admin' 
          ? 'Sign In as Authority / Admin' 
          : 'Sign In as Citizen';
      }

      // Toggle registration prompt (Admin accounts cannot register)
      if (registerPrompt) {
        registerPrompt.style.display = targetRole === 'admin' ? 'none' : 'block';
      }
      if (adminNotice) {
        adminNotice.style.display = targetRole === 'admin' ? 'block' : 'none';
      }
    });
  });
}

/* ==========================================================================
   2. PASSWORD VISIBILITY TOGGLE (EYE ICON)
   ========================================================================== */
function initPasswordToggles() {
  const toggleButtons = document.querySelectorAll('.password-toggle-btn');

  const eyeIconSvg = `
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
      <circle cx="12" cy="12" r="3"></circle>
    </svg>`;

  const eyeOffIconSvg = `
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path>
      <line x1="1" y1="1" x2="23" y2="23"></line>
    </svg>`;

  toggleButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      const targetId = btn.dataset.target;
      const targetInput = document.getElementById(targetId);
      if (!targetInput) return;

      if (targetInput.type === 'password') {
        targetInput.type = 'text';
        btn.innerHTML = eyeOffIconSvg;
        btn.setAttribute('aria-label', 'Hide password');
      } else {
        targetInput.type = 'password';
        btn.innerHTML = eyeIconSvg;
        btn.setAttribute('aria-label', 'Show password');
      }
    });
  });
}

/* ==========================================================================
   3. DRAG-AND-DROP FILE UPLOAD & PREVIEW
   ========================================================================== */
function initFileDropzone() {
  const dropzone = document.getElementById('complaintFileDropzone');
  const fileInput = document.getElementById('complaintImageInput');
  const previewCard = document.getElementById('filePreviewCard');
  const previewThumb = document.getElementById('previewThumb');
  const previewName = document.getElementById('previewName');
  const previewSize = document.getElementById('previewSize');
  const removeBtn = document.getElementById('removeFileBtn');

  if (!dropzone || !fileInput) return;

  // Open file selector on click
  dropzone.addEventListener('click', (e) => {
    if (e.target !== removeBtn && !previewCard.contains(e.target)) {
      fileInput.click();
    }
  });

  // Drag and drop events
  ['dragenter', 'dragover'].forEach(eventName => {
    dropzone.addEventListener(eventName, (e) => {
      e.preventDefault();
      e.stopPropagation();
      dropzone.classList.add('dragover');
    });
  });

  ['dragleave', 'drop'].forEach(eventName => {
    dropzone.addEventListener(eventName, (e) => {
      e.preventDefault();
      e.stopPropagation();
      dropzone.classList.remove('dragover');
    });
  });

  dropzone.addEventListener('drop', (e) => {
    const files = e.dataTransfer.files;
    if (files.length > 0) {
      fileInput.files = files;
      handleFileSelected(files[0]);
    }
  });

  fileInput.addEventListener('change', () => {
    if (fileInput.files.length > 0) {
      handleFileSelected(fileInput.files[0]);
    }
  });

  function handleFileSelected(file) {
    const validTypes = ['image/png', 'image/jpeg', 'image/jpg', 'image/webp'];
    if (!validTypes.includes(file.type)) {
      alert('Invalid file format. Please upload a PNG, JPG, or WEBP image.');
      fileInput.value = '';
      return;
    }

    if (file.size > 5 * 1024 * 1024) {
      alert('File size exceeds the 5MB limit. Please upload a smaller image.');
      fileInput.value = '';
      return;
    }

    // Read and render thumbnail
    const reader = new FileReader();
    reader.onload = (e) => {
      if (previewThumb) previewThumb.src = e.target.result;
      if (previewName) previewName.textContent = file.name;
      if (previewSize) previewSize.textContent = `${(file.size / (1024 * 1024)).toFixed(2)} MB`;
      if (previewCard) previewCard.style.display = 'flex';
      dropzone.querySelector('.dropzone-content').style.display = 'none';
    };
    reader.readAsDataURL(file);
  }

  if (removeBtn) {
    removeBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      fileInput.value = '';
      if (previewCard) previewCard.style.display = 'none';
      dropzone.querySelector('.dropzone-content').style.display = 'block';
      if (previewThumb) previewThumb.src = '';
    });
  }
}

/* ==========================================================================
   4. GEOLOCATION CAPTURE & REVERSE GEOCODING
   ========================================================================== */
function initGeolocation() {
  const geoBtn = document.getElementById('detectLocationBtn');
  const locationInput = document.getElementById('locationInput');
  const latInput = document.getElementById('latInput');
  const lngInput = document.getElementById('lngInput');
  const geoStatus = document.getElementById('geoStatus');

  if (!geoBtn || !locationInput) return;

  function showStatus(message, type) {
    if (!geoStatus) return;
    geoStatus.style.display = 'block';
    if (type === 'loading') {
      geoStatus.style.background = '#EFF6FF';
      geoStatus.style.color = '#1D4ED8';
      geoStatus.style.border = '1px solid #BFDBFE';
      geoStatus.innerHTML = `<span style="display:inline-flex; align-items:center; gap:0.4rem;">
        <svg class="spinner" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
          <circle cx="12" cy="12" r="10" stroke-opacity="0.25"></circle>
          <path d="M12 2a10 10 0 0 1 10 10" stroke-linecap="round"></path>
        </svg>
        ${message}
      </span>`;
    } else if (type === 'success') {
      geoStatus.style.background = '#ECFDF5';
      geoStatus.style.color = '#065F46';
      geoStatus.style.border = '1px solid #A7F3D0';
      geoStatus.innerHTML = `<span style="display:inline-flex; align-items:center; gap:0.4rem;">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#059669" stroke-width="2.5"><polyline points="20 6 9 17 4 12"></polyline></svg>
        ${message}
      </span>`;
    } else if (type === 'warning') {
      geoStatus.style.background = '#FFFBEB';
      geoStatus.style.color = '#B45309';
      geoStatus.style.border = '1px solid #FDE68A';
      geoStatus.innerHTML = `<span style="display:inline-flex; align-items:center; gap:0.4rem;">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#D97706" stroke-width="2.5"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>
        ${message}
      </span>`;
    } else {
      geoStatus.style.background = '#FEF2F2';
      geoStatus.style.color = '#B91C1C';
      geoStatus.style.border = '1px solid #FECACA';
      geoStatus.innerHTML = `<span style="display:inline-flex; align-items:center; gap:0.4rem;">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#DC2626" stroke-width="2.5"><circle cx="12" cy="12" r="10"></circle><line x1="15" y1="9" x2="9" y2="15"></line><line x1="9" y1="9" x2="15" y2="15"></line></svg>
        ${message}
      </span>`;
    }
  }

  // Reverse geocoding via OpenStreetMap Nominatim
  async function reverseGeocode(lat, lng) {
    try {
      const controller = typeof AbortController !== 'undefined' ? new AbortController() : null;
      const timeoutId = controller ? setTimeout(() => controller.abort(), 6000) : null;
      
      const res = await fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lng}&zoom=18&addressdetails=1`, {
        headers: { 'Accept': 'application/json' },
        signal: controller ? controller.signal : undefined
      });
      if (timeoutId) clearTimeout(timeoutId);

      if (res.ok) {
        const data = await res.json();
        if (data && data.address) {
          const a = data.address;
          const parts = [
            a.road || a.pedestrian || a.suburb || a.neighbourhood,
            a.city_district || a.suburb,
            a.city || a.town || a.village || a.county,
            a.state,
            a.postcode
          ].filter(Boolean);
          const unique = [...new Set(parts)];
          if (unique.length > 0) return unique.join(', ');
          if (data.display_name) return data.display_name;
        }
      }
    } catch (e) {
      console.warn('Reverse geocoding notice:', e);
    }
    return null;
  }

  // Fallback to IP-based Geolocation when device GPS is unavailable or blocked
  async function fetchIpLocation() {
    try {
      const controller = typeof AbortController !== 'undefined' ? new AbortController() : null;
      const timeoutId = controller ? setTimeout(() => controller.abort(), 5000) : null;
      const res = await fetch('https://ipapi.co/json/', {
        signal: controller ? controller.signal : undefined
      });
      if (timeoutId) clearTimeout(timeoutId);
      if (res.ok) {
        const data = await res.json();
        if (data && data.latitude && data.longitude) {
          return {
            latitude: parseFloat(data.latitude),
            longitude: parseFloat(data.longitude),
            city: data.city,
            region: data.region,
            country: data.country_name,
            postal: data.postal
          };
        }
      }
    } catch (e) {}

    try {
      const controller2 = typeof AbortController !== 'undefined' ? new AbortController() : null;
      const timeoutId2 = controller2 ? setTimeout(() => controller2.abort(), 4000) : null;
      const res2 = await fetch('https://freeipapi.com/api/json', {
        signal: controller2 ? controller2.signal : undefined
      });
      if (timeoutId2) clearTimeout(timeoutId2);
      if (res2.ok) {
        const data2 = await res2.json();
        if (data2 && data2.latitude && data2.longitude) {
          return {
            latitude: parseFloat(data2.latitude),
            longitude: parseFloat(data2.longitude),
            city: data2.cityName,
            region: data2.regionName,
            country: data2.countryName,
            postal: data2.zipCode
          };
        }
      }
    } catch (e2) {}

    return null;
  }

  function getBrowserPosition(highAccuracy) {
    return new Promise((resolve, reject) => {
      if (!navigator.geolocation) {
        return reject(new Error('NOT_SUPPORTED'));
      }
      navigator.geolocation.getCurrentPosition(resolve, reject, {
        enableHighAccuracy: highAccuracy,
        timeout: highAccuracy ? 8000 : 12000,
        maximumAge: highAccuracy ? 30000 : 300000
      });
    });
  }

  geoBtn.addEventListener('click', async () => {
    geoBtn.disabled = true;
    const originalContent = geoBtn.innerHTML;
    geoBtn.innerHTML = `
      <svg class="spinner" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
        <circle cx="12" cy="12" r="10" stroke-opacity="0.25"></circle>
        <path d="M12 2a10 10 0 0 1 10 10" stroke-linecap="round"></path>
      </svg>
      <span>Detecting...</span>`;

    showStatus('Requesting device GPS coordinates...', 'loading');

    let position = null;
    let isIpFallback = false;
    let ipFallbackData = null;

    // Stage 1: Attempt high accuracy browser GPS
    try {
      position = await getBrowserPosition(true);
    } catch (err1) {
      console.warn('High accuracy geolocation timed out/failed, trying standard accuracy...', err1);
      // Stage 2: Attempt standard accuracy browser positioning (Wi-Fi / cached)
      try {
        showStatus('Refining location via network positioning...', 'loading');
        position = await getBrowserPosition(false);
      } catch (err2) {
        console.warn('Standard browser geolocation failed:', err2);
        // Stage 3: Fallback to IP-based approximate geolocation
        showStatus('Resolving approximate locality via network provider...', 'loading');
        ipFallbackData = await fetchIpLocation();
        if (ipFallbackData) {
          isIpFallback = true;
        } else {
          // All automatic detection methods failed
          geoBtn.disabled = false;
          geoBtn.innerHTML = originalContent;

          let msg = 'Could not acquire location automatically. Please type your street or ward address.';
          if (err1 && err1.code === 1) { // PERMISSION_DENIED
            msg = 'Location permission is blocked in browser settings. Please allow access or type your address manually.';
          } else if (err1 && err1.code === 2) { // POSITION_UNAVAILABLE
            msg = 'GPS signal unavailable on this device. Please type your address or nearest landmark.';
          } else if (err1 && err1.code === 3) { // TIMEOUT
            msg = 'Location request timed out. Please enter your street address or landmark manually.';
          }
          showStatus(msg, 'warning');
          locationInput.focus();
          return;
        }
      }
    }

    // Process acquired coordinates
    let lat = null;
    let lng = null;

    if (position && position.coords) {
      lat = position.coords.latitude;
      lng = position.coords.longitude;
    } else if (ipFallbackData) {
      lat = ipFallbackData.latitude;
      lng = ipFallbackData.longitude;
    }

    if (lat !== null && lng !== null) {
      const latStr = lat.toFixed(6);
      const lngStr = lng.toFixed(6);

      if (latInput) latInput.value = latStr;
      if (lngInput) lngInput.value = lngStr;

      showStatus(`Coordinates locked (${lat.toFixed(4)}, ${lng.toFixed(4)}). Looking up street address...`, 'loading');

      // Stage 4: Reverse geocoding to human-readable address
      const resolvedAddress = await reverseGeocode(lat, lng);

      if (resolvedAddress) {
        locationInput.value = resolvedAddress;
        if (isIpFallback) {
          showStatus(`Approximate address: ${resolvedAddress} [Network IP]. You may refine the house number or landmark.`, 'warning');
        } else {
          showStatus(`Address verified: ${resolvedAddress} (GPS: ${lat.toFixed(4)}, ${lng.toFixed(4)})`, 'success');
        }
      } else if (ipFallbackData && (ipFallbackData.city || ipFallbackData.region)) {
        const ipAddr = [ipFallbackData.city, ipFallbackData.region, ipFallbackData.country].filter(Boolean).join(', ');
        locationInput.value = ipAddr;
        showStatus(`Approximate locality: ${ipAddr} (GPS: ${latStr}, ${lngStr}). You can refine street details above.`, 'warning');
      } else {
        locationInput.value = `GPS Coordinates: ${latStr}, ${lngStr}`;
        showStatus(`GPS Coordinates recorded: ${latStr}, ${lngStr}. You can add nearby landmark or house number.`, 'success');
      }
    }

    geoBtn.disabled = false;
    geoBtn.innerHTML = originalContent;
  });
}

/* ==========================================================================
   5. CLIENT-SIDE FORM VALIDATION
   ========================================================================== */
function initFormValidation() {
  // Indian Mobile Number Mask & Live Validation (Standard 10-digits starting with 6-9)
  const phoneInputs = document.querySelectorAll('#registerPhone, #userPhone, input[type="tel"][name="phone"]');
  phoneInputs.forEach(input => {
    input.addEventListener('input', function() {
      let val = this.value.trim();
      let hasPrefix = val.startsWith('+91');
      let digits = val.replace(/\D/g, '');

      // Strip leading 91 or 0 if more than 10 digits
      if (digits.startsWith('91') && digits.length > 10) {
        digits = digits.slice(2);
      } else if (digits.startsWith('0') && digits.length > 10) {
        digits = digits.slice(1);
      }

      // Enforce max 10 digits
      digits = digits.slice(0, 10);

      // Mask presentation: split 5 + 5 for clean Indian style
      if (hasPrefix) {
        if (digits.length > 5) {
          this.value = '+91 ' + digits.slice(0, 5) + ' ' + digits.slice(5);
        } else if (digits.length > 0) {
          this.value = '+91 ' + digits;
        } else {
          this.value = '+91 ';
        }
      } else {
        if (digits.length > 5) {
          this.value = digits.slice(0, 5) + ' ' + digits.slice(5);
        } else {
          this.value = digits;
        }
      }

      // HTML5 Validation Message
      if (digits.length > 0 && !/^[6-9]/.test(digits)) {
        this.setCustomValidity('Indian mobile number must begin with a digit between 6 and 9.');
      } else if (digits.length > 0 && digits.length < 10) {
        this.setCustomValidity('Mobile number must be exactly 10 digits.');
      } else {
        this.setCustomValidity('');
      }
    });

    input.addEventListener('blur', function() {
      let digits = this.value.replace(/\D/g, '');
      if (digits.startsWith('91') && digits.length === 12) digits = digits.slice(2);
      if (digits.startsWith('0') && digits.length === 11) digits = digits.slice(1);

      if (this.value.trim() && !/^[6-9]\d{9}$/.test(digits)) {
        this.setCustomValidity('Please enter a valid 10-digit Indian mobile number starting with 6, 7, 8, or 9 (e.g. 9876543210).');
        this.reportValidity();
      } else {
        this.setCustomValidity('');
      }
    });
  });

  const registerForm = document.getElementById('registerForm');
  if (registerForm) {
    const password = document.getElementById('registerPassword');
    const confirmPassword = document.getElementById('confirmPassword');
    const matchWarning = document.getElementById('passwordMatchWarning');

    function checkPasswordMatch() {
      if (!confirmPassword.value) {
        if (matchWarning) matchWarning.style.display = 'none';
        return;
      }
      if (password.value !== confirmPassword.value) {
        if (matchWarning) {
          matchWarning.textContent = 'Passwords do not match.';
          matchWarning.style.display = 'block';
          matchWarning.style.color = '#E11D48';
        }
      } else {
        if (matchWarning) {
          matchWarning.textContent = 'Passwords match.';
          matchWarning.style.display = 'block';
          matchWarning.style.color = '#059669';
        }
      }
    }

    if (password && confirmPassword) {
      password.addEventListener('input', checkPasswordMatch);
      confirmPassword.addEventListener('input', checkPasswordMatch);
    }

    registerForm.addEventListener('submit', (e) => {
      if (password.value !== confirmPassword.value) {
        e.preventDefault();
        alert('Please ensure both passwords match before submitting.');
        confirmPassword.focus();
        return;
      }

      const phoneInput = document.getElementById('registerPhone');
      if (phoneInput) {
        let digits = phoneInput.value.replace(/\D/g, '');
        if (digits.startsWith('91') && digits.length === 12) digits = digits.slice(2);
        if (digits.startsWith('0') && digits.length === 11) digits = digits.slice(1);

        if (!/^[6-9]\d{9}$/.test(digits)) {
          e.preventDefault();
          alert('Please enter a valid 10-digit Indian mobile number starting with 6, 7, 8, or 9 (e.g. 9876543210).');
          phoneInput.focus();
          return;
        }
      }
    });
  }
}

/* ==========================================================================
   6. MODAL DIALOG HANDLERS
   ========================================================================== */
function initModalHandlers() {
  // Close modal when clicking on backdrop or close button
  document.querySelectorAll('.modal-backdrop').forEach(backdrop => {
    backdrop.addEventListener('click', (e) => {
      if (e.target === backdrop || e.target.closest('.modal-close-trigger')) {
        closeModal(backdrop.id);
      }
    });
  });

  // Close open modal on Escape key
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      document.querySelectorAll('.modal-backdrop.open').forEach(modal => {
        closeModal(modal.id);
      });
    }
  });
}

window.openModal = function(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.classList.add('open');
    document.body.style.overflow = 'hidden';
  }
};

window.closeModal = function(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.classList.remove('open');
    document.body.style.overflow = '';
  }
};

// Open Action/Resolution Modal for Admin
window.openComplaintModal = function(complaintId) {
  const modal = document.getElementById('complaintActionModal');
  if (!modal) return;

  // Fetch complaint details via JSON API
  fetch(`/admin/complaints/${complaintId}`)
    .then(res => {
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return res.json();
    })
    .then(data => {
      const c = data.complaint;
      document.getElementById('modalTicketNumber').textContent = c.ticket_number;
      document.getElementById('modalCategory').textContent = c.category;
      document.getElementById('modalCitizenName').textContent = c.citizen_name;
      document.getElementById('modalCitizenPhone').textContent = c.citizen_phone;
      document.getElementById('modalCitizenEmail').textContent = c.citizen_email;
      document.getElementById('modalLocation').textContent = c.location;

      const titleEl = document.getElementById('modalTitle');
      if (titleEl) {
        if (c.title && c.title.trim() && c.title.trim() !== (c.description || '').trim()) {
          titleEl.textContent = c.title;
          titleEl.style.display = 'block';
        } else {
          titleEl.textContent = '';
          titleEl.style.display = 'none';
        }
      }
      document.getElementById('modalDescription').textContent = c.description;

      const imgContainer = document.getElementById('modalImageContainer');
      imgContainer.innerHTML = '';
      if (c.image_url) {
        const imageUrl = (c.image_url.startsWith('http://') || c.image_url.startsWith('https://'))
          ? c.image_url
          : `/static/uploads/complaints/${encodeURIComponent(c.image_url)}`;

        const link = document.createElement('a');
        link.href = imageUrl;
        link.target = '_blank';
        link.rel = 'noopener noreferrer';
        link.title = 'Click to view full-size evidence image';
        link.style.display = 'inline-block';

        const img = document.createElement('img');
        img.src = imageUrl;
        img.alt = 'Complaint Evidence';
        img.style.cssText = 'max-width:100%; max-height:180px; border-radius:8px; border:1px solid var(--border-subtle); object-fit:cover; display:block;';

        link.appendChild(img);
        imgContainer.appendChild(link);
        imgContainer.style.display = 'block';
      } else {
        imgContainer.style.display = 'none';
      }

      // Populate form controls
      const form = document.getElementById('modalUpdateForm');
      form.action = `/admin/complaints/${c.id}/update`;
      document.getElementById('modalStatusSelect').value = c.status;
      document.getElementById('modalDeptSelect').value = c.department_id ? String(c.department_id) : '';
      document.getElementById('modalAdminRemarks').value = c.admin_remarks || '';

      // Populate collapsible update history if present
      const historySection = document.getElementById('modalHistorySection');
      const historyList = document.getElementById('modalHistoryList');
      const historyCount = document.getElementById('modalHistoryCount');
      if (historySection && historyList && historyCount) {
        historyList.innerHTML = '';
        historySection.open = false;
        const logs = Array.isArray(data.logs) ? data.logs : [];
        if (logs.length > 0) {
          historyCount.textContent = String(logs.length);
          logs.slice().reverse().forEach(log => {
            const row = document.createElement('div');
            row.style.cssText = 'background: var(--bg-surface); border: 1px solid var(--border-subtle); border-radius: 6px; padding: 0.5rem 0.75rem; font-size: 0.8rem;';

            const meta = document.createElement('div');
            meta.style.cssText = 'display: flex; justify-content: space-between; gap: 0.5rem; margin-bottom: 0.2rem; color: var(--text-muted); font-size: 0.72rem;';
            const statusSpan = document.createElement('strong');
            statusSpan.style.color = 'var(--text-main)';
            statusSpan.textContent = (log.new_status || '').replace(/_/g, ' ').toUpperCase();
            const timeSpan = document.createElement('span');
            timeSpan.textContent = log.created_at || '';
            meta.appendChild(statusSpan);
            meta.appendChild(timeSpan);

            const note = document.createElement('div');
            note.style.color = 'var(--text-main)';
            note.textContent = log.notes || '';

            row.appendChild(meta);
            row.appendChild(note);
            historyList.appendChild(row);
          });
          historySection.style.display = 'block';
        } else {
          historySection.style.display = 'none';
        }
      }

      openModal('complaintActionModal');
      const modalBody = modal.querySelector('.modal-body');
      if (modalBody) {
        modalBody.scrollTop = 0;
      }
    })
    .catch(err => {
      console.error('Error fetching complaint details:', err);
      alert('Unable to load ticket details.');
    });
};
