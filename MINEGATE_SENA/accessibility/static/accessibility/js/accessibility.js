let fontSizeFactor = 100;
let isHighContrast = false;
let filterStates = {
    'underline-links': false,
    'big-cursor': false,
    'extra-spacing': false,
    'high-contrast-mode': false
};
let isReading = false;
let guideEnabled = false;
let guideElement = null;

document.addEventListener('DOMContentLoaded', () => {
    loadSettings();
    initializeReadingGuide();
    applyAccessibilityChanges();
    setupEventListeners();
});

function loadSettings() {
    const savedFont = localStorage.getItem('mg-font');
    if (savedFont) fontSizeFactor = parseInt(savedFont);
    
    const savedContrast = localStorage.getItem('mg-contrast');
    if (savedContrast === 'true') {
        isHighContrast = true;
        filterStates['high-contrast-mode'] = true;
    }
    
    Object.keys(filterStates).forEach(filter => {
        const saved = localStorage.getItem('mg-' + filter);
        if (saved === 'true') filterStates[filter] = true;
    });
}

function initializeReadingGuide() {
    if (!document.getElementById('reading-guide')) {
        guideElement = document.createElement('div');
        guideElement.id = 'reading-guide';
        guideElement.style.cssText = `
            display: none;
            position: fixed;
            height: 12px;
            width: 100%;
            background: rgba(255, 235, 0, 0.7);
            z-index: 2147483647;
            pointer-events: none;
            top: 0;
            left: 0;
            will-change: transform;
            box-shadow: 0 0 12px rgba(255, 255, 0, 0.9);
            border-bottom: 2px solid #ffd600;
        `;
        document.body.appendChild(guideElement);
    } else {
        guideElement = document.getElementById('reading-guide');
    }
}

function initializeReadingGuide() {
    guideElement = document.getElementById('reading-guide');
    if (!guideElement) {
        guideElement = document.createElement('div');
        guideElement.id = 'reading-guide';
        document.body.appendChild(guideElement);
    }
}

function setupEventListeners() {
    window.addEventListener('mousemove', (e) => {
        if (guideEnabled && guideElement) {
            guideElement.style.setProperty('--mouse-x', e.clientX + 'px');
            guideElement.style.setProperty('--mouse-y', e.clientY + 'px');
            
            if (guideElement.style.display !== 'block') {
                guideElement.style.display = 'block';
            }
        }
    });

    document.addEventListener('click', (e) => {
        const panel = document.getElementById('accPanel');
        const trigger = document.querySelector('.minegate-acc-trigger');
        if (panel && trigger && !panel.contains(e.target) && !trigger.contains(e.target)) {
            panel.style.display = 'none';
        }
    });
}


function toggleAccPanel() {
    const panel = document.getElementById('accPanel');
    if (panel) {
        panel.style.display = (panel.style.display === 'block') ? 'none' : 'block';
    }
}

function adjustFont(dir) {
    fontSizeFactor += (dir * 10);
    fontSizeFactor = Math.min(Math.max(fontSizeFactor, 70), 150);
    localStorage.setItem('mg-font', fontSizeFactor);
    applyAccessibilityChanges();
}

function handleContrast() {
    isHighContrast = !isHighContrast;
    filterStates['high-contrast-mode'] = isHighContrast;
    localStorage.setItem('mg-contrast', isHighContrast);
    applyAccessibilityChanges();
}

function toggleFeature(className) {
    filterStates[className] = !filterStates[className];
    localStorage.setItem('mg-' + className, filterStates[className]);
    applyAccessibilityChanges();
}

function toggleReadingGuide() {
    guideEnabled = !guideEnabled;
    if (guideElement) {
        guideElement.style.display = guideEnabled ? 'block' : 'none';
    }
}

function applyAccessibilityChanges() {
    document.documentElement.style.fontSize = fontSizeFactor + "%";
    
    const body = document.body;
    body.classList.toggle('underline-links', filterStates['underline-links']);
    body.classList.toggle('big-cursor', filterStates['big-cursor']);
    body.classList.toggle('extra-spacing', filterStates['extra-spacing']);
    body.classList.toggle('high-contrast-mode', filterStates['high-contrast-mode']);
}

function handleTextToSpeech() {
    if (!isReading) {
        const text = window.getSelection().toString() || document.body.innerText;
        if (!text.trim()) return;

        const msg = new SpeechSynthesisUtterance(text);
        msg.lang = 'es-ES';
        msg.onend = () => isReading = false;
        msg.onerror = () => isReading = false;
        window.speechSynthesis.speak(msg);
        isReading = true;
    } else {
        window.speechSynthesis.cancel();
        isReading = false;
    }
}

function resetAll() {
    fontSizeFactor = 100;
    isHighContrast = false;
    filterStates = {
        'underline-links': false,
        'big-cursor': false,
        'extra-spacing': false,
        'high-contrast-mode': false
    };
    
    localStorage.clear();
    
    guideEnabled = false;
    if (guideElement) guideElement.style.display = 'none';
    
    window.speechSynthesis.cancel();
    isReading = false;
    
    applyAccessibilityChanges();
    
    const panel = document.getElementById('accPanel');
    if (panel) panel.style.display = 'none';
}