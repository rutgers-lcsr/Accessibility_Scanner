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

let showUserMessages = true;

// Assistent function for preparing the dom

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

function createToolTip(injections: Injection[], element: HTMLElement, selector: string) {
    // Create a tooltip element
    const tooltip = document.createElement('div');

    tooltip.className = 'custom-tooltip';

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
                ${
                    injection.message && injection.message.trim() !== ''
                        ? `<div style="margin-bottom: 4px; color: #333;">
                            <em>${injection.message}</em>
                        </div>`
                        : ''
                }
                ${
                    injection.help && injection.help.trim() !== ''
                        ? `<pre style="margin-bottom: 4px;">${injection.help
                              .replaceAll('<', '&lt;')
                              .replaceAll('>', '&gt;')}</pre>`
                        : ''
                }
                <a href="${
                    injection.help_url
                }" target="_blank" style="color: #1976d2; text-decoration: underline;">
                    Learn more
                </a>
            `;
            if (injections.length == 1) {
                message.innerHTML += `<div style="margin-top: 8px; color: #2b2b2b; font-size: 12px;">
                    (Click anywhere on the highlighted element to learn more)
                </div>`;
            }

            message.className = 'tooltip-message';
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
            // Apply styles
            injections.forEach((injection) => {
                (element as HTMLElement).style.cssText += injection.style;
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

// Add some global styles for the tooltip
const style = document.createElement('style');
style.innerHTML = `
    .custom-tooltip {
        max-width: 500px;
        min-width: 300px;
        overflow-wrap: break-word;
        z-index: 9998;
        font-family: Arial, sans-serif;
        font-size: 14px;
        line-height: 1.4;
        position: absolute;
        background-color: rgba(255, 255, 255, 1);
        color: black;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
        border-radius: 4px;
        display: none; /* Initially hidden */
        max-height: 400px;
        overflow: auto;
        top: 3px;
        left: 3px;
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
    .tooltip-message:hover {
        background-color: rgba(0, 0, 0, 0.1);
    }
    @media (max-width: 600px) {
        .custom-tooltip {
            max-width: 90%;
            min-width: 200px;
            font-size: 12px;
        }
        .tooltip-message {
            font-size: 12px;
        }
        .custom-tooltip pre {
            font-size: 11px;
        }
        .a11y-alert {
            font-size: 12px;
            overflow-wrap: break-word;
            max-width: 200px;
        }
    }
    .tooltip-message {
        line-height: 1.4;
        font-size: 14px;
        z-index: 9999;
        position: relative;
        cursor: pointer;
        font-weight: bold;
        padding: 4px;
        position: relative;
    }
    .a11y-alert {
        position: fixed;
        top: 10px;
        right: 10px;
        background-color: darkred;
        color: white;
        padding: 10px;
        border-radius: 5px;
        z-index: 10000;
        font-family: Arial, sans-serif;
        font-size: 14px;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
    }
`;
document.head.appendChild(style);

// Log summary of injections applied
console.log(
    `Applied ${injections.length} style injections to ${elementMap.size} unique selectors.`
);
