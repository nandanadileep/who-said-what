const btn = document.getElementById('predict');
const genBtn = document.getElementById('generate');
const clearBtn = document.getElementById('clear');
const queryEl = document.getElementById('query');
const avatar = document.getElementById('avatar');
const nameEl = document.getElementById('name');
const confEl = document.getElementById('confidence');
const scoresEl = document.getElementById('scores');

// Defensive UI fixes: remove accidental HTML dumped into the textarea
document.addEventListener('DOMContentLoaded', () => {
  try {
    if (queryEl && queryEl.value && queryEl.value.includes('<button')) {
      // Clear accidental paste of HTML controls
      queryEl.value = '';
    }

    // Ensure .controls isn't accidentally nested inside the textarea
    const controls = document.querySelector('.controls');
    const panel = document.querySelector('.panel');
    if (controls && panel && controls.parentElement && controls.parentElement.tagName.toLowerCase() === 'textarea') {
      panel.appendChild(controls);
    }
  } catch (e) {
    // non-fatal
    console.warn('UI init cleanup error', e);
  }
});

const mapToAsset = (char) => {
  if (!char) return 'assets/unknown.svg';
  const file = char.toLowerCase().replace(/[^a-z0-9]+/g, '_') + '.svg';
  return 'assets/' + file;
}

async function predict(){
  const q = queryEl.value.trim();
  if(!q) return;

  nameEl.textContent = 'Thinking...';
  confEl.textContent = '';
  scoresEl.textContent = '';

  try{
    let res = null;
    try{
      res = await fetch('/api/predict', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({query: q, min_confidence: 0.2})
    });
    }catch(e){
      // network error calling primary endpoint, fall back to demo
      try{
        res = await fetch('/api/predict_demo', {
          method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({query: q, min_confidence: 0.2})
        });
      }catch(e2){
        nameEl.textContent = 'Network Error';
        avatar.src = 'assets/unknown.svg';
        scoresEl.textContent = e.toString();
        return;
      }
    }

    if(!res.ok){
      const err = await res.json().catch(()=>({status:res.status}));
      nameEl.textContent = 'Error';
      scoresEl.textContent = JSON.stringify(err);
      avatar.src = 'assets/unknown.svg';
      return;
    }

    const data = await res.json();
    const char = data.prediction || null;
    const conf = data.confidence ?? 0;
    const scores = data.all_scores || {};

    // Prefer cached local image, then server-provided external image, then fallback SVG
    if (data.local_image) {
      avatar.src = data.local_image;
    } else if (data.image) {
      avatar.src = data.image;
    } else {
      avatar.src = mapToAsset(char);
    }

    nameEl.textContent = char || 'Unknown';
    // Do not display confidence in the UI tweet card per request.
    confEl.textContent = '';
    scoresEl.textContent = Object.entries(scores).map(([k,v])=>`${k}: ${v}`).join('\n');

  }catch(e){
    nameEl.textContent = 'Network Error';
    avatar.src = 'assets/unknown.svg';
    scoresEl.textContent = e.toString();
  }
  // return the last response shown to UI for chaining
  return {prediction: nameEl.textContent === 'Unknown' ? null : nameEl.textContent, confidence: confEl.textContent};
}

btn.addEventListener('click', predict);
genBtn.addEventListener('click', async ()=>{
  // If we don't have a current predicted character, run predict first
  if(!nameEl.textContent || nameEl.textContent === '—' || nameEl.textContent === 'Thinking...'){
    await predict();
  }

  // Use the current displayed name to map to an asset
  const char = (nameEl.textContent && nameEl.textContent !== 'Unknown' && nameEl.textContent !== '—') ? nameEl.textContent : null;
  avatar.src = mapToAsset(char);

  // small visual feedback
  avatar.style.transition = 'transform 160ms ease';
  avatar.style.transform = 'scale(0.96)';
  setTimeout(()=> avatar.style.transform = 'scale(1)', 160);
});
clearBtn.addEventListener('click', ()=>{queryEl.value=''; nameEl.textContent='—'; confEl.textContent=''; scoresEl.textContent=''; avatar.src='assets/unknown.svg'})

// Submit on Ctrl+Enter
queryEl.addEventListener('keydown', (e)=>{if((e.ctrlKey||e.metaKey) && e.key==='Enter'){predict()}})
