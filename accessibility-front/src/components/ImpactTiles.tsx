'use client';
import { IMPACTS } from '@/lib/impact';
import { AxeReportCounts } from '@/lib/types/axe';
import { Tooltip } from 'antd';

type Props = {
    counts: AxeReportCounts;
    // The id of the issue list a non-empty tile leads to, filtered to that impact
    // (?impact=critical#<id>). Without it the tiles are plain counts with the severity
    // explained in a tooltip.
    listId?: string;
    // Extra query parameters for that link, e.g. "tab=violations" on the website page.
    query?: string;
    // Counts that are not this website's (a scan that ended on another site): no colour.
    muted?: boolean;
};

// The four severity count tiles shown on the dashboard, report and website pages. A tile only
// takes its severity colour when it has something in it, so the eye goes to the non-zero ones.
function ImpactTiles({ counts, listId, query, muted = false }: Props) {
    return (
        <ul
            className="grid grid-cols-2 gap-3 md:grid-cols-4 md:gap-4"
            style={{ margin: 0, padding: 0, listStyle: 'none' }}
        >
            {IMPACTS.map((meta) => {
                const count = counts[meta.key];
                const active = count > 0 && !muted;
                const body = (
                    <>
                        <span
                            className={`flex items-center gap-2 text-sm font-medium ${active ? meta.text : 'text-gray-600'}`}
                        >
                            <span aria-hidden="true" className="text-base leading-none">
                                {meta.icon}
                            </span>
                            {meta.label}
                        </span>
                        <span
                            className={`text-3xl leading-none font-semibold tabular-nums ${active ? meta.text : 'text-gray-500'}`}
                        >
                            {count}
                        </span>
                    </>
                );
                const box = `flex h-full flex-col gap-3 rounded-xl border px-4 py-3.5 ${active ? `${meta.bg} ${meta.border}` : 'border-gray-200 bg-white'}`;
                return (
                    <li key={meta.key}>
                        {active && listId ? (
                            // A link, not a Tooltip: the description goes in the accessible
                            // name and the title, and a keyboard user can reach it.
                            <a
                                href={`?${query ? `${query}&` : ''}impact=${meta.key}#${listId}`}
                                className={`${box} tile-link no-underline transition-shadow hover:shadow-md focus-visible:outline-2 focus-visible:outline-offset-2`}
                                title={meta.description}
                                aria-label={`${count} ${meta.label.toLowerCase()}: show ${count === 1 ? 'it' : 'them'}`}
                            >
                                {body}
                            </a>
                        ) : (
                            <Tooltip title={meta.description}>
                                <div className={box}>{body}</div>
                            </Tooltip>
                        )}
                    </li>
                );
            })}
        </ul>
    );
}

export default ImpactTiles;
