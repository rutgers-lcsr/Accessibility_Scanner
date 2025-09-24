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

            message.innerHTML = `<strong style="color: ${getImpactColor(
                injection.impact
            )};">${injection.impact.toUpperCase()}</strong>: ${injection.description}
            <br/>
            ${
                injection.message && injection.message.trim() !== ''
                    ? `<em>${injection.message}</em><br/>`
                    : ''
            }
            <div style="margin-top: 4px;">Help:</div>
            ${
                injection.help && injection.help.trim() !== ''
                    ? `<pre>${injection.help
                          .replaceAll('<', '&lt;')
                          .replaceAll('>', '&gt;')}<br/></pre>`
                    : ''
            }
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

    // Append the tooltip to the body
    document.body.appendChild(tooltip);

    // Position the tooltip on hover
    element.addEventListener('mouseenter', (event) => {
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
        const rect = element.getBoundingClientRect();

        // Set the tooltip to be relative to the hovered element
        let top = rect.top + window.scrollY + 20; // 20px below the element
        let left = rect.left + window.scrollX + 20; // 20px to the right of the element

        // Adjust position if tooltip goes beyond viewport
        if (left + tooltip.offsetWidth > window.innerWidth) {
            left = rect.right + window.scrollX - tooltip.offsetWidth - 20; // Position to the left
        }
        if (top + tooltip.offsetHeight > window.innerHeight) {
            top = rect.top + window.scrollY; // Position above
        }

        // Apply the calculated position

        tooltip.style.top = `${top}px`;
        tooltip.style.left = `${left}px`;
        tooltip.style.zIndex = '9998'; // Ensure the tooltip is above other content

        element.style.zIndex = '9900'; // Ensure the element is above other content
        // make sure all elements are below the tooltip
        tooltip.style.zIndex = '9999';

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
        if (!tooltipFocused) {
            tooltip.style.display = 'none';
            element.style.zIndex = ''; // Reset z-index
        }
        if (currentFocus === tooltip) {
            currentFocus = null;
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
}

var elementMap = new Map<string, Injection[]>();

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
        elementMap.get(injection.selector)?.push(injection);
    } catch (error) {
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
                (element as HTMLElement).style.cssText += injection.style;
            });
            // Create tooltip
            createToolTip(injections, element as HTMLElement, selector);
        });
    } catch (error) {
        console.log(`Error processing selector ${selector}:`, error);
    }
}
