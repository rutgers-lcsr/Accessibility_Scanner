'use client';
import { Check, CheckTemplate, Rule, RuleTemplate } from '@/lib/types/axe';
import { createContext, Dispatch, SetStateAction, useContext, useState } from 'react';
import useSWR, { KeyedMutator } from 'swr';
import { useAlerts } from './Alerts';
import { useUser } from './User';
type RuleContextType = {
    rules: Rule[] | null;
    tags: string[] | null;
    error: Error | null;
    loading: boolean;
    loadingEdits: boolean;
    loadingChecks: boolean;
    mutate: KeyedMutator<Rule[]>;
    getRuleTags: () => Promise<string[]>;
    setTagSearch: Dispatch<SetStateAction<string>>;
    addRule: (newRule: RuleTemplate) => Promise<boolean>;
    exportRule: (ruleId: number) => Promise<void>;
    validateMatchRule: (match: string) => Promise<boolean>;
    validateCheckRule: (evaluation: string) => Promise<boolean>;
    deleteRule: (ruleId: number) => Promise<void>;
    updateRule: (ruleId: number, updatedFields: Partial<Rule>) => Promise<void>;
    fetchChecks: (ruleId: number) => Promise<{
        all: Check[];
        any: Check[];
        none: Check[];
    }>;
    checkNames: { id: number; name: string }[] | null;
    addCheck: (newCheck: CheckTemplate) => Promise<Check | null>;
    deleteCheck: (checkId: number) => Promise<void>;
    updateCheck: (checkId: number, updatedFields: Partial<Check>) => Promise<Check | null>;
};

export const RuleContext = createContext<RuleContextType | undefined>(undefined);

export const RuleProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
    const { handlerUserApiRequest } = useUser();
    const [loading, setLoading] = useState(false);
    const [loadingEdits, setLoadingEdits] = useState(false);
    const [loadingChecks, setLoadingChecks] = useState(false);
    const [tagSearch, setTagSearch] = useState('');
    const { addAlert } = useAlerts();

    const {
        data: rules,
        error,
        isLoading,
        mutate,
    } = useSWR(
        `/api/axe/rules/` + (tagSearch ? `?search=${tagSearch}` : ''),
        handlerUserApiRequest<Rule[]>
    );
    const {
        data: tags,
        error: tagsError,
        isLoading: tagsLoading,
        mutate: mutateTags,
    } = useSWR('/api/axe/rules/tags/', handlerUserApiRequest<string[]>);

    const {
        data: checkNames,
        error: checkNamesError,
        isLoading: checkNamesLoading,
        mutate: mutateCheckNames,
    } = useSWR('/api/axe/checks/names/', handlerUserApiRequest<{ id: number; name: string }[]>);

    const exportRule = async (ruleId: number) => {
        try {
            const response = await handlerUserApiRequest<Rule>(`/api/axe/rules/${ruleId}/export/`, {
                method: 'GET',
            });
            // Create a URL for the blob
            const url = window.URL.createObjectURL(new Blob([JSON.stringify(response)]));
            // Create a link element
            const link = document.createElement('a');
            link.href = url;
            link.setAttribute('download', `rule-${response.name}.json`); // Set the file name
            // Append to the document and trigger the download
            document.body.appendChild(link);
            link.click();
            // Clean up and remove the link
            link.parentNode?.removeChild(link);
            window.URL.revokeObjectURL(url);
        } catch (error) {
            addAlert(`Failed to export rule ${(error as Error).message}`, 'error');
            console.error('Failed to export rule:', error);
        }
    };

    const validateMatchRule = async (match: string) => {
        try {
            const isValid = await handlerUserApiRequest<{ valid: boolean }>(
                '/api/axe/validate_javascript',
                {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ s: match, type: 'rule_match_function' }),
                }
            );
            return isValid.valid;
        } catch {
            return false;
        }
    };
    const validateCheckRule = async (evaluation: string) => {
        try {
            const isValid = await handlerUserApiRequest<{ valid: boolean }>(
                '/api/axe/validate_javascript',
                {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ s: evaluation, type: 'check_eval_function' }),
                }
            );
            return isValid.valid;
        } catch {
            return false;
        }
    };

    const getRuleTags = async () => {
        try {
            const data = await handlerUserApiRequest<string[]>('/api/axe/rules/tags/', {
                method: 'GET',
            });
            return data;
        } catch (error) {
            addAlert(`Failed to fetch rule tags ${(error as Error).message}`, 'error');
            console.error('Failed to fetch rule tags:', error);
            return [];
        }
    };

    const addRule = async (newRule: RuleTemplate) => {
        // Logic to add a new rule
        setLoading(true);
        try {
            await handlerUserApiRequest<Rule>('/api/axe/rules/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(newRule),
            });
            mutate();
            return true;
        } catch (error) {
            addAlert(`Failed to add rule ${(error as Error).message}`, 'error');
            console.error('Failed to add rule:', error);
            return false;
        } finally {
            setLoading(false);
        }
        // Update state or context with the new rule
    };
    const deleteRule = async (ruleId: number) => {
        // Logic to delete a rule
        setLoadingEdits(true);
        try {
            await handlerUserApiRequest(`/api/axe/rules/${ruleId}`, {
                method: 'DELETE',
            });
            mutate(
                (rules ?? []).filter((r) => r.id !== ruleId),
                false
            );
        } catch (error) {
            addAlert(`Failed to delete rule ${(error as Error).message}`, 'error');
            console.error('Failed to delete rule:', error);
        } finally {
            setLoadingEdits(false);
        }
        // Update state or context to remove the deleted rule
    };
    const updateRule = async (ruleId: number, updatedFields: Partial<Rule>) => {
        // Logic to update a rule
        setLoadingEdits(true);
        try {
            const data = await handlerUserApiRequest<Rule>(`/api/axe/rules/${ruleId}`, {
                method: 'PATCH',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(updatedFields),
            });

            if (updatedFields.tags) {
                mutateTags(); // Refresh tags if they were updated
            }

            mutate(
                (rules ?? []).map((r) => (r.id === ruleId ? data : r)),
                false
            );
        } catch (error) {
            addAlert(`Failed to update rule ${(error as Error).message}`, 'error');
            console.error('Failed to update rule:', error);
        } finally {
            setLoadingEdits(false);
        }
    };

    const fetchChecks = async (ruleId: number) => {
        // Logic to fetch checks for a rule
        setLoadingChecks(true);
        try {
            const data = await handlerUserApiRequest<{
                all: Check[];
                any: Check[];
                none: Check[];
            }>(`/api/axe/rules/${ruleId}/checks/`, {
                method: 'GET',
            });
            // Update state or context with fetched checks
            return data;
        } catch (error) {
            addAlert(`Failed to fetch checks ${(error as Error).message}`, 'error');
            console.error('Failed to fetch checks:', error);
            return { all: [], any: [], none: [] };
        } finally {
            setLoadingChecks(false);
        }
    };

    const addCheck = async (newCheck: CheckTemplate) => {
        // Logic to add a new check
        setLoadingChecks(true);
        try {
            const data = await handlerUserApiRequest<Check>('/api/axe/checks/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(newCheck),
            });

            return data;
        } catch (error) {
            addAlert(`Failed to add check ${(error as Error).message}`, 'error');
            console.error('Failed to add check:', error);
            return null;
        } finally {
            setLoadingChecks(false);
        }
        // Update state or context with the new check
    };
    const deleteCheck = async (checkId: number) => {
        // Logic to delete a check
        setLoadingChecks(true);
        try {
            await handlerUserApiRequest(`/api/axe/checks/${checkId}/`, {
                method: 'DELETE',
            });
        } catch (error) {
            addAlert(`Failed to delete check ${(error as Error).message}`, 'error');
            console.error('Failed to delete check:', error);
        } finally {
            setLoadingChecks(false);
        }
        // Update state or context to remove the deleted check
    };
    const updateCheck = async (checkId: number, updatedFields: Partial<Check>) => {
        // Logic to update a check
        setLoadingChecks(true);
        try {
            const check = await handlerUserApiRequest<Check>(`/api/axe/checks/${checkId}/`, {
                method: 'PATCH',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(updatedFields),
            });
            return check;
        } catch (error) {
            addAlert(`Failed to update check ${(error as Error).message}`, 'error');
            console.error('Failed to update check:', error);
            return null;
        } finally {
            setLoadingChecks(false);
        }
    };

    return (
        <RuleContext.Provider
            value={{
                rules: rules || null,
                error: error || null,
                tags: tags || null,
                setTagSearch,
                loading: isLoading || loading,
                loadingEdits,
                loadingChecks,
                addRule,
                exportRule,
                validateMatchRule,
                validateCheckRule,
                getRuleTags,
                deleteRule,
                updateRule,
                fetchChecks,
                checkNames: checkNames || null,
                addCheck,
                deleteCheck,
                updateCheck,
                mutate,
            }}
        >
            {children}
        </RuleContext.Provider>
    );
};

export const useRules = () => {
    const context = useContext(RuleContext);
    if (!context) {
        throw new Error('useRules must be used within a RuleProvider');
    }
    return context;
};
