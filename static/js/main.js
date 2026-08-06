(() => {
  const nav = document.getElementById('site-nav');
  const menuBtn = document.getElementById('menu-btn');
  const mobileMenu = document.getElementById('mobile-menu');
  const form = document.getElementById('rsvp-form');
  const statusEl = document.getElementById('rsvp-status');
  const submitBtn = document.getElementById('rsvp-submit');

  /* Sticky nav */
  const onScroll = () => {
    if (!nav) return;
    nav.classList.toggle('nav-solid', window.scrollY > 40);
  };
  window.addEventListener('scroll', onScroll, { passive: true });
  onScroll();

  /* Mobile menu */
  if (menuBtn && mobileMenu) {
    menuBtn.addEventListener('click', () => {
      const open = mobileMenu.classList.toggle('hidden') === false;
      menuBtn.setAttribute('aria-expanded', String(open));
    });

    mobileMenu.querySelectorAll('a').forEach((link) => {
      link.addEventListener('click', () => {
        mobileMenu.classList.add('hidden');
        menuBtn.setAttribute('aria-expanded', 'false');
      });
    });
  }

  /* Smooth scroll for same-page anchors */
  document.querySelectorAll('a[href^="#"]').forEach((anchor) => {
    anchor.addEventListener('click', (e) => {
      const id = anchor.getAttribute('href');
      if (!id || id === '#') return;
      const target = document.querySelector(id);
      if (!target) return;
      e.preventDefault();
      target.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
  });

  /* Reveal on scroll */
  const reveals = document.querySelectorAll('.reveal');
  if ('IntersectionObserver' in window) {
    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add('is-visible');
            io.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.15, rootMargin: '0px 0px -40px 0px' }
    );
    reveals.forEach((el) => io.observe(el));
  } else {
    reveals.forEach((el) => el.classList.add('is-visible'));
  }

  /* RSVP */
  if (form) {
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      statusEl.textContent = '';
      statusEl.classList.remove('is-ok', 'is-err');

      const data = {
        name: form.name.value.trim(),
        guests: Number(form.guests.value),
        attendance: form.attendance.value,
        message: form.message.value.trim(),
      };

      if (!data.name) {
        statusEl.textContent = 'Пожалуйста, укажите имя.';
        statusEl.classList.add('is-err');
        return;
      }

      submitBtn.disabled = true;
      submitBtn.textContent = 'Отправляем…';

      try {
        const res = await fetch('/api/rsvp', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(data),
        });

        if (!res.ok) {
          const err = await res.json().catch(() => ({}));
          throw new Error(err.detail || 'Не удалось отправить ответ');
        }

        statusEl.textContent =
          data.attendance === 'yes'
            ? 'Спасибо! Ждём вас на празднике.'
            : 'Спасибо, что сообщили. Будем скучать!';
        statusEl.classList.add('is-ok');
        form.reset();
        form.querySelector('input[name="attendance"][value="yes"]').checked = true;
      } catch (err) {
        statusEl.textContent = err.message || 'Что-то пошло не так. Попробуйте ещё раз.';
        statusEl.classList.add('is-err');
      } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Отправить ответ';
      }
    });
  }
})();
