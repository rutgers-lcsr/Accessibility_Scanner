var _a;
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
    tooltip.style.backgroundColor = 'rgba(255, 255, 255, 0.9)';
    tooltip.style.color = 'black';
    // tooltip.style.padding = '8px';
    tooltip.style.boxShadow = '0 2px 4px rgba(0, 0, 0, 0.2)';
    tooltip.style.borderRadius = '4px';
    tooltip.style.fontSize = '14px';
    // tooltip.style.maxWidth = '200px';
    tooltip.style.zIndex = '9998';
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
    // Populate the tooltip with injection messages
    injections.forEach((injection) => {
        if (injection.selector === selector) {
            const message = document.createElement('div');
            // sometimes help has html tags, so we need to escape them
            message.innerHTML = `<strong style="color: ${getImpactColor(injection.impact)};">${injection.impact.toUpperCase()}</strong>: ${injection.description}
            <br/>
            ${injection.message && injection.message.trim() !== ''
                ? `<em>${injection.message}</em><br/>`
                : ''}
            <div style="margin-top: 4px;">Help:</div>
            ${injection.help && injection.help.trim() !== ''
                ? `<pre>${injection.help
                    .replaceAll('<', '&lt;')
                    .replaceAll('>', '&gt;')}<br/></pre>`
                : ''}
            <a href="${injection.help_url}" target="_blank" style="color: blue;">Learn more</a>
            `;
            if (injections.length == 1) {
                message.innerHTML =
                    message.innerHTML +
                        `<br/><br/><em>(Click anywhere on the highlighted element to learn more)</em>`;
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
                message.style.textDecoration = 'underline';
            });
            message.addEventListener('mouseleave', () => {
                message.style.textDecoration = 'none';
                message.style.backgroundColor = 'transparent';
            });
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
        element.style.zIndex = '9900'; // Ensure the element is above other content
        // make sure all elements are below the tooltip
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
}
var elementMap = new Map();
for (const injection of injections) {
    try {
        const elements = document.querySelector(injection.selector);
        if (!elements) {
            console.log(`No elements found for selector: ${injection.selector}`);
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
for (const [selector, injections] of elementMap.entries()) {
    try {
        const elements = document.querySelectorAll(selector);
        elements.forEach((element) => {
            // Apply styles
            injections.forEach((injection) => {
                element.style.cssText += injection.style;
            });
            // Create tooltip
            createToolTip(injections, element, selector);
        });
    }
    catch (error) {
        console.log(`Error processing selector ${selector}:`, error);
    }
}
