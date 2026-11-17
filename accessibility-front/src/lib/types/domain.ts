export type Domain = {
    id: string;
    domain: string;
    parent: Domain | null;
    // add other properties if needed
    active: boolean;
    // Site discovery: weekly runs, the last run and why its certificate lookup failed.
    discovery_enabled: boolean;
    discovered_at: string | null;
    discovery_error: string | null;
};
