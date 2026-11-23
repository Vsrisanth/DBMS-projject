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
  const adminPasskeyGroup = document.getElementById('adminPasskeyGroup');
  const citizenAddressGroup = document.getElementById('citizenAddressGroup');

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
        const isRegisterPage = document.getElementById('registerForm') !== null;
        if (isRegisterPage) {
          submitBtn.textContent = targetRole === 'admin' 
            ? 'Register as Municipal Authority' 
            : 'Register as Citizen';
        } else {
          submitBtn.textContent = targetRole === 'admin' 
            ? 'Sign In as Authority / Admin' 
            : 'Sign In as Citizen';
        }
      }

      // Role specific fields on registration
      if (adminPasskeyGroup) {
        if (targetRole === 'admin') {
          adminPasskeyGroup.style.display = 'block';
          const passkeyInput = adminPasskeyGroup.querySelector('input');
          if (passkeyInput) passkeyInput.required = true;
        } else {
          adminPasskeyGroup.style.display = 'none';
          const passkeyInput = adminPasskeyGroup.querySelector('input');
          if (passkeyInput) passkeyInput.required = false;
        }
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
   4. GEOLOCATION CAPTURE
   ========================================================================== */
function initGeolocation() {
  const geoBtn = document.getElementById('detectLocationBtn');
  const locationInput = document.getElementById('locationInput');
  const latInput = document.getElementById('latInput');
  const lngInput = document.getElementById('lngInput');
  const geoStatus = document.getElementById('geoStatus');

  if (!geoBtn) return;

  geoBtn.addEventListener('click', () => {
    if (!navigator.geolocation) {
      alert('Geolocation is not supported by your browser.');
      return;
    }

    geoBtn.disabled = true;
    const originalText = geoBtn.innerHTML;
    geoBtn.innerHTML = `
      <svg class="spinner" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="12" cy="12" r="10" stroke-opacity="0.25"></circle>
        <path d="M12 2a10 10 0 0 1 10 10" stroke-linecap="round"></path>
      </svg> Locating...`;

    navigator.geolocation.getCurrentPosition(
      (position) => {
        const lat = position.coords.latitude.toFixed(6);
        const lng = position.coords.longitude.toFixed(6);

        if (latInput) latInput.value = lat;
        if (lngInput) lngInput.value = lng;

        if (locationInput && !locationInput.value.trim()) {
          locationInput.value = `GPS: [${lat}, ${lng}] - Ward/Locality detected via coordinates`;
        }

        if (geoStatus) {
          geoStatus.textContent = `Coordinates detected: ${lat}, ${lng}`;
          geoStatus.style.display = 'block';
        }

        geoBtn.innerHTML = originalText;
        geoBtn.disabled = false;
      },
      (error) => {
        console.warn('Geolocation error:', error);
        alert('Could not detect location automatically. Please enter your address or landmark manually.');
        geoBtn.innerHTML = originalText;
        geoBtn.disabled = false;
      },
      { timeout: 10000, enableHighAccuracy: true }
    );
  });
}

/* ==========================================================================
   5. CLIENT-SIDE FORM VALIDATION
   ========================================================================== */
function initFormValidation() {
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
    .then(res => res.json())
    .then(data => {
      const c = data.complaint;
      document.getElementById('modalTicketNumber').textContent = c.ticket_number;
      document.getElementById('modalCategory').textContent = c.category;
      document.getElementById('modalCitizenName').textContent = c.citizen_name;
      document.getElementById('modalCitizenPhone').textContent = c.citizen_phone;
      document.getElementById('modalCitizenEmail').textContent = c.citizen_email;
      document.getElementById('modalLocation').textContent = c.location;
      document.getElementById('modalDescription').textContent = c.description;
      
      const imgContainer = document.getElementById('modalImageContainer');
      if (c.image_url) {
        imgContainer.innerHTML = `<img src="/static/uploads/complaints/${c.image_url}" alt="Evidence" style="max-width:100%; max-height:260px; border-radius:8px; border:1px solid #E2E8F0; object-fit:cover;">`;
        imgContainer.style.display = 'block';
      } else {
        imgContainer.style.display = 'none';
      }

      // Populate form controls
      const form = document.getElementById('modalUpdateForm');
      form.action = `/admin/complaints/${c.id}/update`;
      document.getElementById('modalStatusSelect').value = c.status;
      if (c.department_id) {
        document.getElementById('modalDeptSelect').value = c.department_id;
      } else {
        document.getElementById('modalDeptSelect').value = '';
      }
      document.getElementById('modalAdminRemarks').value = c.admin_remarks || '';

      openModal('complaintActionModal');
    })
    .catch(err => {
      console.error('Error fetching complaint details:', err);
      alert('Unable to load ticket details.');
    });
};
