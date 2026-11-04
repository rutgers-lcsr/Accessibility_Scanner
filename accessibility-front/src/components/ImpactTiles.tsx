'use client';
import { IMPACTS } from '@/lib/impact';
import { AxeReportCounts } from '@/lib/types/axe';
import { Tooltip } from 'antd';

// The four severity count tiles shown on the dashboard, report and website pages. A tile only
// takes its severity colour when it has something in it, so the eye goes to the non-zero ones.
function ImpactTiles({ counts }: { counts: AxeReportCounts }) {
    return (
        <ul
            className="grid grid-cols-2 gap-3 md:grid-cols-4 md:gap-4"
            style={{ margin: 0, padding: 0, listStyle: 'none' }}
        >
            {IMPACTS.map((meta) => {
                const count = counts[meta.key];
                const active = count > 0;
                return (
                    <li key={meta.key}>
                        <Tooltip title={meta.description}>
                            <div
                                className={`flex h-full flex-col gap-3 rounded-xl border px-4 py-3.5 ${active ? `${meta.bg} ${meta.border}` : 'border-gray-200 bg-white'}`}
                            >
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
                            </div>
                        </Tooltip>
                    </li>
                );
            })}
        </ul>
    );
}

export default ImpactTiles;
