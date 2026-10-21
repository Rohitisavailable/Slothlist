const $ = (selector) => document.querySelector(selector);
const textarea = $('#tasks');
const button = $('#plan-button');
const statusLabel = $('#connection-label');
const modelHint = $('#model-hint');
const energy = $('#energy');
let assistantId = '';
try { assistantId = localStorage.getItem('slothlist_backboard_assistant') || ''; } catch { /* storage may be disabled */ }

textarea.addEventListener('input', () => { $('#char-count').textContent = `${textarea.value.length} / 6000`; });
energy.addEventListener('input', () => { $('#energy-value').textContent = `${energy.value} / 5`; });

async function checkStatus() {
  try {
    const response = await fetch('/api/status');
    const info = await response.json();
    statusLabel.textContent = info.backboard ? 'Backboard key configured' : 'Backboard key needed';
    modelHint.textContent = `${info.provider}/${info.model} · Backboard receives task text when you make a plan`;
  } catch {
    statusLabel.textContent = 'Local server unavailable';
  }
}

function safeText(value) { return String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }
function array(value) { return Array.isArray(value) ? value : []; }

function renderPlan(plan) {
  const actions = array(plan.actions).slice(0, 3);
  const later = array(plan.later).slice(0, 8);
  const delegate = array(plan.delegate).slice(0, 4);
  const actionHtml = actions.map(item => `<div class="action"><button class="check" aria-label="Mark complete" type="button"></button><div class="action-text"><strong>${safeText(typeof item === 'string' ? item : item.title)}</strong>${item.why ? `<span>${safeText(item.why)}</span>` : ''}</div></div>`).join('');
  const laterHtml = later.length ? `<div class="result-section"><h3>Can wait</h3><ul class="later-list">${later.map(item => `<li>${safeText(item)}</li>`).join('')}</ul></div>` : '';
  const delegateHtml = delegate.length ? `<div class="result-section"><h3>Could leave your plate</h3><ul class="later-list">${delegate.map(item => `<li>${safeText(item)}</li>`).join('')}</ul></div>` : '';
  $('#result-card').innerHTML = `<div class="result-kicker">YOUR DAY, WITH ROOM TO BREATHE</div><h2 class="result-headline">${safeText(plan.headline || 'One thing at a time.')}</h2><div class="first-step"><small>Start here</small><p>${safeText(plan.first_step || (actions[0]?.title ?? 'Take one slow breath.'))}</p></div>${actionHtml ? `<div class="result-section"><h3>A few small moves</h3>${actionHtml}</div>` : ''}${laterHtml}${delegateHtml}<div class="gentle-note">${safeText(plan.gentle_note || 'You can stop when your energy says stop.')}</div>`;
  $('#result-card').classList.remove('hidden');
  $('#empty-state').classList.add('hidden');
  $('#result-card').querySelectorAll('.check').forEach(check => check.addEventListener('click', () => check.classList.toggle('done')));
}

button.addEventListener('click', async () => {
  if (!textarea.value.trim()) { textarea.focus(); return; }
  button.disabled = true;
  button.querySelector('span:nth-child(2)').textContent = 'Finding a gentle starting point…';
  try {
    const response = await fetch('/api/plan', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        tasks: textarea.value,
        energy: Number(energy.value),
        minutes: Number($('#minutes').value),
        assistant_id: assistantId || undefined,
        remember_preferences: $('#remember-preferences').checked
      })
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || 'Something went wrong.');
    if (result.assistant_id) {
      assistantId = result.assistant_id;
      try { localStorage.setItem('slothlist_backboard_assistant', assistantId); } catch { /* plan still works without persistence */ }
    }
    renderPlan(result);
  } catch (error) {
    $('#result-card').innerHTML = `<div class="result-kicker">A SMALL PAUSE</div><h2 class="result-headline">We couldn't make that plan.</h2><div class="error-note">${safeText(error.message)}</div><div class="gentle-note">Your task text is sent to Backboard when you request a plan. Backboard may retain its hosted thread.</div>`;
    $('#result-card').classList.remove('hidden');
    $('#empty-state').classList.add('hidden');
  } finally {
    button.disabled = false;
    button.querySelector('span:nth-child(2)').textContent = 'Make me a gentle plan';
  }
});

checkStatus();
