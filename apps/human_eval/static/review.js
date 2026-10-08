document.addEventListener('DOMContentLoaded', function () {
  // --- Unsaved-changes guard ---
  var dirty = false;
  window.addEventListener('beforeunload', function (e) {
    if (dirty) {
      e.preventDefault();
      e.returnValue = '';
    }
  });

  // --- Likert selection: color the card border, advance active field ---
  document.querySelectorAll('.likert-option input[type="radio"]').forEach(function (radio) {
    radio.addEventListener('change', function () {
      dirty = true;
      var fieldCard = this.closest('.field-card');
      if (!fieldCard) return;
      for (var i = 1; i <= 5; i++) {
        fieldCard.classList.remove('answered-' + i);
      }
      fieldCard.classList.add('answered-' + this.value);
      setActiveField(nextUnansweredCard() || fieldCard);
    });
  });

  // --- Active field management (for keyboard shortcuts) ---
  var fieldCards = Array.prototype.slice.call(document.querySelectorAll('#review-form .field-card'));

  function cardAnswered(card) {
    return Array.prototype.some.call(
      card.querySelectorAll('input[type="radio"]'),
      function (r) { return r.checked; }
    );
  }

  function nextUnansweredCard() {
    for (var i = 0; i < fieldCards.length; i++) {
      if (!cardAnswered(fieldCards[i])) return fieldCards[i];
    }
    return null;
  }

  function setActiveField(card) {
    fieldCards.forEach(function (c) { c.classList.remove('field-active'); });
    if (card) card.classList.add('field-active');
  }

  var activeCard = function () {
    return document.querySelector('#review-form .field-card.field-active');
  };

  if (fieldCards.length) {
    setActiveField(nextUnansweredCard() || fieldCards[0]);
    // Clicking anywhere in a card makes it the active one
    fieldCards.forEach(function (card) {
      card.addEventListener('click', function () { setActiveField(card); });
    });
  }

  // --- Keyboard shortcuts: 1-5 rate, Enter submit, arrows navigate ---
  var form = document.getElementById('review-form');
  document.addEventListener('keydown', function (e) {
    if (!form) return;
    var tag = (document.activeElement && document.activeElement.tagName) || '';
    if (tag === 'INPUT' && document.activeElement.type === 'text') return;
    if (tag === 'TEXTAREA') return;

    if (e.key >= '1' && e.key <= '5') {
      var card = activeCard() || nextUnansweredCard();
      if (card) {
        var radio = card.querySelector('input[value="' + e.key + '"]');
        if (radio) {
          radio.checked = true;
          radio.dispatchEvent(new Event('change'));
          e.preventDefault();
        }
      }
    } else if (e.key === 'Enter') {
      e.preventDefault();
      form.requestSubmit();
    }
  });

  // --- Validation: all three fields must be rated before submit ---
  if (form) {
    form.addEventListener('submit', function (e) {
      dirty = false;
      var unanswered = fieldCards.filter(function (card) { return !cardAnswered(card); });
      if (unanswered.length) {
        e.preventDefault();
        unanswered.forEach(function (card) {
          card.style.borderColor = '#dc3545';
          card.style.boxShadow = '0 0 0 2px rgba(220, 53, 69, 0.2)';
        });
        setActiveField(unanswered[0]);
        unanswered[0].scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
    });
  }

  // --- Initialize border colors for pre-filled (revisited) forms ---
  document.querySelectorAll('.likert-option input[type="radio"]:checked').forEach(function (radio) {
    var fieldCard = radio.closest('.field-card');
    if (fieldCard) fieldCard.classList.add('answered-' + radio.value);
  });

  // --- Likert definition hints on hover ---
  var defaultHintText = 'Hover over a label or rating to see its full definition.';
  document.querySelectorAll('.likert-scale').forEach(function (scale) {
    var hint = scale.querySelector('.likert-definition-hint');
    if (!hint) return;
    scale.querySelectorAll('[data-definition]').forEach(function (el) {
      el.addEventListener('mouseenter', function () {
        hint.textContent = this.getAttribute('data-definition');
        hint.classList.add('has-definition');
      });
    });
    scale.addEventListener('mouseleave', function () {
      hint.textContent = defaultHintText;
      hint.classList.remove('has-definition');
    });
  });

  // --- Copy URL buttons (admin) ---
  document.querySelectorAll('.btn-copy').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var input = this.closest('.copy-url-container').querySelector('input');
      if (input) {
        navigator.clipboard.writeText(input.value).then(function () {
          btn.textContent = 'Copied!';
          setTimeout(function () { btn.textContent = 'Copy'; }, 2000);
        });
      }
    });
  });
});
