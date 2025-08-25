export type Domain = {
    id: string;
    domain: string;
    parent: Domain | null;
    // add other properties if needed
    active: boolean;
};
