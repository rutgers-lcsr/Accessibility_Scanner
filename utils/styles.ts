/**
 * This script is intended to be used as a template for injection.
 *
 * var injections = []; // This will be replaced with actual injections by the style_generator.py
 *
 * This script provides a way to display tooltips on elements that have been styled,
 * giving users information about the changes made, their impact, and links to learn more.
 *
 * This script requires to be compiled with the following command:
 * tsc utils/styles.ts --outFile utils/styles.js --lib DOM,es2021 --target es2015
 *
 */

// Add some global styles for the tooltip
const style = document.createElement('style');
style.innerHTML = `
    .a11y-minor {
        border: 3px solid #ffe066 !important;
        box-shadow: 0 0 6px 1px #ffe06655 !important;
    }
    .a11y-moderate {
        border: 3px solid #ffa94d !important;
        box-shadow: 0 0 6px 1px #ffa94d55 !important;
    }
    .a11y-serious {
        border: 3px solid #fa5252 !important;
        box-shadow: 0 0 6px 1px #fa525255 !important;
    }
    .a11y-critical {
        border: 3px solid #800f2f !important;
        box-shadow: 0 0 8px 2px #800f2f88 !important;
    }
    .animation-highlight {
        animation: highlight 1.5s cubic-bezier(.4,0,.2,1) !important;
    }
    @keyframes highlight {
        0% {
            box-shadow: 0 0 8px 2px #ffe066 !important;
        }
        50% {
            box-shadow: 0 0 16px 6px #ffa94d !important;
        }
        100% {
            box-shadow: 0 0 8px 2px #ffe066 !important;
        }
    }
    .a11y-tooltip {
        all: unset;
        box-sizing: border-box ;
        max-width: 500px ;
        min-width: 300px ;
        overflow-wrap: break-word ;
        z-index: 9997 ;
        font-family: 'Segoe UI', Arial, sans-serif !important; 
        font-size: 15px ;
        line-height: 1.5 ;
        position: absolute ;
        background: linear-gradient(135deg, #fffbe6 0%, #f8f9fa 100%) ;
        color: #222 ;
        border-radius: 10px ;
        border: 1px solid #e9ecef ;
        box-shadow: 0 4px 16px rgba(0,0,0,0.12), 0 1.5px 4px rgba(0,0,0,0.08) ;
        display: none;
        max-height: 400px ;
        overflow: auto ;
        top: 10px ;
        left: 10px ;
        transition: box-shadow 0.2s ;
        animation: fadeIn 0.3s ease-in-out ;

    }
    .a11y-tooltip pre {
        white-space: pre-wrap ;
        word-wrap: break-word ;
        background-color: #f1f3f5 ;
        padding: 6px 8px ;
        border-radius: 4px ;
        font-family: 'Fira Mono', 'Consolas', monospace ;
        font-size: 13px ;
        max-height: 180px ;
        overflow: auto ;
        margin-bottom: 6px ;
    }
    .a11y-tooltip a {
        color: #1976d2 ;
        text-decoration: underline ;
        font-weight: 500 ;
        transition: color 0.15s ;
    }
    .a11y-tooltip a:hover {
        color: #0d47a1 ;
        text-decoration: underline ;
    }
    .a11y-tooltip-message:hover {
        background-color: #f3f0ff ;
    }
    @media (max-width: 600px) {
        .a11y-tooltip {
            max-width: 96vw ;
            min-width: 140px ;
            font-size: 13px ;
        }
        .a11y-tooltip-message {
            font-size: 13px ;
        }
        .a11y-tooltip pre {
            font-size: 11px ;
        }
        .a11y-alert {
            font-size: 12px ;
            overflow-wrap: break-word ;
            max-width: 180px ;
        }
    }
    .a11y-tooltip-message {
        line-height: 1.5 ;
        font-size: 15px ;
        z-index: 9998 ;
        position: relative ;
        cursor: pointer ;
        font-weight: 500 ;
        padding: 7px 6px 7px 6px ;
        border-radius: 6px ;
        border: 1.5px solid transparent ;
        background: transparent ;
        transition: background 0.15s, border 0.15s ;
    }
    .a11y-tooltip-message-content {
        cursor: pointer ;
        font-weight: 500 ;
        line-height: 1.4 ;
        font-size: 15px ;
        padding: 0 ;
        margin: 0 ;
    }
    .a11y-message-ai-button {
        margin-top: 8px ;
        padding: 6px 12px ;
        border: none ;
        border-radius: 4px ;
        background-color: #1976d2 ;
        color: white ;
        cursor: pointer ;
        font-size: 13px ;
        font-weight: 500 ;
        transition: background-color 0.2s ;
        box-shadow: 0 2px 6px rgba(0,0,0,0.2) ;
        z-index: 9999 ;
    }
    .a11y-message-ai-button:hover {
        background-color: #0d47a1 ;
    }
    .a11y-alert {
        position: fixed;
        top: 18px;
        right: 18px;
        background: linear-gradient(90deg, #d7263d 0%, #a41313 100%);
        color: #fff;
        padding: 13px 18px;
        border-radius: 7px;
        z-index: 10000;
        font-family: 'Segoe UI', Arial, sans-serif;
        font-size: 15px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.18);
        font-weight: 500;
        letter-spacing: 0.01em;
        border: 1px solid #fff3;
        opacity: 0.97;
        transition: opacity 0.3s;
    }
    .a11y-modal {
        position: fixed ;
        top: 0 ;
        left: 0 ;
        width: 100vw ;
        height: 100vh ;
        background: rgba(30, 34, 30, 0.55) ;
        display: flex ;
        align-items: center ;
        justify-content: center ;
        z-index: 10000 ;
        animation: fadeIn 0.3s cubic-bezier(.4,0,.2,1) ;
        font-family: 'Segoe UI', Arial, sans-serif ;
        padding: 0 ;
        box-sizing: border-box ;
        backdrop-filter: blur(4px) saturate(1.2);
    }
    .a11y-modal-content {
        background: linear-gradient(135deg, #fffbe6 0%, #f8f9fa 100%);
        padding: 32px 28px 24px 28px ;
        border-radius: 18px ;
        box-shadow: 0 8px 32px rgba(30,34,90,0.18), 0 2px 8px rgba(0,0,0,0.08) ;
        max-width: 440px ;
        width: 96vw ;
        max-height: 88vh ;
        overflow-y: auto ;
        position: relative ;
        animation: fadeIn 0.3s cubic-bezier(.4,0,.2,1) ;
        border: 1.5px solid #e9ecef;
        display: flex;
        flex-direction: column;
        align-items: flex-start;
        gap: 10px;
    }
    .a11y-modal-content h2 {
        margin-top: 0 ;
        margin-bottom: 10px;
        font-size: 1.45rem;
        font-weight: 700;
        color: #111;
        letter-spacing: 0.01em;
    }
    .a11y-modal-content p {
        line-height: 1.7 ;
        color: #333;
        font-size: 1.07rem;
        margin-bottom: 0;
        margin-top: 0;
    }
    .a11y-close-button {
        position: absolute ;
        top: 12px ;
        right: 16px ;
        background: none ;
        border: none ;
        font-size: 28px ;
        line-height: 0.4;
        cursor: pointer ;
        color: #888 ;
        transition: color 0.2s, background 0.2s ;
        border-radius: 50%;
        width: 38px;
        height: 38px;
        display: flex;
        text-align: center;
        align-items: center;
        justify-content: center;
        margin: 0;
        padding: 0;
        font-weight: 600;
        
    }
    .a11y-close-button:hover, .a11y-close-button:focus {
        color: #fff ;
        background: #1976d2 ;
        outline: none;
    }
    .a11y-modal-content::-webkit-scrollbar {
        width: 8px;
        background: #f1f3f5;
        border-radius: 8px;
    }
    .a11y-modal-content::-webkit-scrollbar-thumb {
        background: #e9ecef;
        border-radius: 8px;
    }
    @media (max-width: 600px) {
        .a11y-modal-content {
            max-width: 98vw;
            width: 98vw;
            padding: 18px 7vw 16px 7vw;
            border-radius: 12px;
        }
        .a11y-modal-content h2 {
            font-size: 1.1rem;
        }
        .a11y-modal-content p {
            font-size: 0.97rem;
        }
        .a11y-close-button {
            font-size: 22px;
            width: 32px;
            height: 32px;
            top: 8px;
            right: 8px;
        }
    }
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(-10px); }
        to { opacity: 1; transform: translateY(0); }
    }
    .a11y-loading-indicator {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(30, 34, 30, 0.55);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 10001;
        font-family: 'Segoe UI', Arial, sans-serif;
        font-size: 18px;
        font-weight: 500;
        letter-spacing: 0.01em;
        border: none;
        opacity: 1;
        transition: opacity 0.3s;
        animation: fadeIn 0.3s cubic-bezier(.4,0,.2,1);
        backdrop-filter: blur(4px) saturate(1.2);
    }
    .a11y-loading-indicator > span {
        display: flex;
        align-items: center;
        background: linear-gradient(135deg, #fffbe6 0%, #f8f9fa 100%);
        color: #222;
        padding: 22px 36px;
        border-radius: 18px;
        box-shadow: 0 8px 32px rgba(30,34,90,0.18), 0 2px 8px rgba(0,0,0,0.08);
        border: 1.5px solid #e9ecef;
        font-size: 1.15rem;
        font-weight: 600;
        gap: 18px;
    }
    .a11y-loading-spinner {
        display: inline-block;
        width: 38px;
        height: 38px;
        border: 5px solid #fff;
        border-top: 5px solid #1976d2;
        border-radius: 50%;
        animation: a11y-spin 1s linear infinite;
        vertical-align: middle;
        margin-right: 14px;
        box-shadow: 0 2px 8px rgba(25,118,210,0.10);
        background: transparent;
    }
    @keyframes a11y-spin {
        0% { transform: rotate(0deg);}
        100% { transform: rotate(360deg);}
    }
`;
document.head.appendChild(style);

let showUserMessages = true;

let loadingElement: HTMLElement | null = null;

function ToggleLoadingIndicator(show: boolean) {
    if (show) {
        if (loadingElement) return;
        // Check if document.body is available and has appendChild method
        if (!document.body || typeof document.body.appendChild !== 'function') {
            console.warn(
                '[A11y Scanner] document.body not available or not writable, skipping loading indicator'
            );
            return;
        }
        loadingElement = document.createElement('div');
        loadingElement.innerHTML = `
            <span>
                <span class="a11y-loading-spinner" aria-hidden="true"></span>
                <span style="margin-left: 12px;">Loading, please wait...</span>
            </span>
        `;
        loadingElement.className = 'a11y-loading-indicator';
        document.body.appendChild(loadingElement);

        // Add spinner styles if not already present
        if (!document.getElementById('a11y-loading-spinner-style')) {
            const spinnerStyle = document.createElement('style');
            spinnerStyle.id = 'a11y-loading-spinner-style';
            spinnerStyle.innerHTML = `
                
            `;
            document.head.appendChild(spinnerStyle);
        }
    } else {
        loadingElement?.remove();
        loadingElement = null;
    }
}
ToggleLoadingIndicator(true);

// Assistent function for preparing the dom

function OpenModal(
    title: string,
    message: string,
    extra: HTMLElement | null = null,
    onClose: (() => void) | null = null
) {
    const modal = document.createElement('div');
    modal.className = 'a11y-modal';
    modal.innerHTML = `
        <div class="a11y-modal-content">
            <span class="a11y-close-button" role="button" aria-label="Close Modal">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="currentColor">
                <path d="M18.3 5.71a1 1 0 0 0-1.41 0L12 10.59 7.11 5.7A1 1 0 0 0 5.7 7.11L10.59 12l-4.89 4.89a1 1 0 1 0 1.41 1.41L12 13.41l4.89 4.89a1 1 0 0 0 1.41-1.41L13.41 12l4.89-4.89a1 1 0 0 0 .01-1.4z"/>
            </svg>

            </span>
            <h2>${title}</h2>
            <p>${message}</p>${extra ? extra.outerHTML : ''}</div>
    `;
    document.body.style.position = 'relative';
    document.body.appendChild(modal);

    // Capture all events and stop their propagation to prevent background interaction
    const stopEvent = (e: Event) => {
        e.stopPropagation();
        if (e.cancelable) e.preventDefault();
    };
    [
        'mousedown',
        'mouseup',
        'mousemove',
        'mouseenter',
        'mouseleave',
        'keydown',
        'keyup',
        'keypress',
        'focus',
        'blur',
        'touchstart',
        'touchend',
        'touchmove',
        'wheel',
        'scroll',
        'contextmenu',
    ].forEach((eventType) => {
        modal.addEventListener(eventType, stopEvent, true);
    });

    const close = () => {
        document.body.removeChild(modal);
        onClose?.();
    };

    const closeButton = modal.querySelector('.a11y-close-button') as HTMLElement;
    closeButton.onclick = close;

    window.onclick = (event) => {
        if (event.target === modal) {
            close();
        }
    };
}

function makeZindexSafe() {
    // Make all z-index values within a safe range (0-1000) to avoid conflicts with tooltips
    // Find all elements with a z-index value
    const allElements = document.querySelectorAll<HTMLElement>('*');
    let smallestZindex = 1000;
    let largestZindex = 0;

    allElements.forEach((element) => {
        // set all z-index values above 1000 to 1000
        if (element.style.zIndex) {
            const zIndex = parseInt(element.style.zIndex);
            if (!isNaN(zIndex)) {
                if (zIndex > largestZindex) {
                    largestZindex = zIndex;
                }
                if (zIndex < smallestZindex) {
                    smallestZindex = zIndex;
                }
            }
        }
    });

    const range = largestZindex - smallestZindex;
    const scale = range > 0 ? 900 / range : 1;

    allElements.forEach((element) => {
        if (element.style.zIndex) {
            const zIndex = parseInt(element.style.zIndex);
            if (!isNaN(zIndex)) {
                let newZindex = Math.round((zIndex - smallestZindex) * scale) + 1;
                if (newZindex > 999) {
                    newZindex = 999;
                }
                element.style.zIndex = newZindex.toString();
            }
        } else {
            // set base z-index to 1
            element.style.zIndex = 'auto';
        }
    });
}

let alerts: HTMLElement[] = [];
function addAlert(message: string, timeout = 15000) {
    // Disable alerts if showUserMessages is false used for Report mode
    if (!showUserMessages) {
        return;
    }
    const alert = document.createElement('div');
    alert.className = 'a11y-alert';

    alert.innerText = message;

    // If there are already alerts, move the new one down
    if (alerts.length > 0) {
        let offset = 0;
        alerts.forEach((a) => {
            offset += a.offsetHeight + 10; // 10px margin
        });
        alert.style.top = `${10 + offset}px`;
    }

    document.body.firstChild?.before(alert);
    alerts.push(alert);
    // Remove the alert after 15 seconds
    setTimeout(() => {
        alerts = alerts.filter((a) => a !== alert);

        // fade out the alert
        alert.style.transition = 'opacity 0.5s';
        alert.style.opacity = '0';
        setTimeout(() => {
            if (alert.parentElement) {
                alert.parentElement.removeChild(alert);
            }

            // Move remaining alerts up
            if (alerts.length > 0) {
                let offset = 0;
                alerts.forEach((a) => {
                    a.style.top = `${10 + offset}px`;
                    offset += a.offsetHeight + 10; // 10px margin
                });
            }
        }, 500);
    }, timeout);
}

// Call the function to adjust z-index values
makeZindexSafe();

type Injection = {
    selector: string;
    style: string;
    impact: 'minor' | 'moderate' | 'serious' | 'critical';
    description: string;
    message: string;
    help: string;
    help_url: string;
};

var injections: Injection[] = [];

let currentFocus: HTMLElement | null = null;
let tooltipAnimation: Animation | null = null;
let currentTooltipFocused = false;

function getImpactColor(impact: string): string {
    switch (impact) {
        case 'critical':
            return 'darkred';
        case 'serious':
            return 'red';
        case 'moderate':
            return 'orange';
        case 'minor':
            return 'yellow';
        default:
            return 'gray';
    }
}

function createMessage(injection: Injection, single: boolean, element?: HTMLElement) {
    const message = document.createElement('div');

    // Add impact level and description
    const impactDiv = document.createElement('div');
    impactDiv.style.display = 'inline-block';
    impactDiv.style.fontWeight = 'bold';
    impactDiv.style.color = getImpactColor(injection.impact);
    impactDiv.innerText = injection.impact.toUpperCase();
    message.appendChild(impactDiv);

    message.appendChild(document.createElement('br'));

    const descriptionSpan = document.createElement('span');
    descriptionSpan.style.marginLeft = '8px';
    descriptionSpan.innerText = injection.description;
    message.appendChild(descriptionSpan);

    // Add a line break
    message.appendChild(document.createElement('br'));

    // Add message if available
    if (injection.message && injection.message.trim() !== '') {
        const msgDiv = document.createElement('div');
        msgDiv.style.marginBottom = '4px';
        msgDiv.style.color = '#333';
        const em = document.createElement('em');
        em.innerText = injection.message;
        msgDiv.appendChild(em);
        message.appendChild(msgDiv);
    }

    // Add help text if available
    if (injection.help && injection.help.trim() !== '') {
        const pre = document.createElement('pre');
        pre.style.marginBottom = '4px';
        pre.innerHTML = injection.help.replaceAll('<', '&lt;').replaceAll('>', '&gt;');
        message.appendChild(pre);
    }

    const helpLink = document.createElement('a');
    helpLink.href = injection.help_url;
    helpLink.target = '_blank';
    helpLink.style.color = '#1976d2';
    helpLink.style.textDecoration = 'underline';
    helpLink.innerText = 'Learn more about this issue';
    helpLink.title = 'Open documentation in a new tab';
    message.appendChild(helpLink);

    message.appendChild(document.createElement('br'));

    // If single, add extra info
    if (single) {
        const infoDiv = document.createElement('div');
        infoDiv.style.marginTop = '8px';
        infoDiv.style.color = '#555';
        infoDiv.style.fontSize = '10px';
        infoDiv.style.wordBreak = 'break-word';
        infoDiv.style.textWrap = 'balance';
        infoDiv.innerText =
            '(Click anywhere on the highlighted element to learn more or press the "Ask Microsoft Copilot" button below to get a custom AI prompt for this issue. This will copy the prompt to clipboard and open the AI Copilot in a new tab.)';
        message.appendChild(infoDiv);
    }

    message.className = 'a11y-tooltip-message';

    message.addEventListener('click', () => {
        window.open(injection.help_url, '_blank');
    });
    message.addEventListener('mouseenter', () => {
        message.style.backgroundColor = 'rgba(0, 0, 0, 0.1)';
    });
    message.addEventListener('mouseleave', () => {
        message.style.backgroundColor = 'transparent';
    });
    if (!single) {
        message.style.borderBottom = '2px solid #ccc';
    }

    // Label all children of message as a11y-tooltip-message-content
    const children = message.querySelectorAll('*');
    children.forEach((child) => {
        child.className = 'a11y-tooltip-message-content';
    });
    if (element) {
        // add a button to make an AI prompt for this issue
        const aiButton = document.createElement('button');
        const text = 'Ask Microsoft Copilot';

        aiButton.innerText = text;
        aiButton.className = 'a11y-message-ai-button';
        aiButton.type = 'button';
        aiButton.title = `${text}, and copy the prompt to clipboard`;

        aiButton.addEventListener('click', async (e) => {
            e.stopPropagation();
            aiButton.disabled = true;
            aiButton.innerText = 'Loading...';
            const prompt = makeAiPrompt(injection, element);
            try {
                navigator.clipboard.writeText(prompt);

                // see if tab already has copilot open, if so, focus it, otherwise open it

                const extra = document.createElement('div');
                extra.style.marginTop = '12px';
                extra.style.fontSize = '13px';
                extra.style.color = '#333';
                extra.innerHTML = `Redirecting to <a href="https://copilot.microsoft.com/" target="_blank" style="color:#1976d2;text-decoration:underline;">Microsoft Copilot</a>...`;

                OpenModal(
                    'AI Prompt Copied to Clipboard',
                    `The AI prompt has been copied to your clipboard. Please paste it into your preferred AI tool, such as Microsoft 365 Copilot, to get assistance with resolving the accessibility issue.`,
                    extra
                );

                // wait 2 seconds
                await new Promise((resolve) => setTimeout(resolve, 3000));
                window.open('https://copilot.microsoft.com/', 'copilot', 'noopener,noreferrer');
            } catch (error) {
                console.error('Error calling AI API:', error);
            } finally {
                aiButton.disabled = false;
                aiButton.innerText = text;
            }
        });
        message.appendChild(aiButton);
    }
    return message;
}

function makeAiPrompt(injection: Injection, element: HTMLElement) {
    const prompt = `You are a web accessibility expert. Please review the following issue and provide guidance on how to fix it:

    Issue Description: ${injection.description}
    Impact Level: ${injection.impact}
    Suggested Fix: ${injection.help}
    Help URL: ${injection.help_url}
    Affected Element: ${element.outerHTML}
    Additional Information: ${injection.message}

    Please provide a detailed response with code examples where applicable.`;
    return prompt;
}

function createToolTip(injections: Injection[], element: HTMLElement, selector: string) {
    // Create a tooltip element
    const tooltip = document.createElement('div');
    const clonedElement = element.cloneNode(true) as HTMLElement;

    // check if cloned element subtree contains our tooltip, if so, remove it
    const existingTooltips = clonedElement.querySelectorAll('.a11y-tooltip');
    existingTooltips.forEach((tooltip) => tooltip.remove());

    // remove a11y classes from cloned element
    const a11yClasses = Array.from(clonedElement.classList).filter((cls) =>
        cls.startsWith('a11y-')
    );
    a11yClasses.forEach((cls) => clonedElement.classList.remove(cls));

    tooltip.className = 'a11y-tooltip';

    let tooltipFocused = false;
    tooltip.addEventListener('mouseenter', () => {
        tooltipFocused = true;
        currentFocus = tooltip;
        tooltip.style.display = 'block';
        currentTooltipFocused = true;
    });
    tooltip.addEventListener('mouseleave', () => {
        tooltipFocused = false;
        currentTooltipFocused = false;
    });

    const numberOfInjections = injections.length;
    // Populate the tooltip with injection messages
    injections.forEach((injection) => {
        if (injection.selector === selector) {
            // sometimes help has html tags, so we need to escape them

            // Compose a more readable and visually clear tooltip message
            const message = createMessage(injection, numberOfInjections === 1, clonedElement);
            tooltip.appendChild(message);
        }
    });

    // Append the tooltip to the element
    // Check if element is a img or input type image, if so, append tooltip to parent
    if (
        element.tagName.toLowerCase() === 'img' ||
        (element.tagName.toLowerCase() === 'input' &&
            (element as HTMLInputElement).type === 'image')
    ) {
        if (element.parentElement) {
            element.parentElement.style.position = 'relative';
            element.parentElement.appendChild(tooltip);
        } else {
            element.style.position = 'relative';
            element.appendChild(tooltip);
        }
    } else {
        element.style.position = 'relative';
        element.appendChild(tooltip);
    }

    // Position the tooltip on hover
    element.addEventListener('mouseenter', (event) => {
        event.stopPropagation();

        if (currentTooltipFocused) {
            return;
        }
        if (currentFocus === tooltip) {
            return;
        }
        if (currentFocus && currentFocus !== tooltip) {
            currentFocus.style.display = 'none';

            // Reset styles of previously focused element
            if (tooltipAnimation) {
                tooltipAnimation.cancel();
                tooltipAnimation = null;
            }
            currentFocus = null;
        }

        tooltip.style.display = 'block';

        // Log all injections to the console for debugging

        injections.forEach((injection) => {
            //@ts-ignore
            accesslog(
                `[${injection.impact}] [${injection.description}] [${injection.help}] [${
                    injection.help_url
                }] ${
                    injection.message && injection.message.trim() !== ''
                        ? '- ' + injection.message
                        : ''
                }`,
                'info',
                element
            );
        });

        currentFocus = tooltip;

        // make sure the tooltip is child of the element

        // Highlight the element with an animation based on the highest impact level

        const elementBorderColor = getImpactColor(
            injections
                .map((inj) => inj.impact)
                .sort((a, b) => {
                    const levels = { critical: 4, serious: 3, moderate: 2, minor: 1, null: 0 };
                    return levels[b] - levels[a];
                })[0]
        );

        const oldBorder = element.style.border;

        // If the element already has a border, make it dashed

        // add element highlight animation (no rotation)
        element.style.border = `3px dashed ${elementBorderColor}`;
        element.style.transition = 'border 0.2s, box-shadow 0.2s';
        element.style.boxShadow = `0 0 8px 2px ${elementBorderColor}`;

        if (tooltipAnimation) {
            tooltipAnimation.cancel();
        }

        tooltipAnimation = {
            cancel: () => {
                element.style.boxShadow = '';
                element.style.border = oldBorder;
            },
        } as unknown as Animation;
    });

    element.addEventListener('mouseleave', () => {
        if (currentFocus === tooltip && tooltipFocused) {
            return;
        }
        if (!tooltipFocused) {
            tooltip.style.display = 'none';
            element.style.zIndex = ''; // Reset z-index
        }
        if (currentFocus === tooltip) {
            currentFocus = null;
            tooltip.style.display = 'none';
        }

        // remove element animation
        // element.style.boxShadow = 'none';
        tooltipAnimation?.cancel();
        tooltipAnimation = null;
    });

    if (injections.length == 1) {
        element.style.position = 'relative';
        element.style.cursor = 'pointer';
        element.title = injections[0].message;
        element.addEventListener('click', () => {
            window.open(injections[0].help_url, '_blank');
        });
    }
    return tooltip;
}

var elementMap = new Map<string, Injection[]>();

let alertTimeout = 10000;

for (const injection of injections) {
    try {
        const elements = document.querySelector(injection.selector);
        if (!elements) {
            console.log(`No elements found for selector: ${injection.selector}`);
            addAlert(`No elements found for selector: ${injection.selector}`, alertTimeout);
            alertTimeout += 2500; // Increase timeout for next alert
            continue;
        }

        if (!elementMap.has(injection.selector)) {
            elementMap.set(injection.selector, []);
        }
        elementMap.get(injection.selector)?.push(injection);
    } catch (error) {
        console.log(`Error processing selector ${injection.selector}:`, error);
        continue;
    }
}

let tooltips: HTMLElement[] = [];
for (const [selector, injections] of elementMap.entries()) {
    try {
        const elements = document.querySelectorAll(selector);
        elements.forEach((element) => {
            // check if element is our tooltip, or is parent to our tooltip, if so, skip it
            // Skip if the element or any of its ancestors up to 3 levels are a tooltip
            if (element.classList.value.includes('a11y')) {
                // all elements used in the script have a11y in their class name, so skip them
                return;
            }

            // Apply styles
            injections.forEach((injection) => {
                (element as HTMLElement).classList.add(`a11y-${injection.impact}`);
            });
            // Create tooltip
            const tooltip = createToolTip(injections, element as HTMLElement, selector);
            tooltips.push(tooltip);
        });
    } catch (error) {
        console.log(`Error processing selector ${selector}:`, error);
    }
}

// Add a global click listener to hide tooltips when clicking outside
document.addEventListener('click', (event) => {
    if (currentFocus && !currentFocus.contains(event.target as Node)) {
        currentFocus.style.display = 'none';
        currentFocus = null;
        currentTooltipFocused = false;
    }
});

// Log summary of injections applied
console.log(
    `Applied ${injections.length} style injections to ${elementMap.size} unique selectors.`
);

addAlert(`Click on highlighted elements to learn more about the changes made.`, 15000);
addAlert(
    `Click the "Ask Microsoft Copilot" button in the tooltip, this will copy the prompt to clipboard and open another tab with Microsoft 365 Copilot.`,
    20000
);

ToggleLoadingIndicator(false);
