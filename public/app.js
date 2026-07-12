const form = document.querySelector('#generator');
const submit = document.querySelector('#submit');
const empty = document.querySelector('#empty');
const loading = document.querySelector('#loading');
const errorBox = document.querySelector('#error');
const resultBox = document.querySelector('#result');

function showState(state) {
  empty.hidden = state !== 'empty';
  loading.hidden = state !== 'loading';
  errorBox.hidden = state !== 'error';
  resultBox.hidden = state !== 'result';
  submit.disabled = state === 'loading';
}

function dataUrlToBlobUrl(dataUrl) {
  const [header, payload] = dataUrl.split(',');
  const mime = header.match(/:(.*?);/)[1];
  const bytes = Uint8Array.from(atob(payload), character => character.charCodeAt(0));
  return URL.createObjectURL(new Blob([bytes], { type: mime }));
}

form.addEventListener('submit', async event => {
  event.preventDefault();
  showState('loading');
  errorBox.textContent = '';

  try {
    const response = await fetch('/api/generate', { method: 'POST', body: new FormData(form) });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.detail || 'Generation failed.');

    const imageUrl = `data:image/png;base64,${payload.image_base64}`;
    document.querySelector('#pin-preview').src = imageUrl;
    document.querySelector('#download-png').href = dataUrlToBlobUrl(imageUrl);
    document.querySelector('#download-json').href = URL.createObjectURL(
      new Blob([JSON.stringify(payload.metadata, null, 2)], { type: 'application/json' })
    );
    document.querySelector('#headline').textContent = payload.copy.headline;
    document.querySelector('#bullets').textContent = payload.copy.bullets.join(' · ');
    document.querySelector('#pin-title').textContent = payload.copy.title;
    document.querySelector('#description').textContent = payload.copy.description;
    document.querySelector('#destination').textContent = payload.destination_url;
    showState('result');
  } catch (error) {
    errorBox.textContent = error.message;
    showState('error');
  } finally {
    form.elements.openai_api_key.value = '';
  }
});
