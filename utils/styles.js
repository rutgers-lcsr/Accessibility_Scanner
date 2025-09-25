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
var _a;
let showUserMessages = true;
// Assistent function for preparing the dom
function makeZindexSafe() {
    // Make all z-index values within a safe range (0-1000) to avoid conflicts with tooltips
    // Find all elements with a z-index value
    const allElements = document.querySelectorAll('*');
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
        }
        else {
            // set base z-index to 1
            element.style.zIndex = 'auto';
        }
    });
}
let alerts = [];
function addAlert(message, timeout = 15000) {
    var _a;
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
    (_a = document.body.firstChild) === null || _a === void 0 ? void 0 : _a.before(alert);
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
var injections = [];
let currentFocus = null;
let tooltipAnimation = null;
let currentTooltipFocused = false;
function getImpactColor(impact) {
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
function createMessage(injection, single) {
    const message = document.createElement('div');
    message.innerHTML = `
                <div style="margin-bottom: 4px;">
                    <span style="font-weight: bold; color: ${getImpactColor(injection.impact)};">
                        ${injection.impact.toUpperCase()}
                    </span>
                    <span style="margin-left: 8px;">${injection.description}</span>
                </div>
                ${injection.message && injection.message.trim() !== ''
        ? `<div style="margin-bottom: 4px; color: #333;">
                            <em>${injection.message}</em>
                        </div>`
        : ''}
                ${injection.help && injection.help.trim() !== ''
        ? `<pre style="margin-bottom: 4px;">${injection.help
            .replaceAll('<', '&lt;')
            .replaceAll('>', '&gt;')}</pre>`
        : ''}
                <a href="${injection.help_url}" target="_blank" style="color: #1976d2; text-decoration: underline;">
                    Learn more
                </a>
            `;
    if (single) {
        message.innerHTML += `<div style="margin-top: 8px; color: #2b2b2b; font-size: 12px;">
                    (Click anywhere on the highlighted element to learn more)
                </div>`;
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
    return message;
}
function createToolTip(injections, element, selector) {
    // Create a tooltip element
    const tooltip = document.createElement('div');
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
            const message = createMessage(injection, numberOfInjections === 1);
            tooltip.appendChild(message);
        }
    });
    // Append the tooltip to the element
    // Check if element is a img or input type image, if so, append tooltip to parent
    if (element.tagName.toLowerCase() === 'img' ||
        (element.tagName.toLowerCase() === 'input' &&
            element.type === 'image')) {
        if (element.parentElement) {
            element.parentElement.style.position = 'relative';
            element.parentElement.appendChild(tooltip);
        }
        else {
            element.style.position = 'relative';
            element.appendChild(tooltip);
        }
    }
    else {
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
            accesslog(`[${injection.impact}] [${injection.description}] [${injection.help}] [${injection.help_url}] ${injection.message && injection.message.trim() !== ''
                ? '- ' + injection.message
                : ''}`, 'info', element);
        });
        currentFocus = tooltip;
        // make sure the tooltip is child of the element
        // Highlight the element with an animation based on the highest impact level
        const elementBorderColor = getImpactColor(injections
            .map((inj) => inj.impact)
            .sort((a, b) => {
            const levels = { critical: 4, serious: 3, moderate: 2, minor: 1, null: 0 };
            return levels[b] - levels[a];
        })[0]);
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
        };
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
        tooltipAnimation === null || tooltipAnimation === void 0 ? void 0 : tooltipAnimation.cancel();
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
var elementMap = new Map();
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
        (_a = elementMap.get(injection.selector)) === null || _a === void 0 ? void 0 : _a.push(injection);
    }
    catch (error) {
        console.log(`Error processing selector ${injection.selector}:`, error);
        continue;
    }
}
let tooltips = [];
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
                element.classList.add(`a11y-${injection.impact}`);
            });
            // Create tooltip
            const tooltip = createToolTip(injections, element, selector);
            tooltips.push(tooltip);
        });
    }
    catch (error) {
        console.log(`Error processing selector ${selector}:`, error);
    }
}
// Add a global click listener to hide tooltips when clicking outside
document.addEventListener('click', (event) => {
    if (currentFocus && !currentFocus.contains(event.target)) {
        currentFocus.style.display = 'none';
        currentFocus = null;
        currentTooltipFocused = false;
    }
});
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
        animation: highlight 1.5s cubic-bezier(.4,0,.2,1);
    }
    @keyframes highlight {
        0% {
            box-shadow: 0 0 8px 2px #ffe066;
        }
        50% {
            box-shadow: 0 0 16px 6px #ffa94d;
        }
        100% {
            box-shadow: 0 0 8px 2px #ffe066;
        }
    }
    .a11y-tooltip {
        max-width: 420px;
        min-width: 240px;
        overflow-wrap: break-word;
        z-index: 9998;
        font-family: 'Segoe UI', Arial, sans-serif;
        font-size: 15px;
        line-height: 1.5;
        position: absolute;
        background: linear-gradient(135deg, #fffbe6 0%, #f8f9fa 100%);
        color: #222;
        border-radius: 10px;
        border: 1px solid #e9ecef;
        box-shadow: 0 4px 16px rgba(0,0,0,0.12), 0 1.5px 4px rgba(0,0,0,0.08);
        display: none;
        max-height: 400px;
        overflow: auto;
        top: 8px;
        left: 8px;
        transition: box-shadow 0.2s;
    }
    .a11y-tooltip pre {
        white-space: pre-wrap;
        word-wrap: break-word;
        background-color: #f1f3f5;
        padding: 6px 8px;
        border-radius: 4px;
        font-family: 'Fira Mono', 'Consolas', monospace;
        font-size: 13px;
        max-height: 180px;
        overflow: auto;
        margin-bottom: 6px;
    }
    .a11y-tooltip a {
        color: #1976d2;
        text-decoration: underline;
        font-weight: 500;
        transition: color 0.15s;
    }
    .a11y-tooltip a:hover {
        color: #0d47a1;
        text-decoration: underline;
    }
    .a11y-tooltip-message:hover {
        background-color: #f3f0ff;
    }
    @media (max-width: 600px) {
        .a11y-tooltip {
            max-width: 96vw;
            min-width: 140px;
            font-size: 13px;
        }
        .a11y-tooltip-message {
            font-size: 13px;
        }
        .a11y-tooltip pre {
            font-size: 11px;
        }
        .a11y-alert {
            font-size: 12px;
            overflow-wrap: break-word;
            max-width: 180px;
        }
    }
    .a11y-tooltip-message {
        line-height: 1.5;
        font-size: 15px;
        z-index: 9999;
        position: relative;
        cursor: pointer;
        font-weight: 500;
        padding: 7px 6px 7px 6px;
        border-radius: 6px;
        border: 1.5px solid transparent;
        background: transparent;
        transition: background 0.15s, border 0.15s;
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
`;
document.head.appendChild(style);
// Log summary of injections applied
console.log(`Applied ${injections.length} style injections to ${elementMap.size} unique selectors.`);
