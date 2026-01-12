// --- CONFIGURATION ---
// This points to your Python backend on Hugging Face
const BACKEND_URL = 'https://ndileep-thebigbangtheorytweet.hf.space';
const API_URL = `${BACKEND_URL}/api/predict`;

// --- DOM ELEMENTS ---
const composeInput = document.getElementById('compose-input');
const postBtn = document.getElementById('post-btn');
const feedStream = document.getElementById('feed-stream');
const spinner = document.getElementById('spinner');

// --- STATE ---
let isProcessing = false;

// --- AUTO RESIZE TEXTAREA ---
if (composeInput) {
    composeInput.addEventListener('input', function() {
        this.style.height = 'auto';
        this.style.height = (this.scrollHeight) + 'px';
        
        // Enable/Disable Button
        if (this.value.trim().length > 0) {
            postBtn.classList.add('active');
        } else {
            postBtn.classList.remove('active');
        }
    });
}

// --- POST ACTION ---
if (postBtn) {
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
        renderTweet(
            text, 
            'User', 
            '@user', 
            'Just now', 
            'https://abs.twimg.com/sticky/default_profile_images/default_profile_400x400.png', 
            false, 
            userTweetId
        );

        // Clear Input
        composeInput.value = '';
        composeInput.style.height = 'auto';

        // 3. SHOW TYPING INDICATOR IN FEED
        const loadingElement = showTypingIndicator();

        // 4. Call Backend API
        try {
            const response = await fetch(API_URL, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query: text, min_confidence: 0.2 })
            });

            // Attempt to surface server messages if present
            const textResp = await response.text().catch(() => null);
            if (!response.ok) {
                const errMsg = textResp || response.statusText || 'API Error';
                throw new Error(errMsg);
            }

            const data = textResp ? JSON.parse(textResp) : {};

            // Process Character Data
            const charName = data.prediction || 'Unknown';
            let charImg = data.local_image || data.image;

            // --- IMAGE FIX ---
            // If the backend gives us a relative path (like "/assets/remote/..."),
            // we prepend the Hugging Face URL so the browser can find it.
            if (charImg && charImg.startsWith('/')) {
                charImg = BACKEND_URL + charImg;
            }
            
            // If no image is found, set to empty string so the <img> onerror tag triggers
            if (!charImg) {
                charImg = '';
            }

            const replyText = getCharacterReply(charName);
            
            // Artificial delay to let the user see the "typing" animation
            setTimeout(() => {
                if (loadingElement) loadingElement.remove();

                renderTweet(
                    replyText, 
                    charName, 
                    `@${charName.replace(' ', '_').toLowerCase()}`, 
                    '1s', 
                    charImg, 
                    true, 
                    null, 
                    userTweetId
                );
                finishPost();
            }, 1500);

        } catch (error) {
            console.error('Predict API error:', error);
            // Remove typing indicator immediately
            if (loadingElement) loadingElement.remove();

            // Show a friendly error message
            showError('Server error: ' + error.message);

            // Fallback reply for demo so user sees result flow
            setTimeout(() => {
                renderTweet(
                    "I couldn't reach the server, but that sounded like Sheldon.", 
                    "System", 
                    "@server_bot", 
                    "1s", 
                    "", 
                    true, 
                    null, 
                    userTweetId
                );
                finishPost();
            }, 800);
        }
    });
}

function finishPost() {
    isProcessing = false;
    spinner.style.display = 'none';
    composeInput.disabled = false;
    composeInput.focus();
}

// --- RENDER TYPING INDICATOR ---
function showTypingIndicator() {
    const article = document.createElement('article');
    article.className = 'tweet loading-state';
    
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
    
    feedStream.insertBefore(article, feedStream.firstChild);
    return article; 
}

// --- RENDER TWEET FUNCTION ---
function renderTweet(text, name, handle, time, avatarUrl, isReply, id, replyToId) {
    const article = document.createElement('article');
    article.className = 'tweet';
    if (isReply) article.classList.add('reply');
    
    const safeAvatar = avatarUrl || 'https://abs.twimg.com/sticky/default_profile_images/default_profile_400x400.png';

    const html = `
        ${!isReply && id ? `<div class="thread-line" id="line-${id}"></div>` : ''}
        <img src="${safeAvatar}" class="user-avatar" onerror="this.src='https://abs.twimg.com/sticky/default_profile_images/default_profile_400x400.png'">
        <div class="tweet-content">
            <div class="tweet-header">
                <span class="user-name">${name}</span>
                <span class="user-handle">${handle}</span>
                <span class="time">· ${time}</span>
            </div>
            <div class="tweet-text">${text}</div>
            <div class="tweet-actions">
                <div class="action-item blue"><svg class="action-icon" viewBox="0 0 24 24"><path d="M1.751 10c0-4.42 3.584-8 8.005-8h4.366c4.49 0 8.129 3.64 8.129 8.13 0 2.96-1.607 5.68-4.196 7.11l-8.054 4.46v-3.69h-.067c-4.49.1-8.183-3.51-8.183-8.01zm8.005-6c-3.317 0-6.005 2.69-6.005 6 0 3.37 2.77 6.08 6.138 6.01l.351-.01h1.761v2.3l5.087-2.81c1.951-1.08 3.163-3.13 3.163-5.36 0-3.39-2.744-6.13-6.129-6.13H9.756z"></path></svg> 0</div>
                <div class="action-item green"><svg class="action-icon" viewBox="0 0 24 24"><path d="M4.5 3.88l4.432 4.14-1.364 1.46L5.5 7.55V16c0 1.1.896 2 2 2H13v2H7.5c-2.209 0-4-1.79-4-4V7.55L1.432 9.48.068 8.02 4.5 3.88zM16.5 6H11V4h5.5c2.209 0 4 1.79 4 4v8.45l2.068-1.93 1.364 1.46-4.432 4.14-4.432-4.14 1.364-1.46 2.068 1.93V8c0-1.1-.896-2-2-2z"></path></svg> 0</div>
                <div class="action-item red" onclick="toggleLike(this)"><svg class="action-icon" viewBox="0 0 24 24"><path d="M16.697 5.5c-1.222-.06-2.679.51-3.89 2.16l-.805 1.09-.806-1.09C9.984 6.01 8.526 5.44 7.304 5.5c-1.243.07-2.349.78-2.91 1.91-.552 1.12-.633 2.78.479 4.82 1.074 1.97 3.257 4.27 7.129 6.61 3.87-2.34 6.052-4.64 7.126-6.61 1.111-2.04 1.03-3.7.477-4.82-.561-1.13-1.666-1.84-2.908-1.91zm4.187 7.69c-1.351 2.48-4.001 5.12-8.379 7.67l-.503.3-.504-.3c-4.379-2.55-7.029-5.19-8.382-7.67-1.36-2.5-1.41-4.86-.514-6.67.887-1.79 2.647-2.91 4.601-3.01 1.651-.09 3.368.56 4.798 2.01 1.429-1.45 3.146-2.1 4.796-2.01 1.954.1 3.714 1.22 4.605 3.01.894 1.81.844 4.17-.518 6.67z"></path></svg> <span class="like-count">0</span></div>
                <div class="action-item"><svg class="action-icon" viewBox="0 0 24 24"><path d="M8.75 21V3h2v18h-2zM18 21V8.5h2V21h-2zM4 21l.004-10h2L6 21H4zm9.248 0v-7h2v7h-2z"></path></svg> 0</div>
            </div>
        </div>
    `;
    article.innerHTML = html;

    if (replyToId) {
        feedStream.insertBefore(article, feedStream.firstChild);
    } else {
        feedStream.insertBefore(article, feedStream.firstChild);
    }
}

// --- LIKE TOGGLE (Global Scope for HTML onclick) ---
window.toggleLike = function(el) {
    el.classList.toggle('liked');

    let countSpan = el.querySelector('.like-count');
    if (!countSpan) {
        const textNode = Array.from(el.childNodes).find(n => n.nodeType === Node.TEXT_NODE && n.textContent.trim());
        const txt = textNode ? textNode.textContent.trim() : '0';
        if (textNode) textNode.remove();
        countSpan = document.createElement('span');
        countSpan.className = 'like-count';
        countSpan.innerText = txt;
        el.appendChild(countSpan);
    }

    const raw = (countSpan.innerText || '').trim();
    let count = parseAbbreviatedNumber(raw);
    if (isNaN(count)) count = 0;

    if (el.classList.contains('liked')) {
        count++;
    } else {
        count = Math.max(0, count - 1);
    }

    countSpan.innerText = formatAbbreviatedNumber(count);
}

function parseAbbreviatedNumber(str) {
    if (!str) return 0;
    const s = str.replace(/[, ]+/g, '').toUpperCase();
    const m = s.match(/^([0-9]*\.?[0-9]+)([KMB])?$/);
    if (!m) return parseInt(s) || 0;
    const val = parseFloat(m[1]);
    const suffix = m[2];
    if (!suffix) return Math.round(val);
    if (suffix === 'K') return Math.round(val * 1000);
    if (suffix === 'M') return Math.round(val * 1000000);
    if (suffix === 'B') return Math.round(val * 1000000000);
    return Math.round(val);
}

function formatAbbreviatedNumber(n) {
    if (n >= 1000000) {
        const v = (n / 1000000);
        return (Math.round(v * 10) / 10).toString().replace(/\.0$/, '') + 'M';
    }
    if (n >= 1000) {
        const v = (n / 1000);
        return (Math.round(v * 10) / 10).toString().replace(/\.0$/, '') + 'K';
    }
    return String(n);
}

// --- ERROR DISPLAY ---
function showError(message) {
    try {
        const existing = document.getElementById('api-error-widget');
        if (existing) existing.remove();

        const box = document.createElement('div');
        box.id = 'api-error-widget';
        box.className = 'widget';
        box.style.border = '1px solid rgba(255,80,80,0.12)';
        box.style.background = '#2a1b1b';
        box.style.color = '#ffdcdc';
        box.style.marginBottom = '12px';
        box.innerHTML = `
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
                <div style="font-weight:800;">Connection Error</div>
                <button style="background:transparent;color:var(--text-secondary);border-radius:6px;padding:6px;cursor:pointer;" aria-label="close">✕</button>
            </div>
            <div style="color:var(--text-secondary);font-size:14px;">${message}</div>
        `;

        const closeBtn = box.querySelector('button');
        closeBtn.addEventListener('click', () => box.remove());

        feedStream.insertBefore(box, feedStream.firstChild);
    } catch (e) {
        console.error('Failed to show error widget', e);
        alert(message);
    }
}

// --- CHARACTER REPLIES ---
function getCharacterReply(name) {
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

    const generic = [
        "I believe that was my line.",
        "Yes, I recall saying that.",
        "That sounds exactly like me.",
        "You have excellent hearing. That was me.",
        "A quote attributed to me? Fascinating.",
        "Indeed."
    ];

    const characterKey = Object.keys(replies).find(key => cleanName.includes(key));
    const pool = characterKey ? replies[characterKey] : generic;

    return pool[Math.floor(Math.random() * pool.length)];
}