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
            element.style.zIndex = '1';
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
    alert.style.position = 'fixed';
    alert.style.top = '10px';
    alert.style.right = '10px';
    alert.style.backgroundColor = 'darkred';
    alert.style.color = 'white';
    alert.style.padding = '10px';
    alert.style.borderRadius = '5px';
    alert.style.zIndex = '10000';
    alert.style.fontFamily = 'Arial, sans-serif';
    alert.style.fontSize = '14px';
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
function createToolTip(injections, element, selector) {
    // Create a tooltip element
    const tooltip = document.createElement('div');
    tooltip.className = 'custom-tooltip';
    tooltip.style.position = 'absolute';
    tooltip.style.backgroundColor = 'rgba(255, 255, 255, 1)';
    tooltip.style.color = 'black';
    tooltip.style.boxShadow = '0 2px 4px rgba(0, 0, 0, 0.2)';
    tooltip.style.borderRadius = '4px';
    tooltip.style.fontSize = '14px';
    tooltip.style.display = 'none'; // Initially hidden
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
            const message = document.createElement('div');
            // sometimes help has html tags, so we need to escape them
            // Compose a more readable and visually clear tooltip message
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
            if (injections.length == 1) {
                message.innerHTML += `<div style="margin-top: 8px; color: #2b2b2b; font-size: 12px;">
                    (Click anywhere on the highlighted element to learn more)
                </div>`;
            }
            message.style.lineHeight = '1.4';
            message.style.fontSize = '14px';
            message.style.zIndex = '9999';
            message.style.position = 'relative';
            message.style.cursor = 'pointer';
            message.style.fontWeight = 'bold';
            message.style.padding = '4px';
            message.title = injection.message;
            message.addEventListener('click', () => {
                window.open(injection.help_url, '_blank');
            });
            message.addEventListener('mouseenter', () => {
                message.style.backgroundColor = 'rgba(0, 0, 0, 0.1)';
            });
            message.addEventListener('mouseleave', () => {
                message.style.backgroundColor = 'transparent';
            });
            if (numberOfInjections > 1) {
                message.style.borderBottom = '2px solid #ccc';
            }
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
        tooltip.style.position = 'absolute';
        tooltip.style.top = '3px';
        tooltip.style.left = '3px';
        tooltip.style.zIndex = '9998'; // Ensure the tooltip is above other content
        tooltip.style.zIndex = '9999';
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
            // Apply styles
            injections.forEach((injection) => {
                element.style.cssText += injection.style;
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
    .custom-tooltip {
        max-width: 500px;
        min-width: 300px;
        overflow-wrap: break-word;
        z-index: 9999;
        font-family: Arial, sans-serif;
        font-size: 14px;
        line-height: 1.4;
    }
    .custom-tooltip pre {
        white-space: pre-wrap; /* Allow line breaks */
        word-wrap: break-word; /* Break long words */
        background-color: #f4f4f4;
        padding: 4px;
        border-radius: 4px;
        font-family: monospace;
        font-size: 13px;
        max-height: 200px;
        overflow: auto;
    }
    .custom-tooltip a {
        text-decoration: none;
    }
    .custom-tooltip a:hover {
        text-decoration: underline;
    }
`;
document.head.appendChild(style);
// Log summary of injections applied
console.log(`Applied ${injections.length} style injections to ${elementMap.size} unique selectors.`);
