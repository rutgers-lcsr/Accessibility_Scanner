'use client';
import { IMPACTS } from '@/lib/impact';
import { AxeReportCounts } from '@/lib/types/axe';
import { Tooltip } from 'antd';

// The four severity count tiles shown on the report and website pages.
function ImpactTiles({ counts }: { counts: AxeReportCounts }) {
    return (
        <div className="grid grid-cols-2 gap-6 text-center md:grid-cols-4">
            {IMPACTS.map((meta) => (
                <div
                    key={meta.key}
                    className={`flex flex-col items-center rounded-lg ${meta.bg} p-4 shadow-sm`}
                >
                    <Tooltip title={meta.description}>
                        <div className="flex flex-col items-center">
                            <span className={`mb-2 text-3xl ${meta.text}`}>{meta.icon}</span>
                            <h3 className={`mb-2 text-lg font-medium ${meta.text}`}>
                                {meta.label}
                            </h3>
                            <h4 className={`text-3xl font-bold ${meta.text}`}>
                                {counts[meta.key]}
                            </h4>
                        </div>
                    </Tooltip>
                </div>
            ))}
        </div>
    );
}

export default ImpactTiles;
