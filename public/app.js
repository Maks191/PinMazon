const form = document.querySelector('#generator');
const submit = document.querySelector('#submit');
const empty = document.querySelector('#empty');
const loading = document.querySelector('#loading');
const errorBox = document.querySelector('#error');
const resultBox = document.querySelector('#result');
const apiAccess = document.querySelector('#api-access');
const manualAccess = document.querySelector('#manual-access');
const apiModeButton = document.querySelector('#api-mode');
const manualModeButton = document.querySelector('#manual-mode');
const apiKeyInput = form.elements.openai_api_key;
const manualJsonInput = form.elements.pin_copy_json;
const aiBackground = document.querySelector('#ai-background');
let mode = 'manual';

function setMode(nextMode) {
  mode = nextMode;
  const manual = mode === 'manual';
  apiAccess.hidden = manual;
  manualAccess.hidden = !manual;
  aiBackground.hidden = manual;
  apiKeyInput.required = !manual;
  manualJsonInput.required = manual;
  form.elements.use_ai_background.disabled = manual;
  if (manual) form.elements.use_ai_background.checked = false;
  manualModeButton.classList.toggle('active', manual);
  apiModeButton.classList.toggle('active', !manual);
  submit.childNodes[0].nodeValue = manual ? 'Render Pin from JSON ' : 'Generate Pin Pack ';
}

manualModeButton.addEventListener('click', () => setMode('manual'));
apiModeButton.addEventListener('click', () => setMode('api'));

document.querySelector('#copy-prompt').addEventListener('click', async () => {
  const productName = form.elements.product_name.value.trim();
  if (!productName) {
    document.querySelector('#prompt-status').textContent = 'Fill Product name first.';
    form.elements.product_name.focus();
    return;
  }
  const prompt = `Create one compliant Pinterest copy package in English for this verified product.

Product name: ${productName}
Verified facts only: ${form.elements.features.value.trim() || 'No verified technical specifications supplied.'}
Audience: ${form.elements.audience.value}
Content cluster: ${form.elements.cluster.value}
Visual style: ${form.elements.style.value}

Return ONLY valid JSON, with no markdown and exactly these fields:
{
  "headline": "",
  "bullets": ["", ""],
  "title": "",
  "description": "",
  "alt_text": "",
  "short_description": "",
  "hashtags": [],
  "keywords": [],
  "visual_prompt": ""
}

Rules: use only supplied facts; never invent price, discount, rating, reviews, compatibility or specifications. Headline 2-6 words. Exactly two bullets, each 2-6 words. Title max 100 characters. Description max 500 characters and must end exactly with: Affiliate links may earn commission. Use 10-15 targeted hashtags and 3-8 keywords. No BUY NOW or aggressive CTA. The real product image is composited separately, so visual_prompt describes a background only, with no product, logo or text.`;
  try {
    await navigator.clipboard.writeText(prompt);
    document.querySelector('#prompt-status').textContent = 'Prompt copied. Paste it into ChatGPT.';
  } catch (_) {
    document.querySelector('#prompt-status').textContent = 'Clipboard was blocked. Copy the prompt from the dialog.';
    window.prompt('Copy this prompt for ChatGPT:', prompt);
  }
});

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
    const endpoint = mode === 'manual' ? '/api/render-manual' : '/api/generate';
    const response = await fetch(endpoint, { method: 'POST', body: new FormData(form) });
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
    apiKeyInput.value = '';
  }
});

setMode('manual');
