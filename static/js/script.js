/* ═══════════════════════════════════════
   DiabetesAI – Main JavaScript
   ═══════════════════════════════════════ */

document.addEventListener('DOMContentLoaded', () => {

  // ── Password show/hide ──────────────────────────────────────
  window.togglePw = function(fieldId) {
    const input = document.getElementById(fieldId);
    const eye   = document.getElementById(fieldId + '-eye');
    if (!input || !eye) return;
    if (input.type === 'password') {
      input.type = 'text';
      eye.classList.replace('bi-eye', 'bi-eye-slash');
    } else {
      input.type = 'password';
      eye.classList.replace('bi-eye-slash', 'bi-eye');
    }
  };

  // ── Password strength indicator ─────────────────────────────
  const pwInput    = document.getElementById('password');
  const strengthEl = document.getElementById('passwordStrength');
  const fillEl     = document.getElementById('strengthFill');
  const labelEl    = document.getElementById('strengthLabel');

  if (pwInput && strengthEl) {
    pwInput.addEventListener('input', () => {
      const val = pwInput.value;
      strengthEl.classList.toggle('show', val.length > 0);
      const score = calcStrength(val);
      const configs = [
        { pct: '25%', color: '#ef4444', text: 'Weak' },
        { pct: '50%', color: '#f97316', text: 'Fair' },
        { pct: '75%', color: '#f59e0b', text: 'Good' },
        { pct: '100%', color: '#10b981', text: 'Strong' },
      ];
      const cfg = configs[Math.max(0, Math.min(score - 1, 3))];
      fillEl.style.width = cfg.pct;
      fillEl.style.background = cfg.color;
      labelEl.textContent = 'Strength: ' + cfg.text;
      labelEl.style.color = cfg.color;
    });
  }

  function calcStrength(pw) {
    let s = 0;
    if (pw.length >= 6)  s++;
    if (pw.length >= 10) s++;
    if (/[A-Z]/.test(pw) && /[a-z]/.test(pw)) s++;
    if (/[0-9]/.test(pw)) s++;
    if (/[^A-Za-z0-9]/.test(pw)) s++;
    return Math.min(Math.ceil(s * 0.8) + 1, 4);
  }

  // ── Register form validation ────────────────────────────────
  const registerForm = document.getElementById('registerForm');
  if (registerForm) {
    registerForm.addEventListener('submit', function(e) {
      let valid = true;
      clearErrors(this);

      const name    = this.name.value.trim();
      const email   = this.email.value.trim();
      const pw      = this.password.value;
      const confirm = this.confirm_password.value;

      if (!name || name.length < 2) {
        showError('name', 'Please enter your full name (at least 2 characters).');
        valid = false;
      }
      if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
        showError('email', 'Please enter a valid email address.');
        valid = false;
      }
      if (!pw || pw.length < 6) {
        showError('password', 'Password must be at least 6 characters.');
        valid = false;
      }
      if (pw !== confirm) {
        showError('confirm_password', 'Passwords do not match.');
        valid = false;
      }

      if (!valid) { e.preventDefault(); return; }
      setLoading('registerBtn');
    });
  }

  // ── Login form validation ───────────────────────────────────
  const loginForm = document.getElementById('loginForm');
  if (loginForm) {
    loginForm.addEventListener('submit', function(e) {
      let valid = true;
      clearErrors(this);

      const email = this.email.value.trim();
      const pw    = this.password.value;

      if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
        showError('email', 'Please enter a valid email address.');
        valid = false;
      }
      if (!pw) {
        showError('password', 'Password is required.');
        valid = false;
      }
      if (!valid) { e.preventDefault(); return; }
      setLoading('loginBtn');
    });
  }

  // ── Predict form validation ─────────────────────────────────
  const predictForm = document.getElementById('predictForm');
  if (predictForm) {
    predictForm.addEventListener('submit', function(e) {
      let valid = true;
      clearErrors(this);

      const fields = [
        { id: 'pregnancies',    min: 0,   max: 20,  label: 'Pregnancies' },
        { id: 'glucose',        min: 50,  max: 250, label: 'Glucose' },
        { id: 'blood_pressure', min: 40,  max: 150, label: 'Blood Pressure' },
        { id: 'skin_thickness', min: 0,   max: 100, label: 'Skin Thickness' },
        { id: 'insulin',        min: 0,   max: 900, label: 'Insulin' },
        { id: 'bmi',            min: 10,  max: 70,  label: 'BMI' },
        { id: 'dpf',            min: 0.0, max: 3.0, label: 'Diabetes Pedigree Function' },
        { id: 'age',            min: 10,  max: 120, label: 'Age' },
      ];

      fields.forEach(f => {
        const el  = document.getElementById(f.id);
        const val = parseFloat(el.value);
        if (el.value.trim() === '' || isNaN(val)) {
          showErrorEl(el, `${f.label} is required.`);
          valid = false;
        } else if (val < f.min || val > f.max) {
          showErrorEl(el, `${f.label} must be between ${f.min} and ${f.max}.`);
          valid = false;
        }
      });

      if (!valid) { e.preventDefault(); return; }
      setLoading('predictBtn', 'Analyzing...');

      // Scroll to result after submit (form reloads)
    });
  }

  // Scroll to result card on predict page if present
  const resultCard = document.getElementById('resultCard');
  if (resultCard) {
    setTimeout(() => resultCard.scrollIntoView({ behavior: 'smooth', block: 'start' }), 300);
  }

  // ── Contact form ────────────────────────────────────────────
  const contactForm = document.getElementById('contactForm');
  if (contactForm) {
    contactForm.addEventListener('submit', function(e) {
      let valid = true;
      clearErrors(this);
      ['c_name','c_email','c_subject','c_message'].forEach(id => {
        const el = document.getElementById(id);
        if (!el || el.value.trim() === '') {
          el && el.classList.add('is-invalid');
          valid = false;
        }
      });
      if (!valid) { e.preventDefault(); }
    });
  }

  // ── Helpers ──────────────────────────────────────────────────
  function showError(fieldId, msg) {
    const field = document.getElementById(fieldId);
    if (field) showErrorEl(field, msg);
  }

  function showErrorEl(el, msg) {
    el.classList.add('is-invalid');
    el.style.borderColor = '#ef4444';
    let fb = el.parentElement.nextElementSibling;
    if (!fb || !fb.classList.contains('invalid-feedback-custom')) {
      fb = el.parentElement.parentElement.querySelector('.invalid-feedback-custom');
    }
    if (fb) { fb.textContent = msg; fb.classList.add('show'); }
  }

  function clearErrors(form) {
    form.querySelectorAll('.form-control-custom, .textarea-custom').forEach(el => {
      el.classList.remove('is-invalid');
      el.style.borderColor = '';
    });
    form.querySelectorAll('.invalid-feedback-custom').forEach(el => {
      el.classList.remove('show');
    });
  }

  function setLoading(btnId, text) {
    const btn      = document.getElementById(btnId);
    if (!btn) return;
    const textEl   = btn.querySelector('.btn-text');
    const loaderEl = btn.querySelector('.btn-loader');
    if (textEl)   textEl.classList.add('d-none');
    if (loaderEl) loaderEl.classList.remove('d-none');
    btn.disabled = true;
  }

  // ── Navbar scroll effect ─────────────────────────────────────
  const nav = document.getElementById('mainNav');
  if (nav) {
    window.addEventListener('scroll', () => {
      nav.style.boxShadow = window.scrollY > 30
        ? '0 4px 30px rgba(0,0,0,0.4)'
        : '0 2px 20px rgba(0,0,0,0.3)';
    });
  }

  // ── Auto-dismiss flash alerts ────────────────────────────────
  document.querySelectorAll('.alert').forEach(el => {
    setTimeout(() => {
      el.style.transition = 'opacity .5s';
      el.style.opacity = '0';
      setTimeout(() => el.remove(), 500);
    }, 5000);
  });

});
