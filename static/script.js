/* ============================================================
   AI Resume Analyzer — Main Client Script
   Vanilla JS · No frameworks · Complete implementation
   ============================================================ */

document.addEventListener('DOMContentLoaded', () => {
  'use strict';

  // ──────────────────────────────────────────────────────────
  // 1.  UTILITIES
  // ──────────────────────────────────────────────────────────

  const $ = (sel, ctx = document) => ctx.querySelector(sel);
  const $$ = (sel, ctx = document) => [...ctx.querySelectorAll(sel)];

  /** Convert bytes → human-readable KB / MB string */
  const formatFileSize = (bytes) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1048576) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / 1048576).toFixed(2)} MB`;
  };

  /** Simple email regex check */
  const validateEmail = (email) =>
    /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);

  // ──────────────────────────────────────────────────────────
  // 2.  DARK / LIGHT MODE TOGGLE
  // ──────────────────────────────────────────────────────────

  const toggleTheme = () => {
    const root = document.documentElement;
    const btn = $('.theme-toggle');
    const isDark = root.getAttribute('data-theme') === 'dark';
    const next = isDark ? '' : 'dark';

    root.setAttribute('data-theme', next);
    localStorage.setItem('theme', next);

    if (btn) btn.textContent = next === 'dark' ? '☀️' : '🌙';
  };

  // Apply saved preference immediately
  (() => {
    const saved = localStorage.getItem('theme') || '';
    document.documentElement.setAttribute('data-theme', saved);
    const btn = $('.theme-toggle');
    if (btn) {
      btn.textContent = saved === 'dark' ? '☀️' : '🌙';
      btn.addEventListener('click', toggleTheme);
    }
  })();

  // ──────────────────────────────────────────────────────────
  // 3.  MOBILE NAVBAR
  // ──────────────────────────────────────────────────────────

  (() => {
    const hamburger = $('.hamburger');
    const navLinks = $('.navbar-links');
    const navbar = $('.navbar');

    if (hamburger && navLinks) {
      hamburger.addEventListener('click', () => {
        hamburger.classList.toggle('active');
        navLinks.classList.toggle('active');
      });

      $$('a', navLinks).forEach((link) => {
        link.addEventListener('click', () => {
          hamburger.classList.remove('active');
          navLinks.classList.remove('active');
        });
      });
    }

    if (navbar) {
      window.addEventListener('scroll', () => {
        navbar.classList.toggle('scrolled', window.scrollY > 50);
      }, { passive: true });
    }
  })();

  // ──────────────────────────────────────────────────────────
  // 4.  SMOOTH SCROLL
  // ──────────────────────────────────────────────────────────

  $$('a[href^="#"]').forEach((anchor) => {
    anchor.addEventListener('click', (e) => {
      const targetId = anchor.getAttribute('href');
      if (targetId === '#') return;
      const target = $(targetId);
      if (!target) return;

      e.preventDefault();
      const offset = 80; // fixed navbar height
      const top = target.getBoundingClientRect().top + window.scrollY - offset;
      window.scrollTo({ top, behavior: 'smooth' });
    });
  });

  // ──────────────────────────────────────────────────────────
  // 5 & 6.  DRAG-AND-DROP FILE UPLOAD + VALIDATION
  // ──────────────────────────────────────────────────────────

  const validateFile = (file) => {
    const maxSize = 16 * 1024 * 1024; // 16 MB
    const ext = file.name.split('.').pop().toLowerCase();

    if (ext !== 'pdf') {
      showToast('Only PDF files are accepted.', 'error');
      return false;
    }
    if (file.size > maxSize) {
      showToast('File size must be under 16 MB.', 'error');
      return false;
    }
    return true;
  };

  (() => {
    const zone = $('.upload-zone');
    if (!zone) return;

    const fileInput = $('#resume-file');
    const analyzeBtn = $('.analyze-btn') || $('button[type="submit"]', zone.closest('form'));

    const updateZoneUI = (file) => {
      const fileInfo = $('#fileInfo');
      const fileName = $('#fileName');
      const fileSize = $('#fileSize');
      const uploadText = $('.upload-text', zone);
      const uploadHint = $('.upload-hint', zone);
      const uploadIcon = $('.upload-icon', zone);
      
      if (fileName) fileName.textContent = file.name;
      if (fileSize) fileSize.textContent = formatFileSize(file.size);
      
      if (fileInfo) fileInfo.style.display = 'block';
      if (uploadText) uploadText.style.display = 'none';
      if (uploadHint) uploadHint.style.display = 'none';
      if (uploadIcon) uploadIcon.style.display = 'none';

      zone.classList.add('has-file');
      if (analyzeBtn) analyzeBtn.disabled = false;
    };

    const handleFiles = (files) => {
      if (!files || files.length === 0) return;
      const file = files[0];
      if (!validateFile(file)) return;

      // Sync with hidden input via DataTransfer
      if (fileInput) {
        const dt = new DataTransfer();
        dt.items.add(file);
        fileInput.files = dt.files;
      }
      updateZoneUI(file);
    };

    zone.addEventListener('dragover', (e) => {
      e.preventDefault();
      zone.classList.add('drag-over');
    });

    zone.addEventListener('dragleave', () => {
      zone.classList.remove('drag-over');
    });

    zone.addEventListener('drop', (e) => {
      e.preventDefault();
      zone.classList.remove('drag-over');
      handleFiles(e.dataTransfer.files);
    });

    zone.addEventListener('click', () => {
      if (fileInput) fileInput.click();
    });

    if (fileInput) {
      fileInput.addEventListener('change', () => {
        handleFiles(fileInput.files);
      });
    }
  })();

  // ──────────────────────────────────────────────────────────
  // 7.  ATS SCORE ANIMATION
  // ──────────────────────────────────────────────────────────

  const animateScore = (targetScore) => {
    const circle = $('.score-circle');
    if (!circle) return;

    const progress = $('.progress', circle);
    const valueEl = $('.score-value', circle);
    if (!progress || !valueEl) return;

    const fullDash = 565;
    const targetOffset = fullDash - (fullDash * targetScore / 100);

    progress.style.strokeDashoffset = fullDash;

    // Animate stroke
    requestAnimationFrame(() => {
      progress.style.transition = 'stroke-dashoffset 1.8s ease-out';
      progress.style.strokeDashoffset = targetOffset;
    });

    // Counter animation
    const duration = 1800;
    let start = null;

    const step = (timestamp) => {
      if (!start) start = timestamp;
      const elapsed = timestamp - start;
      const ratio = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - ratio, 3); // ease-out cubic
      const current = Math.round(eased * targetScore);
      valueEl.textContent = current;
      if (ratio < 1) requestAnimationFrame(step);
    };

    requestAnimationFrame(step);
  };

  // Trigger when .score-circle scrolls into view
  (() => {
    const scoreCircle = $('.score-circle');
    if (!scoreCircle) return;

    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          const target = parseInt(scoreCircle.dataset.score, 10) || 0;
          animateScore(target);
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.3 });

    observer.observe(scoreCircle);
  })();

  // ──────────────────────────────────────────────────────────
  // 8.  TOAST NOTIFICATION SYSTEM
  // ──────────────────────────────────────────────────────────

  const showToast = (message, type = 'info', duration = 4000) => {
    let container = $('.toast-container');
    if (!container) {
      container = document.createElement('div');
      container.className = 'toast-container';
      document.body.appendChild(container);
    }

    const icons = { success: '✓', error: '✕', warning: '⚠', info: 'ℹ' };
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `
      <span class="toast-icon">${icons[type] || icons.info}</span>
      <span class="toast-message">${message}</span>
      <button class="toast-close" aria-label="Close">&times;</button>`;

    container.appendChild(toast);

    // Force reflow then reveal
    toast.offsetHeight; // eslint-disable-line no-unused-expressions
    toast.classList.add('show');

    const remove = () => {
      toast.classList.add('hiding');
      toast.addEventListener('transitionend', () => toast.remove(), { once: true });
      // Fallback in case transitionend never fires
      setTimeout(() => { if (toast.parentNode) toast.remove(); }, 600);
    };

    const timer = setTimeout(remove, duration);

    $('.toast-close', toast).addEventListener('click', () => {
      clearTimeout(timer);
      remove();
    });
  };

  // ──────────────────────────────────────────────────────────
  // 9.  FAQ ACCORDION
  // ──────────────────────────────────────────────────────────

  $$('.faq-item').forEach((item) => {
    const question = $('.faq-question', item);
    if (!question) return;

    question.addEventListener('click', () => {
      // Close others
      $$('.faq-item.active').forEach((open) => {
        if (open !== item) open.classList.remove('active');
      });
      item.classList.toggle('active');
    });
  });

  // ──────────────────────────────────────────────────────────
  // 10. TESTIMONIALS CAROUSEL
  // ──────────────────────────────────────────────────────────

  (() => {
    const track = $('.testimonials-track');
    if (!track) return;

    let currentSlide = 0;
    const slides = $$('.testimonial-card', track);
    const totalSlides = slides.length;
    if (totalSlides === 0) return;

    let slideWidth = slides[0].offsetWidth +
      parseInt(getComputedStyle(slides[0]).marginRight, 10) || 0;

    const move = () => {
      currentSlide = (currentSlide + 1) % totalSlides;
      // Loop back smoothly
      if (currentSlide === 0) {
        track.style.transition = 'none';
        track.style.transform = 'translateX(0)';
        track.offsetHeight; // reflow
        track.style.transition = 'transform 0.6s ease';
      }
      track.style.transform = `translateX(-${currentSlide * slideWidth}px)`;
    };

    let interval = setInterval(move, 4000);

    track.addEventListener('mouseenter', () => clearInterval(interval));
    track.addEventListener('mouseleave', () => {
      interval = setInterval(move, 4000);
    });

    // Recalculate on resize
    window.addEventListener('resize', () => {
      if (slides[0]) {
        slideWidth = slides[0].offsetWidth +
          (parseInt(getComputedStyle(slides[0]).marginRight, 10) || 0);
        track.style.transform = `translateX(-${currentSlide * slideWidth}px)`;
      }
    });
  })();

  // ──────────────────────────────────────────────────────────
  // 11. SCROLL REVEAL ANIMATIONS
  // ──────────────────────────────────────────────────────────

  (() => {
    const reveals = $$('.reveal');
    if (reveals.length === 0) return;

    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add('active');
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.1 });

    reveals.forEach((el) => observer.observe(el));
  })();

  // ──────────────────────────────────────────────────────────
  // 12. ANIMATED COUNTERS
  // ──────────────────────────────────────────────────────────

  const animateCounter = (element, target, duration = 2000) => {
    let start = null;

    const step = (timestamp) => {
      if (!start) start = timestamp;
      const elapsed = timestamp - start;
      const ratio = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - ratio, 3);
      element.textContent = Math.round(eased * target).toLocaleString();
      if (ratio < 1) requestAnimationFrame(step);
    };

    requestAnimationFrame(step);
  };

  (() => {
    const stats = $$('.stat-value[data-count]');
    if (stats.length === 0) return;

    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          const el = entry.target;
          const target = parseInt(el.dataset.count, 10) || 0;
          animateCounter(el, target);
          observer.unobserve(el);
        }
      });
    }, { threshold: 0.2 });

    stats.forEach((el) => observer.observe(el));
  })();

  // ──────────────────────────────────────────────────────────
  // 13. AI CHATBOT WIDGET
  // ──────────────────────────────────────────────────────────

  (() => {
    const toggle = $('.chatbot-toggle');
    const panel = $('.chatbot-panel');
    const closeBtn = $('.chatbot-close');
    const input = $('.chatbot-input');
    const sendBtn = $('.chatbot-send');
    const messages = $('.chatbot-messages');

    if (!panel) return;

    const addChatMessage = (text, sender) => {
      const bubble = document.createElement('div');
      bubble.className = `chat-message ${sender}`;
      bubble.textContent = text;
      messages.appendChild(bubble);
      messages.scrollTop = messages.scrollHeight;
      return bubble;
    };

    const showTypingIndicator = () => {
      const indicator = document.createElement('div');
      indicator.className = 'chat-message bot typing';
      indicator.innerHTML = '<span></span><span></span><span></span>';
      messages.appendChild(indicator);
      messages.scrollTop = messages.scrollHeight;
      return indicator;
    };

    const sendMessage = async () => {
      if (!input) return;
      const text = input.value.trim();
      if (!text) return;

      addChatMessage(text, 'user');
      input.value = '';

      const typing = showTypingIndicator();

      try {
        const res = await fetch('/api/chatbot', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ message: text }),
        });
        const data = await res.json();
        typing.remove();
        addChatMessage(data.reply || data.message || 'Sorry, something went wrong.', 'bot');
      } catch {
        typing.remove();
        addChatMessage('Unable to reach the server. Please try again.', 'bot');
      }
    };

    if (toggle) {
      toggle.addEventListener('click', () => panel.classList.toggle('active'));
    }
    if (closeBtn) {
      closeBtn.addEventListener('click', () => panel.classList.remove('active'));
    }
    if (input) {
      input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
          e.preventDefault();
          sendMessage();
        }
      });
    }
    if (sendBtn) {
      sendBtn.addEventListener('click', sendMessage);
    }
  })();

  // ──────────────────────────────────────────────────────────
  // 14. CHART.JS — Score History & Skill Gap
  // ──────────────────────────────────────────────────────────

  (() => {
    // Score History (line chart)
    const historyCanvas = $('#scoreHistoryChart');
    if (historyCanvas) {
      fetch('/api/score-history')
        .then((r) => r.json())
        .then((data) => {
          const ctx = historyCanvas.getContext('2d');
          const gradient = ctx.createLinearGradient(0, 0, 0, historyCanvas.height);
          gradient.addColorStop(0, 'rgba(108,99,255,0.3)');
          gradient.addColorStop(1, 'transparent');

          const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
          const gridColor = isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)';
          const textColor = isDark ? '#ccc' : '#666';

          new Chart(ctx, {
            type: 'line',
            data: {
              labels: data.dates || data.labels || [],
              datasets: [{
                label: 'ATS Score',
                data: data.scores || data.data || [],
                borderColor: '#6C63FF',
                backgroundColor: gradient,
                fill: true,
                tension: 0.4,
                pointBackgroundColor: '#6C63FF',
                pointBorderColor: '#fff',
                pointRadius: 5,
                pointHoverRadius: 8,
                borderWidth: 2,
              }],
            },
            options: {
              responsive: true,
              maintainAspectRatio: false,
              animation: { duration: 2000 },
              scales: {
                y: {
                  min: 0,
                  max: 100,
                  grid: { color: gridColor },
                  ticks: { color: textColor },
                },
                x: {
                  grid: { display: false },
                  ticks: { color: textColor },
                },
              },
              plugins: {
                legend: { labels: { color: textColor } },
              },
            },
          });
        })
        .catch(() => {
          // Chart data unavailable — silently degrade
        });
    }

    // Skill Gap (radar chart)
    const radarCanvas = $('#skillGapChart');
    if (radarCanvas) {
      const matchedRaw = radarCanvas.dataset.matched;
      const missingRaw = radarCanvas.dataset.missing;

      if (matchedRaw && missingRaw) {
        const matched = JSON.parse(matchedRaw);
        const missing = JSON.parse(missingRaw);

        // Build labels from the union of both
        const labels = [...new Set([
          ...Object.keys(matched),
          ...Object.keys(missing),
        ])];
        const matchedValues = labels.map((l) => matched[l] ?? 0);
        const missingValues = labels.map((l) => missing[l] ?? 0);

        const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
        const textColor = isDark ? '#ccc' : '#666';
        const gridColor = isDark ? 'rgba(255,255,255,0.15)' : 'rgba(0,0,0,0.1)';

        new Chart(radarCanvas.getContext('2d'), {
          type: 'radar',
          data: {
            labels,
            datasets: [
              {
                label: 'Your Skills',
                data: matchedValues,
                borderColor: 'rgba(75,192,130,1)',
                backgroundColor: 'rgba(75,192,130,0.2)',
                pointBackgroundColor: 'rgba(75,192,130,1)',
                borderWidth: 2,
              },
              {
                label: 'Required Skills',
                data: missingValues,
                borderColor: 'rgba(255,99,132,1)',
                backgroundColor: 'rgba(255,99,132,0.2)',
                pointBackgroundColor: 'rgba(255,99,132,1)',
                borderWidth: 2,
              },
            ],
          },
          options: {
            responsive: true,
            scales: {
              r: {
                min: 0,
                max: 1,
                ticks: { display: false },
                grid: { color: gridColor },
                pointLabels: { color: textColor, font: { size: 12 } },
                angleLines: { color: gridColor },
              },
            },
            plugins: {
              legend: { labels: { color: textColor } },
            },
          },
        });
      }
    }
  })();

  // ──────────────────────────────────────────────────────────
  // 15. FORM VALIDATION
  // ──────────────────────────────────────────────────────────

  const showFieldError = (fieldId, message) => {
    clearFieldError(fieldId);
    const field = $(`#${fieldId}`);
    if (!field) return;
    const error = document.createElement('span');
    error.className = 'field-error';
    error.textContent = message;
    field.classList.add('input-error');
    field.parentElement.appendChild(error);
  };

  const clearFieldError = (fieldId) => {
    const field = $(`#${fieldId}`);
    if (!field) return;
    field.classList.remove('input-error');
    const existing = $('.field-error', field.parentElement);
    if (existing) existing.remove();
  };

  // Login form
  (() => {
    const form = $('#login-form');
    if (!form) return;

    form.addEventListener('submit', (e) => {
      let valid = true;
      const email = $('#login-email');
      const password = $('#login-password');

      if (email) {
        clearFieldError('login-email');
        if (!validateEmail(email.value.trim())) {
          showFieldError('login-email', 'Please enter a valid email address.');
          valid = false;
        }
      }
      if (password) {
        clearFieldError('login-password');
        if (!password.value) {
          showFieldError('login-password', 'Password is required.');
          valid = false;
        }
      }
      if (!valid) e.preventDefault();
    });
  })();

  // Signup form
  (() => {
    const form = $('#signup-form');
    if (!form) return;

    form.addEventListener('submit', (e) => {
      let valid = true;
      const name = $('#signup-name');
      const email = $('#signup-email');
      const password = $('#signup-password');
      const confirm = $('#signup-confirm');

      if (name) {
        clearFieldError('signup-name');
        if (!name.value.trim()) {
          showFieldError('signup-name', 'Name is required.');
          valid = false;
        }
      }
      if (email) {
        clearFieldError('signup-email');
        if (!validateEmail(email.value.trim())) {
          showFieldError('signup-email', 'Please enter a valid email address.');
          valid = false;
        }
      }
      if (password) {
        clearFieldError('signup-password');
        if (password.value.length < 6) {
          showFieldError('signup-password', 'Password must be at least 6 characters.');
          valid = false;
        }
      }
      if (confirm && password) {
        clearFieldError('signup-confirm');
        if (confirm.value !== password.value) {
          showFieldError('signup-confirm', 'Passwords do not match.');
          valid = false;
        }
      }
      if (!valid) e.preventDefault();
    });
  })();

  // Upload / Analyze form
  (() => {
    const form = $('#uploadForm');
    if (!form) return;

    form.addEventListener('submit', (e) => {
      let valid = true;
      const fileInput = $('#resume-file');
      const jobDesc = $('#job-description');

      if (fileInput) {
        clearFieldError('resume-file');
        if (!fileInput.files || fileInput.files.length === 0) {
          showFieldError('resume-file', 'Please upload your resume (PDF).');
          valid = false;
        }
      }
      if (jobDesc) {
        clearFieldError('job-description');
        if (!jobDesc.value.trim()) {
          showFieldError('job-description', 'Please enter the job description.');
          valid = false;
        }
      }
      if (!valid) {
        e.preventDefault();
      } else {
        showLoading();
      }
    });
  })();

  // ──────────────────────────────────────────────────────────
  // 16. LOADING STATES
  // ──────────────────────────────────────────────────────────

  const showLoading = () => {
    const overlay = $('.loading-overlay');
    if (overlay) {
      overlay.classList.remove('hidden');
      overlay.style.display = '';
    }
  };

  const hideLoading = () => {
    const overlay = $('.loading-overlay');
    if (!overlay) return;
    overlay.classList.add('hidden');
    setTimeout(() => {
      if (overlay.classList.contains('hidden')) {
        overlay.style.display = 'none';
      }
    }, 500);
  };

  // Auto-hide on page load
  window.addEventListener('load', () => {
    setTimeout(hideLoading, 500);
  });

  // ──────────────────────────────────────────────────────────
  // 17. COPY TO CLIPBOARD
  // ──────────────────────────────────────────────────────────

  const copyToClipboard = async (text) => {
    try {
      await navigator.clipboard.writeText(text);
      showToast('Copied to clipboard!', 'success', 2500);
    } catch {
      // Fallback for older browsers / insecure contexts
      const ta = document.createElement('textarea');
      ta.value = text;
      ta.style.position = 'fixed';
      ta.style.opacity = '0';
      document.body.appendChild(ta);
      ta.select();
      document.execCommand('copy');
      ta.remove();
      showToast('Copied to clipboard!', 'success', 2500);
    }
  };

  $$('.copy-btn').forEach((btn) => {
    btn.addEventListener('click', () => {
      // Copy sibling or parent text content — adapt selector to your markup
      const target = btn.dataset.target
        ? $(btn.dataset.target)
        : btn.closest('.copy-wrapper')?.querySelector('.copy-content') ||
          btn.previousElementSibling;
      if (target) copyToClipboard(target.textContent);
    });
  });

  // ──────────────────────────────────────────────────────────
  // 18. SIDEBAR TOGGLE (Dashboard)
  // ──────────────────────────────────────────────────────────

  (() => {
    const sidebar = $('.sidebar');
    if (!sidebar) return;

    const sidebarToggle = $('.sidebar-toggle');
    let overlay = $('.sidebar-overlay');

    // Create overlay if it doesn't exist
    if (!overlay) {
      overlay = document.createElement('div');
      overlay.className = 'sidebar-overlay';
      document.body.appendChild(overlay);
    }

    const closeSidebar = () => {
      sidebar.classList.remove('active');
      overlay.classList.remove('active');
    };

    if (sidebarToggle) {
      sidebarToggle.addEventListener('click', () => {
        const isActive = sidebar.classList.toggle('active');
        overlay.classList.toggle('active', isActive);
      });
    }

    overlay.addEventListener('click', closeSidebar);

    window.addEventListener('resize', () => {
      if (window.innerWidth >= 1024) closeSidebar();
    });
  })();

  // ──────────────────────────────────────────────────────────
  // 19. DELETE CONFIRMATION
  // ──────────────────────────────────────────────────────────

  $$('.delete-btn').forEach((btn) => {
    btn.addEventListener('click', (e) => {
      e.preventDefault();

      const message = btn.dataset.confirm || 'Are you sure you want to delete this item?';
      const confirmed = confirm(message);
      if (!confirmed) return;

      // Check for parent form
      const form = btn.closest('form');
      if (form) {
        form.submit();
        return;
      }
      // Check for href / data-url
      const url = btn.getAttribute('href') || btn.dataset.url;
      if (url) {
        window.location.href = url;
      }
    });
  });

  // ──────────────────────────────────────────────────────────
  // 20. KEYBOARD SHORTCUTS
  // ──────────────────────────────────────────────────────────

  document.addEventListener('keydown', (e) => {
    const isMod = e.ctrlKey || e.metaKey;

    // Ctrl/Cmd + K → focus upload / search
    if (isMod && e.key === 'k') {
      e.preventDefault();
      const target = $('.upload-zone') || $('[type="search"]') || $('#job-description');
      if (target) {
        target.focus ? target.focus() : target.click();
        target.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
    }

    // Escape → close chatbot / modal
    if (e.key === 'Escape') {
      const panel = $('.chatbot-panel.active');
      if (panel) panel.classList.remove('active');

      const modal = $('.modal.active, .modal.show');
      if (modal) modal.classList.remove('active', 'show');
    }
  });

  // ──────────────────────────────────────────────────────────
  // 21. PAGE LOAD ANIMATION
  // ──────────────────────────────────────────────────────────

  (() => {
    const main = $('main') || $('.main-content') || $('[role="main"]');
    if (main) main.classList.add('page-transition');

    setTimeout(() => {
      hideLoading();
      if (main) main.classList.add('loaded');
    }, 500);
  })();

  // ──────────────────────────────────────────────────────────
  // 22. TABS (Result Page)
  // ──────────────────────────────────────────────────────────

  (() => {
    const tabNav = $('.tab-nav');
    if (!tabNav) return;

    $$('.tab-btn', tabNav).forEach((btn) => {
      btn.addEventListener('click', () => {
        const targetPanel = btn.dataset.tab;

        // Deactivate all
        $$('.tab-btn', tabNav).forEach((b) => b.classList.remove('active'));
        $$('.tab-panel').forEach((p) => p.classList.remove('active'));

        // Activate clicked
        btn.classList.add('active');
        const panel = $(`#${targetPanel}`) || $(`.tab-panel[data-panel="${targetPanel}"]`);
        if (panel) panel.classList.add('active');
      });
    });
  })();

  // ──────────────────────────────────────────────────────────
  // 23. FLASH MESSAGES → TOASTS
  // ──────────────────────────────────────────────────────────

  $$('.flash-message').forEach((flash) => {
    const type = flash.dataset.type ||
      (flash.classList.contains('success') ? 'success' :
       flash.classList.contains('error') ? 'error' :
       flash.classList.contains('warning') ? 'warning' : 'info');

    showToast(flash.textContent.trim(), type);
    flash.remove();
  });

  // ──────────────────────────────────────────────────────────
  // 24. INTERVIEW PREP — REVEAL ANSWERS
  // ──────────────────────────────────────────────────────────

  $$('.reveal-answer-btn').forEach((btn) => {
    btn.addEventListener('click', () => {
      const answer =
        btn.nextElementSibling?.classList.contains('answer-content')
          ? btn.nextElementSibling
          : btn.parentElement?.querySelector('.answer-content');

      if (!answer) return;

      const isVisible = answer.classList.toggle('visible');
      btn.textContent = isVisible ? 'Hide Answer' : 'Show Answer';
    });
  });

  // ──────────────────────────────────────────────────────────
  // EXPOSE PUBLIC API (for inline handlers if needed)
  // ──────────────────────────────────────────────────────────

  window.ResumeAnalyzer = {
    toggleTheme,
    showToast,
    showLoading,
    hideLoading,
    copyToClipboard,
    animateScore,
    formatFileSize,
    validateEmail,
  };
});
