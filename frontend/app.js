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
// --- UPDATED POST ACTION ---
    postBtn.addEventListener('click', async () => {
        if (isProcessing) return;
        const text = composeInput.value.trim();
        if (!text) return;

        // 1. UI Updates: Disable input, show spinner in button
        isProcessing = true;
        postBtn.classList.remove('active');
        composeInput.disabled = true;
        spinner.style.display = 'block';

        // 2. Render User's Post Immediately
        const userTweetId = Date.now();
        renderTweet(text, 'User', '@user', 'Just now', 'https://abs.twimg.com/sticky/default_profile_images/default_profile_400x400.png', false, userTweetId);

        // Clear Input
        composeInput.value = '';
        composeInput.style.height = 'auto';

        // 3. SHOW TYPING INDICATOR IN FEED
        const loadingElement = showTypingIndicator();

        // 4. Call Backend API (Simulated)
        try {
            const response = await fetch('/api/predict', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query: text, min_confidence: 0.2 })
            });

            if (!response.ok) throw new Error('API Error');
            const data = await response.json();

            // Process Character Data
            const charName = data.prediction || 'Unknown';
            let charImg = data.local_image || data.image;
            if (!charImg) charImg = `assets/${charName.toLowerCase().replace(/[^a-z0-9]/g, '_')}.svg`; 

            const replyText = getCharacterReply(charName);
            
            // Artificial delay to let the user see the "typing" animation
            setTimeout(() => {
                // REMOVE TYPING INDICATOR
                if(loadingElement) loadingElement.remove();

                // Add Real Reply
                renderTweet(replyText, charName, `@${charName.replace(' ', '_').toLowerCase()}`, '1s', charImg, true, null, userTweetId);
                finishPost();
            }, 1500); // Increased delay slightly for effect

        } catch (error) {
            console.error(error);
            // Fallback for demo
            setTimeout(() => {
                if(loadingElement) loadingElement.remove(); // Remove indicator
                renderTweet("I couldn't reach the server, but that sounded like Sheldon.", "System", "@server_bot", "1s", "", true, null, userTweetId);
                finishPost();
            }, 1000);
        }
    });

    // --- NEW FUNCTION: RENDER TYPING INDICATOR ---
    function showTypingIndicator() {
        const article = document.createElement('article');
        article.className = 'tweet loading-state';
        
        // We use a generic "system" avatar or transparent one for the loading state
        article.innerHTML = `
            <div class="user-avatar" style="background: transparent;"></div>
            <div class="tweet-content">
                <div class="tweet-header">
                    <span class="user-name" style="color: var(--text-secondary);">Identifying character</span>
                </div>
                <div class="typing-container">
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                </div>
            </div>
        `;
        
        // Insert at the top of the feed (before the user's post moves down, or right after it)
        feedStream.insertBefore(article, feedStream.firstChild);
        return article; // Return element so we can remove it later
    }
function getCharacterReply(name) {
    // Normalize name to lowercase for easier matching
    const cleanName = name.toLowerCase();

    const replies = {
        sheldon: [
            "Bazinga! I fooled you.",
            "That is my spot. And that is my line.",
            "I'm not crazy, my mother had me tested.",
            "Please, I have a master's degree and two doctorates. Of course I said that.",
            "In the world of minions, I am the Gru. That is my dialogue.",
            "It's a non-optional social convention that you credit me for that quote.",
            "Oh, gravity, thou art a heartless bitch. (Also, I said that)."
        ],
        leonard: [
            "Yeah, yeah, I said it. Can we go now?",
            "Why does everything always have to be about Sheldon?",
            "I did say that. And I regret it immediately.",
            "That sounds like something I'd say while Penny is ignoring me.",
            "Sarcasm sign? No? Okay, yes, that was me.",
            "I put up with a lot, but yes, that is my line."
        ],
        penny: [
            "Holy crap on a cracker, I actually said that?",
            "I need a glass of wine to deal with this.",
            "Yeah, I said it. Don't look at me like I'm stupid.",
            "Is that a science thing? Because I definitely said it.",
            "Knock, knock, knock. Penny. That's me.",
            "Sweetie, I say a lot of things."
        ],
        howard: [
            "I went to space! Of course I said something that cool.",
            "That's the engineer talking. MIT, baby!",
            "Did my mother tell you that? BECAUSE I AM AN ASTRONAUT.",
            "That line works on all the ladies. Trust me.",
            "I believe the term you are looking for is 'Wolowitzed'.",
            "Bernadette would kill me if she knew I repeated that."
        ],
        raj: [
            "(Whispers in ear) *He says he definitely said that.*",
            "I'm comfortable with my masculinity, and I stand by that quote.",
            "That was beautiful. Like a Bollywood movie.",
            "My father paid a lot of money for me to say that.",
            "Did you know I have a dog named Cinnamon? Also, yes, I said that.",
            "Please don't send me back to India, I am being witty!"
        ],
        amy: [
            "According to my research, that is indeed my utterance.",
            "I find your obsession with my quotes... titillating.",
            "Sheldon, look! They are quoting me!",
            "That is scientifically accurate and socially awkward. Definitely me.",
            "My hippocampus retains the memory of saying exactly that."
        ]
    };

    // Generic fallback for unknown characters
    const generic = [
        "I believe that was my line.",
        "Yes, I recall saying that.",
        "That sounds exactly like me.",
        "You have excellent hearing. That was me.",
        "A quote attributed to me? Fascinating.",
        "Indeed."
    ];

    // 1. Check if we have specific lines for this character
    // We search the keys (e.g., if API returns "Sheldon Cooper", we match "sheldon")
    const characterKey = Object.keys(replies).find(key => cleanName.includes(key));

    // 2. Select the array (specific or generic)
    const pool = characterKey ? replies[characterKey] : generic;

    // 3. Return a random item from the selected pool
    return pool[Math.floor(Math.random() * pool.length)];
}